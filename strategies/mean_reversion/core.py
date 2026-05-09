from dataclasses import dataclass
from enum import Enum, auto

from strategies.mean_reversion.config import MeanReversionConfig


class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()


@dataclass
class StrategyState:
    position_qty: int = 0
    last_signal: str | None = None


class MeanReversionCore:
    def __init__(self, config: MeanReversionConfig):
        self.config = config

    def evaluate(self, value: float | None, state: StrategyState) -> Signal:
        if value is None:
            return Signal.HOLD

        if value >= self.config.trigger_value and state.position_qty == 0:
            return Signal.BUY

        if value < self.config.trigger_value and state.position_qty > 0:
            return Signal.SELL

        return Signal.HOLD
