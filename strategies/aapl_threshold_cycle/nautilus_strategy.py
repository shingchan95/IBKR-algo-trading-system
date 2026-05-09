import os
from datetime import datetime, timedelta
from pathlib import Path

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from strategies.aapl_threshold_cycle.config import AaplThresholdCycleConfig
from strategies.aapl_threshold_cycle.core import (
    AaplThresholdCycleCore,
    Signal,
    StrategyState,
)


class AaplThresholdCycleNautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = AaplThresholdCycleConfig()
        self.core = AaplThresholdCycleCore(self.cfg)
        self.strategy_state = StrategyState()

        self.account_type = os.getenv("TRADING_ACCOUNT_TYPE", "paper")
        self.enable_order_placement = (
            os.getenv("ENABLE_ORDER_PLACEMENT", "false").lower() == "true"
        )
        self.log_quotes = os.getenv("LOG_QUOTES", "false").lower() == "true"

        self.instrument_id = InstrumentId.from_str(self.cfg.symbol)
        instrument = self.cache.instrument(self.instrument_id)

        if instrument is None:
            self.log.error(f"Missing instrument: {self.instrument_id}")
            self._write_event_log(f"ERROR missing_instrument={self.instrument_id}")
            self.stop()
            return

        self.subscribe_quote_ticks(self.instrument_id)

        self.log.info(
            f"Started strategy in {self.account_type.upper()} mode for {self.cfg.symbol}"
        )
        self.log.info(
            f"BUY if price <= {self.cfg.buy_below_or_equal}, "
            f"SELL if price >= {self.cfg.sell_above_or_equal}"
        )
        self.log.info(f"Enable order placement: {self.enable_order_placement}")
        self.log.info(f"Log quotes: {self.log_quotes}")

        self._write_event_log(
            f"START account_type={self.account_type} "
            f"symbol={self.cfg.symbol} "
            f"buy<={self.cfg.buy_below_or_equal} "
            f"sell>={self.cfg.sell_above_or_equal} "
            f"qty={self.cfg.order_quantity} "
            f"order_enabled={self.enable_order_placement} "
            f"log_quotes={self.log_quotes}"
        )

        self.clock.set_timer(
            name="aapl_threshold_cycle_timer",
            interval=timedelta(seconds=5),
            callback=self._check_latest_quote,
        )

    def _check_latest_quote(self, _event=None):
        quote = self.cache.quote_tick(self.instrument_id)

        bid = float(quote.bid_price) if quote and getattr(quote, "bid_price", None) else None
        ask = float(quote.ask_price) if quote and getattr(quote, "ask_price", None) else None

        # Fallback decision price
        # price = ask if ask is not None else bid
        price = 279.0

        buy_condition = (
            price is not None
            and self.strategy_state.position_qty < self.cfg.max_position
            and price <= self.cfg.buy_below_or_equal
        )

        sell_condition = (
            price is not None
            and self.strategy_state.position_qty > 0
            and price >= self.cfg.sell_above_or_equal
        )

        signal = self.core.evaluate(price, self.strategy_state)

        if self.log_quotes:
            self.log.info(
                f"TIMER_CHECK symbol={self.cfg.symbol} "
                f"bid={bid} ask={ask} used_price={price} "
                f"pos={self.strategy_state.position_qty} "
                f"buy_check={buy_condition} "
                f"sell_check={sell_condition} "
                f"signal={signal.name}"
            )

        if signal == Signal.BUY:
            self.log.info(f"BUY SIGNAL price={price} qty={self.cfg.order_quantity}")
            self._write_event_log(
                f"BUY_SIGNAL price={price} qty={self.cfg.order_quantity}"
            )

            if self.enable_order_placement:
                self._write_order_log(
                    f"ORDER_ATTEMPT side=BUY symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} price={price}"
                )
                self.log.info("Real order placement not wired yet.")
                self._write_order_log(
                    f"ORDER_NOT_SENT reason=not_wired_yet side=BUY "
                    f"symbol={self.cfg.symbol} qty={self.cfg.order_quantity} price={price}"
                )
            else:
                self.log.info("Order placement disabled; signal logged only.")
                self._write_order_log(
                    f"ORDER_NOT_SENT reason=order_placement_disabled side=BUY "
                    f"symbol={self.cfg.symbol} qty={self.cfg.order_quantity} price={price}"
                )

            self.strategy_state.position_qty += self.cfg.order_quantity
            self.strategy_state.last_signal = "BUY"

        elif signal == Signal.SELL:
            self.log.info(f"SELL SIGNAL price={price} qty={self.cfg.order_quantity}")
            self._write_event_log(
                f"SELL_SIGNAL price={price} qty={self.cfg.order_quantity}"
            )

            if self.enable_order_placement:
                self._write_order_log(
                    f"ORDER_ATTEMPT side=SELL symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} price={price}"
                )
                self.log.info("Real order placement not wired yet.")
                self._write_order_log(
                    f"ORDER_NOT_SENT reason=not_wired_yet side=SELL "
                    f"symbol={self.cfg.symbol} qty={self.cfg.order_quantity} price={price}"
                )
            else:
                self.log.info("Order placement disabled; signal logged only.")
                self._write_order_log(
                    f"ORDER_NOT_SENT reason=order_placement_disabled side=SELL "
                    f"symbol={self.cfg.symbol} qty={self.cfg.order_quantity} price={price}"
                )

            self.strategy_state.position_qty -= self.cfg.order_quantity
            self.strategy_state.last_signal = "SELL"

    def on_stop(self):
        self.log.info("AaplThresholdCycleNautilusStrategy stopped")
        self._write_event_log("STOP")

    def _event_log_path(self) -> Path:
        return Path("/work/logs/strategies/aapl_threshold_cycle_events.log")

    def _order_log_path(self) -> Path:
        return Path("/work/logs/orders/aapl_threshold_cycle_orders.log")

    def _write_event_log(self, message: str) -> None:
        path = self._event_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{ts} | {message}\n")

    def _write_order_log(self, message: str) -> None:
        path = self._order_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{ts} | {message}\n")