from dataclasses import dataclass
from enum import Enum, auto

from strategies.aapl_threshold_cycle.config import AaplThresholdCycleConfig


class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()


@dataclass
class StrategyState:
    position_qty: int = 0
    last_signal: str | None = None


class AaplThresholdCycleCore:
    def __init__(self, config: AaplThresholdCycleConfig):
        self.config = config

    def evaluate(
        self,
        price: float | None,
        state: StrategyState,
    ) -> Signal:
        if price is None:
            return Signal.HOLD

        if (
            state.position_qty < self.config.max_position
            and price <= self.config.buy_below_or_equal
        ):
            return Signal.BUY

        if (
            state.position_qty > 0
            and price >= self.config.sell_above_or_equal
        ):
            return Signal.SELL

        return Signal.HOLD