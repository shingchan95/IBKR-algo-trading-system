from dataclasses import dataclass
from enum import Enum, auto

from strategies.timed_entry_exit.config import TimedEntryExitConfig


class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()
    STOP = auto()


class TradeState(Enum):
    WAITING_TO_BUY = auto()
    BUY_SUBMITTED = auto()
    WAITING_TO_SELL = auto()
    SELL_SUBMITTED = auto()
    DONE = auto()


@dataclass
class StrategyState:
    trade_state: TradeState = TradeState.WAITING_TO_BUY
    orders_submitted: int = 0

    has_submitted_buy: bool = False
    has_submitted_sell: bool = False

    last_seen_bid: float | None = None
    last_seen_ask: float | None = None


class TimedEntryExitCore:
    def __init__(self, config: TimedEntryExitConfig):
        self.config = config

    def should_submit_buy(self, state: StrategyState) -> Signal:
        if state.orders_submitted >= self.config.max_orders_per_run:
            return Signal.STOP

        if state.trade_state != TradeState.WAITING_TO_BUY:
            return Signal.HOLD

        if state.has_submitted_buy:
            return Signal.HOLD

        return Signal.BUY

    def should_submit_sell(self, state: StrategyState) -> Signal:
        if state.orders_submitted >= self.config.max_orders_per_run:
            return Signal.STOP

        if state.trade_state != TradeState.WAITING_TO_SELL:
            return Signal.HOLD

        if state.has_submitted_sell:
            return Signal.HOLD

        return Signal.SELL