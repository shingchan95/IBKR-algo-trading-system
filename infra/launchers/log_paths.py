from pathlib import Path
from datetime import datetime

ROOT = Path("/home/dell-home-server/Documents/trading-system")
LOG_ROOT = ROOT / "logs"


def timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def run_log_path(strategy_name: str) -> Path:
    path = LOG_ROOT / "runs" / strategy_name
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{timestamp_now()}_raw.log"


def strategy_event_log_path(strategy_name: str) -> Path:
    path = LOG_ROOT / "strategies"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{strategy_name}_events.log"


def order_log_path(strategy_name: str) -> Path:
    path = LOG_ROOT / "orders"
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{strategy_name}_orders.log"