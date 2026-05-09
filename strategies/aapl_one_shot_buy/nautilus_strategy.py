import os
from datetime import datetime, timedelta
from pathlib import Path

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from strategies.aapl_one_shot_buy.config import AaplOneShotBuyConfig
from strategies.aapl_one_shot_buy.core import (
    AaplOneShotBuyCore,
    Signal,
    StrategyState,
)


class AaplOneShotBuyNautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = AaplOneShotBuyConfig()
        self.core = AaplOneShotBuyCore(self.cfg)
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
            f"Started one-shot buy strategy in {self.account_type.upper()} mode for {self.cfg.symbol}"
        )
        self.log.info(f"Enable order placement: {self.enable_order_placement}")
        self.log.info(f"Log quotes: {self.log_quotes}")
        self.log.info(
            f"Will attempt buy of {self.cfg.order_quantity} share(s) after {self.cfg.submit_after_seconds}s"
        )

        self._write_event_log(
            f"START account_type={self.account_type} "
            f"symbol={self.cfg.symbol} "
            f"qty={self.cfg.order_quantity} "
            f"order_enabled={self.enable_order_placement} "
            f"log_quotes={self.log_quotes}"
        )

        self.clock.set_timer(
            name="aapl_one_shot_buy_timer",
            interval=timedelta(seconds=self.cfg.submit_after_seconds),
            callback=self._submit_once,
        )

    def on_quote_tick(self, tick):
        bid = float(tick.bid_price) if tick and tick.bid_price else None
        ask = float(tick.ask_price) if tick and tick.ask_price else None

        self.strategy_state.last_seen_bid = bid
        self.strategy_state.last_seen_ask = ask

        if self.log_quotes:
            self.log.info(
                f"QUOTE symbol={self.cfg.symbol} bid={bid} ask={ask}"
            )

    def _submit_once(self, _event=None):
        bid = self.strategy_state.last_seen_bid
        ask = self.strategy_state.last_seen_ask

        self.log.info(
            f"SUBMIT_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask} "
            f"already_submitted={self.strategy_state.has_submitted_order}"
        )

        self._write_event_log(
            f"SUBMIT_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask}"
        )

        signal = self.core.should_submit_buy(self.strategy_state)

        if signal != Signal.BUY:
            self.log.info("No buy submission needed.")
            return

        qty = Quantity.from_int(self.cfg.order_quantity)

        if self.enable_order_placement:
            try:
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=qty,
                    time_in_force=TimeInForce.DAY,
                )

                self.submit_order(order)

                self.log.info(
                    f"BUY ORDER SUBMITTED symbol={self.cfg.symbol} qty={self.cfg.order_quantity}"
                )
                self._write_order_log(
                    f"ORDER_SUBMITTED side=BUY symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} bid={bid} ask={ask}"
                )

                self.strategy_state.has_submitted_order = True

            except Exception as e:
                self.log.error(f"BUY ORDER FAILED: {e}")
                self._write_order_log(
                    f"ORDER_FAILED side=BUY symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} error={e}"
                )
        else:
            self.log.info("Order placement disabled; would have submitted BUY 1 share.")
            self._write_order_log(
                f"ORDER_NOT_SENT reason=order_placement_disabled "
                f"side=BUY symbol={self.cfg.symbol} qty={self.cfg.order_quantity} "
                f"bid={bid} ask={ask}"
            )
            self.strategy_state.has_submitted_order = True

        if self.cfg.stop_after_submit:
            self.stop()

    def on_stop(self):
        self.log.info("AaplOneShotBuyNautilusStrategy stopped")
        self._write_event_log("STOP")

    def _event_log_path(self) -> Path:
        return Path("/work/logs/strategies/aapl_one_shot_buy_events.log")

    def _order_log_path(self) -> Path:
        return Path("/work/logs/orders/aapl_one_shot_buy_orders.log")

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