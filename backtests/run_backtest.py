import importlib
import os
import sys
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider


def env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)

    if value is None or value == "":
        print(f"Missing required environment variable: {name}")
        sys.exit(1)

    return value


def get_strategy_class(strategy_name: str):
    strategy_mod = importlib.import_module(
        f"strategies.{strategy_name}.nautilus_strategy"
    )

    for attr_name in dir(strategy_mod):
        attr = getattr(strategy_mod, attr_name)

        if isinstance(attr, type) and attr_name.endswith("NautilusStrategy"):
            return attr

    print(f"Could not find Nautilus strategy class for {strategy_name}")
    print("Expected a class name ending with 'NautilusStrategy'.")
    sys.exit(1)


def create_equity_instrument(symbol: str, venue_name: str):
    """
    Creates a Nautilus test equity instrument.

    Important:
    The generated instrument ID must match the strategy config symbol.
    Example:
        symbol='AAPL'
        venue_name='NASDAQ'
        instrument.id should become AAPL.NASDAQ
    """
    return TestInstrumentProvider.equity(
        symbol=symbol,
        venue=venue_name,
    )


def load_quote_ticks(csv_path: Path, instrument):
    if not csv_path.exists():
        print()
        print("Missing historical quote data file.")
        print(f"Expected file: {csv_path}")
        print()
        print("Required CSV format:")
        print("timestamp,bid_price,ask_price")
        print("2026-05-01 13:30:00+00:00,190.00,190.02")
        print("2026-05-01 13:31:00+00:00,190.10,190.12")
        print()
        sys.exit(1)

    df = pd.read_csv(csv_path)

    required_columns = {"timestamp", "bid_price", "ask_price"}
    missing = required_columns - set(df.columns)

    if missing:
        print(f"CSV is missing required columns: {sorted(missing)}")
        print("Required columns: timestamp, bid_price, ask_price")
        sys.exit(1)

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp")
    df = df.set_index("timestamp")

    df["bid_price"] = df["bid_price"].astype(float)
    df["ask_price"] = df["ask_price"].astype(float)

    if df.empty:
        print(f"No rows found in {csv_path}")
        sys.exit(1)

    wrangler = QuoteTickDataWrangler(instrument)
    ticks = wrangler.process(df)

    if not ticks:
        print("Wrangler produced no Nautilus quote ticks.")
        sys.exit(1)

    return ticks


def main():
    strategy_name = env("STRATEGY_NAME")

    backtest_data_csv = Path(env("BACKTEST_DATA_CSV"))
    backtest_data_type = env("BACKTEST_DATA_TYPE", "quote_ticks").lower()

    backtest_symbol = env("BACKTEST_SYMBOL", "AAPL")
    backtest_venue = env("BACKTEST_VENUE", "NASDAQ")

    starting_balance_raw = env("BACKTEST_STARTING_BALANCE", "100000")
    starting_balance = float(starting_balance_raw)

    trader_id_raw = env("BACKTEST_TRADER_ID", "BACKTESTER-001")

    print()
    print("=" * 80)
    print("NAUTILUS BACKTEST")
    print("=" * 80)
    print(f"Strategy: {strategy_name}")
    print(f"Data CSV: {backtest_data_csv}")
    print(f"Data type: {backtest_data_type}")
    print(f"Symbol: {backtest_symbol}")
    print(f"Venue: {backtest_venue}")
    print(f"Starting balance: {starting_balance:,.2f} USD")
    print()

    StrategyClass = get_strategy_class(strategy_name)

    if backtest_data_type != "quote_ticks":
        print(f"Unsupported BACKTEST_DATA_TYPE: {backtest_data_type}")
        print("Currently supported: quote_ticks")
        print()
        print("Later we can add: bars, trade_ticks")
        sys.exit(1)

    instrument = create_equity_instrument(
        symbol=backtest_symbol,
        venue_name=backtest_venue,
    )

    expected_instrument_id = f"{backtest_symbol}.{backtest_venue}"

    print(f"Backtest instrument: {instrument.id}")
    print(f"Expected strategy symbol: {expected_instrument_id}")
    print()

    ticks = load_quote_ticks(backtest_data_csv, instrument)

    first_ts = pd.Timestamp(ticks[0].ts_init, unit="ns", tz="UTC")
    last_ts = pd.Timestamp(ticks[-1].ts_init, unit="ns", tz="UTC")

    print(f"Loaded quote ticks: {len(ticks)}")
    print(f"Data start: {first_ts}")
    print(f"Data end:   {last_ts}")
    print()

    engine_config = BacktestEngineConfig(
        trader_id=TraderId(trader_id_raw),
    )

    engine = BacktestEngine(config=engine_config)

    venue = Venue(backtest_venue)

    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USD,
        starting_balances=[Money(starting_balance, USD)],
    )

    engine.add_instrument(instrument)
    engine.add_data(ticks)

    strategy = StrategyClass()
    engine.add_strategy(strategy=strategy)

    print("Starting Nautilus backtest...")
    print()

    engine.run()

    print()
    print("=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
    print()

    try:
        print("Account report:")
        print(engine.trader.generate_account_report(venue))
        print()
    except Exception as e:
        print(f"Could not generate account report: {e}")

    try:
        print("Order fills report:")
        print(engine.trader.generate_order_fills_report())
        print()
    except Exception as e:
        print(f"Could not generate order fills report: {e}")

    try:
        print("Positions report:")
        print(engine.trader.generate_positions_report())
        print()
    except Exception as e:
        print(f"Could not generate positions report: {e}")

    engine.dispose()


if __name__ == "__main__":
    main()