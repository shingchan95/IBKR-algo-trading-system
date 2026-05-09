from dataclasses import dataclass


@dataclass(frozen=True)
class TimedEntryExitConfig:
    symbol: str = "AAPL.NASDAQ"
    order_quantity: int = 1

    # Behaviour
    submit_buy_after_seconds: int = 5
    submit_sell_after_seconds: int = 60

    # Safety
    stop_after_sell: bool = True
    max_orders_per_run: int = 2