from dataclasses import dataclass


@dataclass(frozen=True)
class SimplePriceWatchConfig:
    trigger_symbol: str = "MSFT.NASDAQ"
    trade_symbol: str = "AAPL.NASDAQ"

    buy_trigger_price: float = 420.0
    buy_trade_max_price: float = 250.0

    sell_trigger_price: float = 390.0
    sell_trade_min_price: float = 255.0

    order_quantity: int = 1
    allow_short: bool = False
    max_position: int = 1