from dataclasses import dataclass
from pathlib import Path


ROOT = Path("/home/dell-home-server/Documents/trading-system")
IMAGE = "nautilus-ib-test"


@dataclass(frozen=True)
class GatewayModeConfig:
    mode: str
    ib_host: str
    ib_port: int
    ib_client_id: int
    ib_account_id: str
    trader_id_suffix: str
    market_data_type: str
    enable_order_placement: bool


PAPER_CONFIG = GatewayModeConfig(
    mode="paper",
    ib_host="127.0.0.1",
    ib_port=4002,
    ib_client_id=11,
    ib_account_id="DUP439482",
    trader_id_suffix="PAPER",
    market_data_type="DELAYED",
    enable_order_placement=True,
)

LIVE_CONFIG = GatewayModeConfig(
    mode="live",
    ib_host="127.0.0.1",
    ib_port=4001,
    ib_client_id=21,
    ib_account_id="",
    trader_id_suffix="LIVE",
    market_data_type="REALTIME",
    enable_order_placement=False,
)


def get_gateway_config(mode: str) -> GatewayModeConfig:
    mode = mode.lower().strip()
    if mode == "paper":
        return PAPER_CONFIG
    if mode == "live":
        return LIVE_CONFIG
    raise ValueError(f"Unsupported mode: {mode}")