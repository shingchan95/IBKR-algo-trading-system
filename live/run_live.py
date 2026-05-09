import importlib
import os
import threading
import time

from nautilus_trader.adapters.interactive_brokers.config import (
    IBMarketDataTypeEnum,
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersExecClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
    InteractiveBrokersLiveExecClientFactory,
)
from nautilus_trader.config import ImportableStrategyConfig, TradingNodeConfig
from nautilus_trader.live.node import TradingNode


def get_market_data_type(value: str):
    if value.upper() == "REALTIME":
        return IBMarketDataTypeEnum.REALTIME
    return IBMarketDataTypeEnum.DELAYED


def get_strategy_config_instance(strategy_name: str):
    config_mod = importlib.import_module(f"strategies.{strategy_name}.config")

    strategy_cfg_class = None
    for attr_name in dir(config_mod):
        attr = getattr(config_mod, attr_name)
        if attr_name.endswith("Config") and isinstance(attr, type):
            strategy_cfg_class = attr
            break

    if strategy_cfg_class is None:
        print(f"Could not find config class in strategies.{strategy_name}.config")
        raise SystemExit(1)

    return strategy_cfg_class()


def get_load_ids(strategy_cfg):
    if hasattr(strategy_cfg, "trigger_symbol") and hasattr(strategy_cfg, "trade_symbol"):
        return frozenset([strategy_cfg.trigger_symbol, strategy_cfg.trade_symbol])

    if hasattr(strategy_cfg, "symbol"):
        return frozenset([strategy_cfg.symbol])

    print("Could not determine instruments to load from strategy config")
    raise SystemExit(1)


def main():
    strategy_name = os.environ.get("STRATEGY_NAME")
    if not strategy_name:
        print("STRATEGY_NAME not provided")
        raise SystemExit(1)

    trading_account_type = os.environ.get("TRADING_ACCOUNT_TYPE", "paper")
    ib_host = os.environ.get("IB_HOST", "127.0.0.1")
    ib_port = int(os.environ.get("IB_PORT", "4002"))
    ib_client_id = int(os.environ.get("IB_CLIENT_ID", "11"))
    ib_account_id = os.environ.get("IB_ACCOUNT_ID", "")
    trader_id_suffix = os.environ.get("TRADER_ID_SUFFIX", "PAPER")
    market_data_type = os.environ.get("MARKET_DATA_TYPE", "DELAYED")
    run_seconds = int(os.environ.get("RUN_SECONDS", "300"))

    strategy_cfg = get_strategy_config_instance(strategy_name)
    load_ids = get_load_ids(strategy_cfg)

    instrument_provider = InteractiveBrokersInstrumentProviderConfig(
        load_ids=load_ids,
    )

    data_config = InteractiveBrokersDataClientConfig(
        ibg_host=ib_host,
        ibg_port=ib_port,
        ibg_client_id=ib_client_id,
        instrument_provider=instrument_provider,
        market_data_type=get_market_data_type(market_data_type),
    )

    exec_config = InteractiveBrokersExecClientConfig(
        ibg_host=ib_host,
        ibg_port=ib_port,
        ibg_client_id=ib_client_id,
        account_id=ib_account_id,
        instrument_provider=instrument_provider,
    )

    strategy_class_name = "".join(part.capitalize() for part in strategy_name.split("_")) + "NautilusStrategy"
    strategy_module_path = f"strategies.{strategy_name}.nautilus_strategy:{strategy_class_name}"

    node_config = TradingNodeConfig(
        trader_id=f"{strategy_name.upper()}-{trader_id_suffix}-001",
        data_clients={"IB": data_config},
        exec_clients={"IB": exec_config},
        strategies=[
            ImportableStrategyConfig(
                strategy_path=strategy_module_path,
                config_path="nautilus_trader.config:StrategyConfig",
                config={},
            )
        ],
    )

    node = TradingNode(config=node_config)
    node.add_data_client_factory("IB", InteractiveBrokersLiveDataClientFactory)
    node.add_exec_client_factory("IB", InteractiveBrokersLiveExecClientFactory)

    if run_seconds > 0:
        def stop_later():
            time.sleep(run_seconds)
            print("Stopping node...")
            node.stop()

        threading.Thread(target=stop_later, daemon=True).start()

    print(f"Loaded live strategy: {strategy_name}")
    print(f"Account type: {trading_account_type}")
    print(f"IB host: {ib_host}")
    print(f"IB port: {ib_port}")
    print(f"Market data type: {market_data_type}")
    print(f"Trader ID suffix: {trader_id_suffix}")
    print(f"Load IDs: {sorted(load_ids)}")
    print(f"Run seconds: {run_seconds} (0 means nonstop)")

    node.build()
    node.run()


if __name__ == "__main__":
    main()