import os
from datetime import datetime, timedelta
from pathlib import Path

from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity
from nautilus_trader.trading.strategy import Strategy

from strategies.timed_entry_exit.config import TimedEntryExitConfig
from strategies.timed_entry_exit.core import (
    Signal,
    StrategyState,
    TimedEntryExitCore,
    TradeState,
)


class TimedEntryExitNautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = TimedEntryExitConfig()
        self.core = TimedEntryExitCore(self.cfg)
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
            f"Started timed entry/exit strategy in {self.account_type.upper()} mode "
            f"for {self.cfg.symbol}"
        )
        self.log.info(f"Enable order placement: {self.enable_order_placement}")
        self.log.info(f"Log quotes: {self.log_quotes}")
        self.log.info(
            f"Will attempt BUY after {self.cfg.submit_buy_after_seconds}s, "
            f"then SELL after {self.cfg.submit_sell_after_seconds}s"
        )

        self._write_event_log(
            f"START account_type={self.account_type} "
            f"symbol={self.cfg.symbol} "
            f"qty={self.cfg.order_quantity} "
            f"order_enabled={self.enable_order_placement} "
            f"log_quotes={self.log_quotes}"
        )

        self.clock.set_timer(
            name="timed_entry_exit_buy_timer",
            interval=timedelta(seconds=self.cfg.submit_buy_after_seconds),
            callback=self._submit_buy_once,
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

    def _submit_buy_once(self, _event=None):
        bid = self.strategy_state.last_seen_bid
        ask = self.strategy_state.last_seen_ask

        self.log.info(
            f"BUY_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask} "
            f"already_submitted={self.strategy_state.has_submitted_buy}"
        )

        self._write_event_log(
            f"BUY_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask}"
        )

        signal = self.core.should_submit_buy(self.strategy_state)

        if signal == Signal.STOP:
            self.log.info("Max order limit reached before BUY. Stopping strategy.")
            self._write_event_log("STOP reason=max_order_limit_before_buy")
            self.stop()
            return

        if signal != Signal.BUY:
            self.log.info("No BUY submission needed.")
            return

        self._submit_market_order(OrderSide.BUY, "BUY", bid, ask)

        self.strategy_state.has_submitted_buy = True
        self.strategy_state.trade_state = TradeState.WAITING_TO_SELL

        self._write_event_log(
            f"STATE_CHANGE new_state={self.strategy_state.trade_state.name}"
        )

        self.clock.set_timer(
            name="timed_entry_exit_sell_timer",
            interval=timedelta(seconds=self.cfg.submit_sell_after_seconds),
            callback=self._submit_sell_once,
        )

    def _submit_sell_once(self, _event=None):
        bid = self.strategy_state.last_seen_bid
        ask = self.strategy_state.last_seen_ask

        self.log.info(
            f"SELL_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask} "
            f"already_submitted={self.strategy_state.has_submitted_sell}"
        )

        self._write_event_log(
            f"SELL_CHECK symbol={self.cfg.symbol} last_bid={bid} last_ask={ask}"
        )

        signal = self.core.should_submit_sell(self.strategy_state)

        if signal == Signal.STOP:
            self.log.info("Max order limit reached before SELL. Stopping strategy.")
            self._write_event_log("STOP reason=max_order_limit_before_sell")
            self.stop()
            return

        if signal != Signal.SELL:
            self.log.info("No SELL submission needed.")
            return

        self._submit_market_order(OrderSide.SELL, "SELL", bid, ask)

        self.strategy_state.has_submitted_sell = True
        self.strategy_state.trade_state = TradeState.DONE

        self._write_event_log(
            f"STATE_CHANGE new_state={self.strategy_state.trade_state.name}"
        )

        if self.cfg.stop_after_sell:
            self.stop()

    def _submit_market_order(
        self,
        order_side: OrderSide,
        side_label: str,
        bid: float | None,
        ask: float | None,
    ) -> None:
        qty = Quantity.from_int(self.cfg.order_quantity)

        if self.strategy_state.orders_submitted >= self.cfg.max_orders_per_run:
            self.log.warning("Max orders per run reached. Order not submitted.")
            self._write_order_log(
                f"ORDER_NOT_SENT reason=max_orders_per_run_reached "
                f"side={side_label} symbol={self.cfg.symbol} "
                f"qty={self.cfg.order_quantity} bid={bid} ask={ask}"
            )
            return

        if self.enable_order_placement:
            try:
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    order_side=order_side,
                    quantity=qty,
                    time_in_force=TimeInForce.DAY,
                )

                self.submit_order(order)

                self.strategy_state.orders_submitted += 1

                self.log.info(
                    f"{side_label} ORDER SUBMITTED "
                    f"symbol={self.cfg.symbol} qty={self.cfg.order_quantity}"
                )

                self._write_order_log(
                    f"ORDER_SUBMITTED side={side_label} symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} bid={bid} ask={ask} "
                    f"orders_submitted={self.strategy_state.orders_submitted}"
                )

            except Exception as e:
                self.log.error(f"{side_label} ORDER FAILED: {e}")
                self._write_order_log(
                    f"ORDER_FAILED side={side_label} symbol={self.cfg.symbol} "
                    f"qty={self.cfg.order_quantity} error={e}"
                )

        else:
            self.strategy_state.orders_submitted += 1

            self.log.info(
                f"Order placement disabled; would have submitted "
                f"{side_label} {self.cfg.order_quantity} share(s)."
            )

            self._write_order_log(
                f"ORDER_NOT_SENT reason=order_placement_disabled "
                f"side={side_label} symbol={self.cfg.symbol} "
                f"qty={self.cfg.order_quantity} bid={bid} ask={ask} "
                f"orders_submitted={self.strategy_state.orders_submitted}"
            )

    def on_stop(self):
        self.log.info("TimedEntryExitNautilusStrategy stopped")
        self._write_event_log(
            f"STOP final_state={self.strategy_state.trade_state.name} "
            f"orders_submitted={self.strategy_state.orders_submitted}"
        )

    def _event_log_path(self) -> Path:
        return Path("/work/logs/strategies/timed_entry_exit_events.log")

    def _order_log_path(self) -> Path:
        return Path("/work/logs/orders/timed_entry_exit_orders.log")

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