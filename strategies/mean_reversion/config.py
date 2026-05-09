from dataclasses import dataclass


@dataclass(frozen=True)
class MeanReversionConfig:
    symbol: str = "AAPL.NASDAQ"
    trigger_value: float = 100.0
    order_quantity: int = 1
