from dataclasses import dataclass
from enum import Enum, auto

from strategies.aapl_one_shot_buy.config import AaplOneShotBuyConfig


class Signal(Enum):
    HOLD = auto()
    BUY = auto()


@dataclass
class StrategyState:
    has_submitted_order: bool = False
    last_seen_bid: float | None = None
    last_seen_ask: float | None = None


class AaplOneShotBuyCore:
    def __init__(self, config: AaplOneShotBuyConfig):
        self.config = config

    def should_submit_buy(self, state: StrategyState) -> Signal:
        if state.has_submitted_order:
            return Signal.HOLD
        return Signal.BUY