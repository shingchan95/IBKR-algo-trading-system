# CODEX_TASKS.md

## Goal

Improve this Nautilus Trader + IBKR trading system so it supports:

1. A real generic Nautilus backtest runner
2. Generic dataset selection from the launcher
3. IBKR historical BID/ASK tick download
4. Clear dataset documentation
5. A simple timed entry/exit lifecycle strategy

Work one task at a time.

After each task:

- show changed files
- run safe syntax checks
- explain how to test manually
- stop and wait for the next instruction

Do not run paper or live trading.

Do not set `ENABLE_ORDER_PLACEMENT=true`.

---

## Task 1: Replace fake backtest runner with generic Nautilus BacktestEngine runner

Replace `backtests/run_backtest.py`.

Requirements:

- Read `STRATEGY_NAME` from environment variables.
- Read `BACKTEST_DATA_CSV` from environment variables.
- Read `BACKTEST_DATA_TYPE` from environment variables.
- Read `BACKTEST_SYMBOL` from environment variables.
- Read `BACKTEST_VENUE` from environment variables.
- Read `BACKTEST_STARTING_BALANCE` from environment variables.
- Support `quote_ticks` first.
- Load CSV columns:
  - `timestamp`
  - `bid_price`
  - `ask_price`
- Allow extra CSV columns such as:
  - `bid_size`
  - `ask_size`
- Detect the strategy class from `strategies/<strategy_name>/nautilus_strategy.py`.
- The strategy class should end with `NautilusStrategy`.
- Use Nautilus `BacktestEngine`.
- Create a simulated venue using `BACKTEST_VENUE`.
- Create a test equity instrument using `BACKTEST_SYMBOL` and `BACKTEST_VENUE`.
- Add instrument, quote tick data, and selected strategy to the engine.
- Run the engine.
- Print reports if available.
- Give clear errors for:
  - missing CSV
  - missing required columns
  - missing strategy class
  - unsupported data type
- Do not modify `live/run_live.py`.

After editing, run:

```bash
python -m compileall backtests infra strategies
```

Then stop.

---

## Task 2: Update launcher for backtest dataset selection

Update `infra/launchers/launcher.py`.

Requirements:

- In backtest mode, list CSV files from `data/historical/*.csv`.
- Allow manual path entry.
- Convert host paths into Docker paths under `/work`.
- Pass these environment variables into Docker:
  - `BACKTEST_DATA_CSV`
  - `BACKTEST_DATA_TYPE`
  - `BACKTEST_SYMBOL`
  - `BACKTEST_VENUE`
  - `BACKTEST_STARTING_BALANCE`
  - `BACKTEST_TRADER_ID`
- For now, support only `quote_ticks`.
- Keep paper/live launcher behaviour unchanged.
- Print a clear summary before running Docker.

After editing, run:

```bash
python -m compileall backtests infra strategies
```

Then stop.

---

## Task 3: Add IBKR historical BID_ASK tick downloader

Create:

```text
scripts/download_ibkr_bid_ask_ticks.py
```

Requirements:

- Use `ibapi`.
- Connect to IB Gateway/TWS.
- Default host: `127.0.0.1`.
- Default paper port: `4002`.
- Default client id: `911`.
- Default symbol: `AAPL`.
- Default exchange: `NASDAQ`.
- Default currency: `USD`.
- Request historical ticks using `reqHistoricalTicks`.
- Use `whatToShow="BID_ASK"`.
- Save CSV to:

```text
data/historical/AAPL_NASDAQ_quote_ticks.csv
```

CSV columns:

- `timestamp`
- `bid_price`
- `ask_price`
- `bid_size`
- `ask_size`

Include command-line arguments for:

- symbol
- exchange
- output path
- tick count
- end datetime
- useRTH

Print clear messages if no data is returned.

Do not run this downloader unless explicitly asked.

After editing, run:

```bash
python -m compileall scripts
```

Then stop.

---

## Task 4: Add dataset documentation

Create:

```text
data/historical/README.md
```

Explain:

- What quote ticks are.
- Required CSV columns.
- Example CSV format.
- How the backtest runner uses the file.
- How to download data from IBKR using the script.
- Warning that quote tick availability depends on IBKR market data permissions.

Then stop.

---

## Task 5: Add timed_entry_exit strategy

Create:

```text
strategies/timed_entry_exit/
```

Files:

- `__init__.py`
- `config.py`
- `core.py`
- `nautilus_strategy.py`
- `README.md`

Purpose:

- Start strategy.
- Wait configurable seconds.
- Submit one market BUY.
- Wait configurable seconds.
- Submit one market SELL.
- Stop.

Safety:

- Respect `ENABLE_ORDER_PLACEMENT`.
- Limit max orders per run to 2.
- Log strategy events to `logs/strategies/timed_entry_exit_events.log`.
- Log orders to `logs/orders/timed_entry_exit_orders.log`.

Important:

- This strategy is for lifecycle testing only.
- It should not depend on quote data being present.

After editing, run:

```bash
python -m compileall strategies/timed_entry_exit
```

Then stop.

---

## Task 6: Review changed files

Review the repository after the previous tasks.

Check:

- no accidental paper/live trading behaviour changed
- no API keys were added
- no account IDs were exposed
- no unnecessary hardcoding
- clear errors are shown for missing data
- documentation explains how to use the new backtest flow

Run:

```bash
git status
git diff
python -m compileall backtests infra strategies scripts
```

Then stop.
