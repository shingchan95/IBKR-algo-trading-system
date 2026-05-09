from dataclasses import dataclass


@dataclass(frozen=True)
class AaplThresholdCycleConfig:
    symbol: str = "AAPL.NASDAQ"

    buy_below_or_equal: float = 280.0
    sell_above_or_equal: float = 285.0

    order_quantity: int = 1
    max_position: int = 1