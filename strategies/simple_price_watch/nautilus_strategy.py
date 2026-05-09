import os

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from strategies.simple_price_watch.config import SimplePriceWatchConfig
from strategies.simple_price_watch.core import (
    Signal,
    SimplePriceWatchCore,
    StrategyState,
)


class SimplePriceWatchNautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = SimplePriceWatchConfig()
        self.core = SimplePriceWatchCore(self.cfg)
        self.strategy_state = StrategyState()

        self.account_type = os.getenv("TRADING_ACCOUNT_TYPE", "paper")
        self.enable_order_placement = (
            os.getenv("ENABLE_ORDER_PLACEMENT", "false").lower() == "true"
        )

        self.trigger_instrument_id = InstrumentId.from_str(self.cfg.trigger_symbol)
        self.trade_instrument_id = InstrumentId.from_str(self.cfg.trade_symbol)

        trigger_instrument = self.cache.instrument(self.trigger_instrument_id)
        trade_instrument = self.cache.instrument(self.trade_instrument_id)

        if trigger_instrument is None:
            self.log.error(f"Missing trigger instrument: {self.trigger_instrument_id}")
            self.stop()
            return

        if trade_instrument is None:
            self.log.error(f"Missing trade instrument: {self.trade_instrument_id}")
            self.stop()
            return

        self.subscribe_quote_ticks(self.trigger_instrument_id)
        self.subscribe_quote_ticks(self.trade_instrument_id)

        self.log.info(
            f"Started strategy in {self.account_type.upper()} mode "
            f"with trigger={self.cfg.trigger_symbol}, trade={self.cfg.trade_symbol}"
        )
        self.log.info(
            f"BUY if trigger>={self.cfg.buy_trigger_price} and trade<={self.cfg.buy_trade_max_price}"
        )
        self.log.info(
            f"SELL if trigger<={self.cfg.sell_trigger_price} and trade>={self.cfg.sell_trade_min_price}"
        )
        self.log.info(
            f"Enable order placement: {self.enable_order_placement}"
        )

    def on_quote_tick(self, tick):
        trigger_tick = self.cache.quote_tick(self.trigger_instrument_id)
        trade_tick = self.cache.quote_tick(self.trade_instrument_id)

        trigger_price = float(trigger_tick.bid_price) if trigger_tick else None
        trade_price = float(trade_tick.ask_price) if trade_tick else None

        signal = self.core.evaluate(trigger_price, trade_price, self.strategy_state)

        if signal == Signal.BUY:
            self.log.info(
                f"BUY SIGNAL trigger={trigger_price} trade={trade_price} qty={self.cfg.order_quantity}"
            )
            self.strategy_state.position_qty += self.cfg.order_quantity
            self.strategy_state.last_signal = "BUY"

            if self.enable_order_placement:
                self.log.info("Real order placement not wired yet.")
            else:
                self.log.info("Order placement disabled; signal logged only.")

        elif signal == Signal.SELL:
            self.log.info(
                f"SELL SIGNAL trigger={trigger_price} trade={trade_price} qty={self.cfg.order_quantity}"
            )
            self.strategy_state.position_qty -= self.cfg.order_quantity
            self.strategy_state.last_signal = "SELL"

            if self.enable_order_placement:
                self.log.info("Real order placement not wired yet.")
            else:
                self.log.info("Order placement disabled; signal logged only.")

    def on_stop(self):
        self.log.info("SimplePriceWatchNautilusStrategy stopped")