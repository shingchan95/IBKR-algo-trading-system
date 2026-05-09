from dataclasses import dataclass


@dataclass(frozen=True)
class AaplOneShotBuyConfig:
    symbol: str = "AAPL.NASDAQ"
    order_quantity: int = 1
from dataclasses import dataclass


@dataclass(frozen=True)
class AaplOneShotBuyConfig:
    symbol: str = "AAPL.NASDAQ"
    order_quantity: int = 1

    # Logging / behavior
    submit_after_seconds: int = 5
    stop_after_submit: bool = True