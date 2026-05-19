# AGENTS.md

## Project

This is a Python trading system using:

- Nautilus Trader
- Interactive Brokers Gateway
- Docker
- A launcher under `infra/launchers/`
- Strategy folders under `strategies/`

Strategy folders normally contain:

- `config.py`
- `core.py`
- `nautilus_strategy.py`
- optional `README.md`

Main runtime files:

- `live/run_live.py` for paper/live execution
- `backtests/run_backtest.py` for backtesting
- `infra/launchers/launcher.py` for selecting strategy/mode/profile

## Main safety rules

This is a trading system, so safety is more important than speed.

Do not run live trading.

Do not run paper trading unless the user explicitly asks.

Do not set `ENABLE_ORDER_PLACEMENT=true`.

Do not modify IBKR account configuration unless the task explicitly asks.

Do not modify `live/run_live.py` unless the task explicitly asks.

Do not delete logs, datasets, `.env` files, or configuration files.

Do not touch files outside this repository.

Do not add API keys, account IDs, passwords, tokens, or private credentials to the repository.

Do not push to GitHub unless the user explicitly asks.

## Full-auto rules

The user may run Codex in full-auto mode.

Even in full-auto mode:

- Work on one task only.
- Keep changes small and reviewable.
- Stop after completing the requested task.
- Do not continue to the next task automatically.
- Do not run broker-connected commands.
- Do not run the launcher in paper or live mode.
- Do not run IBKR downloader scripts unless explicitly requested.

## Safe commands

You may run safe local inspection commands such as:

```bash
ls
find
grep
sed
cat
pwd
git status
git diff
```

You may run Python syntax checks such as:

```bash
python -m compileall backtests infra strategies scripts
```

You may run backtest-only commands if they do not connect to IBKR and do not place orders.

## Unsafe commands

Do not run these unless the user explicitly asks:

```bash
./infra/launchers/run_launcher.sh
python live/run_live.py
python scripts/download_ibkr_bid_ask_ticks.py
docker run
docker compose up
```

Do not run anything that connects to IBKR unless explicitly approved.

Do not run anything with:

```bash
ENABLE_ORDER_PLACEMENT=true
```

## Testing expectations

After code changes:

1. Run a syntax check if possible.
2. Show changed files.
3. Summarise what changed.
4. Explain the exact manual test command the user can run.
5. Stop.

Do not claim a test passed unless it was actually run.

## Coding style

Keep the project simple.

Prefer clear function names.

Prefer explicit error messages.

Avoid over-engineering.

Avoid large rewrites unless necessary.

For strategies:

- Put pure decision logic in `core.py`.
- Put Nautilus integration in `nautilus_strategy.py`.
- Put configurable values in `config.py`.

For backtesting:

- Prefer environment variables instead of hardcoded paths/symbols.
- Keep the runner generic.
- Do not hardcode AAPL except as a default.
