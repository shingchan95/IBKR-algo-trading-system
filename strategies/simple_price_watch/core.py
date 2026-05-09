from dataclasses import dataclass
from enum import Enum, auto

from strategies.simple_price_watch.config import SimplePriceWatchConfig


class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()


@dataclass
class StrategyState:
    position_qty: int = 0
    last_signal: str | None = None


class SimplePriceWatchCore:
    def __init__(self, config: SimplePriceWatchConfig):
        self.config = config

    def evaluate(
        self,
        trigger_price: float | None,
        trade_price: float | None,
        state: StrategyState,
    ) -> Signal:
        if trigger_price is None or trade_price is None:
            return Signal.HOLD

        if (
            state.position_qty < self.config.max_position
            and trigger_price >= self.config.buy_trigger_price
            and trade_price <= self.config.buy_trade_max_price
        ):
            return Signal.BUY

        if (
            state.position_qty > 0
            and trigger_price <= self.config.sell_trigger_price
            and trade_price >= self.config.sell_trade_min_price
        ):
            return Signal.SELL

        return Signal.HOLD