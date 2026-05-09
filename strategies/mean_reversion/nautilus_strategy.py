import os

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from strategies.mean_reversion.config import MeanReversionConfig
from strategies.mean_reversion.core import (
    Signal,
    MeanReversionCore,
    StrategyState,
)


class MeanReversionNautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = MeanReversionConfig()
        self.core = MeanReversionCore(self.cfg)
        self.strategy_state = StrategyState()

        self.account_type = os.getenv("TRADING_ACCOUNT_TYPE", "paper")
        self.enable_order_placement = (
            os.getenv("ENABLE_ORDER_PLACEMENT", "false").lower() == "true"
        )

        self.instrument_id = InstrumentId.from_str(self.cfg.symbol)
        instrument = self.cache.instrument(self.instrument_id)

        if instrument is None:
            self.log.error(f"Missing instrument: {self.instrument_id}")
            self.stop()
            return

        self.subscribe_quote_ticks(self.instrument_id)

        self.log.info(
            f"Started strategy in {self.account_type.upper()} mode "
            f"for symbol={self.cfg.symbol}"
        )
        self.log.info(
            f"BUY if value >= {self.cfg.trigger_value}, "
            f"SELL if value < {self.cfg.trigger_value}"
        )

    def on_quote_tick(self, tick):
        value = float(tick.ask_price) if tick and tick.ask_price else None
        signal = self.core.evaluate(value, self.strategy_state)

        if signal == Signal.BUY:
            self.log.info(f"BUY SIGNAL value={value} qty={self.cfg.order_quantity}")
            self.strategy_state.position_qty += self.cfg.order_quantity
            self.strategy_state.last_signal = "BUY"

            if self.enable_order_placement:
                self.log.info("Real order placement not wired yet.")
            else:
                self.log.info("Order placement disabled; signal logged only.")

        elif signal == Signal.SELL:
            self.log.info(f"SELL SIGNAL value={value} qty={self.cfg.order_quantity}")
            self.strategy_state.position_qty -= self.cfg.order_quantity
            self.strategy_state.last_signal = "SELL"

            if self.enable_order_placement:
                self.log.info("Real order placement not wired yet.")
            else:
                self.log.info("Order placement disabled; signal logged only.")

    def on_stop(self):
        self.log.info("MeanReversionNautilusStrategy stopped")
