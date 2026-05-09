import threading
import time

from nautilus_trader.adapters.interactive_brokers.config import (
    IBMarketDataTypeEnum,
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
)
from nautilus_trader.adapters.interactive_brokers.factories import (
    InteractiveBrokersLiveDataClientFactory,
)
from nautilus_trader.config import ImportableStrategyConfig, TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


TEST_INSTRUMENT = "AAPL.NASDAQ"


class IBQuoteLogger(Strategy):
    def on_start(self):
        self.log.info("Strategy on_start reached")

        instrument_id = InstrumentId.from_str(TEST_INSTRUMENT)
        instrument = self.cache.instrument(instrument_id)

        if instrument is None:
            self.log.error(f"Instrument not found in cache: {instrument_id}")
            self.stop()
            return

        self.log.info(f"Instrument found in cache: {instrument_id}")
        self.log.info(f"Subscribing to quote ticks for {instrument_id}")
        self.subscribe_quote_ticks(instrument_id)

    def on_quote_tick(self, tick):
        self.log.info(
            f"QUOTE {tick.instrument_id} bid={tick.bid_price} ask={tick.ask_price}"
        )

    def on_stop(self):
        self.log.info("Strategy on_stop reached")


IB_HOST = "127.0.0.1"
IB_PORT = 4002
IB_CLIENT_ID = 1

instrument_provider = InteractiveBrokersInstrumentProviderConfig(
    load_ids=frozenset([TEST_INSTRUMENT]),
)

data_config = InteractiveBrokersDataClientConfig(
    ibg_host=IB_HOST,
    ibg_port=IB_PORT,
    ibg_client_id=IB_CLIENT_ID,
    instrument_provider=instrument_provider,
    market_data_type=IBMarketDataTypeEnum.DELAYED,
)

node_config = TradingNodeConfig(
    trader_id="IB-PAPER-DATA-001",
    data_clients={"IB": data_config},
    exec_clients={},
    strategies=[
        ImportableStrategyConfig(
            strategy_path="__main__:IBQuoteLogger",
            config_path="nautilus_trader.config:StrategyConfig",
            config={},
        )
    ],
)

node = TradingNode(config=node_config)
node.add_data_client_factory("IB", InteractiveBrokersLiveDataClientFactory)


def stop_later():
    time.sleep(90)
    print("Stopping node...")
    node.stop()


if __name__ == "__main__":
    print("Building node...")
    node.build()

    print("Starting node...")
    threading.Thread(target=stop_later, daemon=True).start()

    node.run()

    print("Finished cleanly.")