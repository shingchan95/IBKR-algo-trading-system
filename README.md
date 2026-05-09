~/Documents/trading-system/infra/launchers/run_launcher.sh

# Trading System Documentation

## Purpose of this document

This document explains the current trading system structure, how it works, what each file does, how strategies are expected to be written, how live and paper execution are launched, how logging works, and the important lessons learned from testing.

The goal is that this document can be given to a new chat so it can understand the system and help write new strategies that fit the same structure.

---

# 1. High-level architecture

The trading system is a Python-based strategy framework built around:

- **Nautilus Trader** for strategy lifecycle, order submission, event handling, and broker integration
- **Interactive Brokers Gateway** for broker connectivity
- **Docker** for running the strategy environment consistently
- **A launcher** for selecting which strategy and mode to run
- **A per-strategy folder structure** so each strategy is self-contained

The basic idea is:

1. A strategy lives inside its own folder under `strategies/`
2. That strategy has its own:
   - `config.py`
   - `core.py`
   - `nautilus_strategy.py`
3. The launcher asks what to run
4. The launcher starts a Docker container
5. The container runs either:
   - `live/run_live.py` for paper/live execution
   - `backtests/run_backtest.py` for backtesting
6. `run_live.py` dynamically imports the selected strategy
7. Nautilus Trader builds the IB data/execution clients and runs the strategy

---

# 2. Current project structure

```text
Documents/trading-system/
├── backtests/
│   ├── __init__.py
│   └── run_backtest.py
├── infra/
│   ├── __init__.py
│   ├── docker/
│   │   └── Dockerfile
│   └── launchers/
│       ├── __init__.py
│       ├── config.py
│       ├── launcher.py
│       ├── logging_config.py
│       ├── log_paths.py
│       └── run_launcher.sh
├── live/
│   ├── __init__.py
│   └── run_live.py
├── logs/
│   ├── orders/
│   ├── runs/
│   └── strategies/
├── strategies/
│   ├── __init__.py
│   ├── aapl_one_shot_buy/
│   │   ├── config.py
│   │   ├── core.py
│   │   ├── nautilus_strategy.py
│   │   └── README.md
│   ├── aapl_threshold_cycle/
│   │   ├── config.py
│   │   ├── core.py
│   │   ├── nautilus_strategy.py
│   │   └── README.md
│   ├── mean_reversion/
│   │   ├── config.py
│   │   ├── core.py
│   │   ├── nautilus_strategy.py
│   │   └── README.md
│   ├── simple_price_watch/
│   │   ├── config.py
│   │   ├── core.py
│   │   ├── nautilus_strategy.py
│   │   └── README.md
│   └── TEMPLATE_STRATEGY/
│       ├── config.py
│       ├── core.py
│       ├── nautilus_strategy.py
│       └── README.md
├── tests/
│   ├── ib_market_data_test.py
│   ├── ib_smoke_test.py
│   └── ib_tiny_order_test.py
└── README.md
```

---

# 3. Main design idea

Each strategy should be split into three parts:

## 3.1 `config.py`

This is where strategy-specific settings live.

Examples:

- symbol(s)
- thresholds
- order quantity
- timings
- flags

This file should usually contain a frozen dataclass.

Example pattern:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MyStrategyConfig:
    symbol: str = "AAPL.NASDAQ"
    order_quantity: int = 1
```

## 3.2 `core.py`

This is the strategy logic layer.

It should contain:

- enums like `Signal`
- state dataclasses like `StrategyState`
- a core class that evaluates rules and returns signals

This lets the actual decision logic stay separate from Nautilus-specific code.

Example pattern:

```python
class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()
```

## 3.3 `nautilus_strategy.py`

This is the Nautilus integration layer.

It handles:

- subscribing to market data
- reading environment variables
- reading/writing logs
- calling the core logic
- creating and submitting Nautilus orders
- reacting to startup/shutdown

This file is the bridge between:

- strategy logic in `core.py`
- runtime config in environment variables
- broker + market data through Nautilus

---

# 4. Runtime modes

The system supports three conceptual modes:

## 4.1 Backtest

Uses `backtests/run_backtest.py`

This is intended for offline strategy testing.

At the moment it is a placeholder structure, but the idea is:

- choose a strategy
- load historical data
- run the selected strategy over that data

## 4.2 Paper

Uses `live/run_live.py` with paper account settings.

This means:

- connect to IB Gateway paper port
- send paper orders
- observe broker behavior without real money

## 4.3 Live

Uses `live/run_live.py` with live account settings.

This means:

- connect to IB Gateway live port
- send real orders if enabled

Important: paper and live are determined by the launcher config, not by the strategy itself.

---

# 5. Launcher system

## 5.1 What the launcher does

The launcher is a Python CLI that asks the user:

1. What area to run:
   - test
   - research
   - strategy
   - create\_strategy
2. Which strategy to use
3. Which mode to use:
   - backtest
   - paper
   - live
4. Which run profile to use:
   - quick\_test
   - debug
   - long\_run
5. How long to run

It then builds the correct Docker command and runs it.

## 5.2 Main launcher files

### `infra/launchers/run_launcher.sh`

Small shell wrapper that changes directory to project root and runs the Python launcher module.

### `infra/launchers/launcher.py`

The main interactive launcher.

Responsibilities:

- show menus
- list strategy folders
- create strategy templates
- map selected mode to gateway config
- set environment variables for the container
- run the Docker command
- store raw run logs

### `infra/launchers/config.py`

Stores shared launcher config, especially paper/live gateway settings.

Typical contents:

- project root path
- Docker image name
- paper IB host/port/client/account configuration
- live IB host/port/client/account configuration
- helper `get_gateway_config(mode)`

### `infra/launchers/logging_config.py`

Stores simple default logging preferences.

### `infra/launchers/log_paths.py`

Creates paths for:

- raw run logs
- strategy event logs
- order logs

---

# 6. Docker setup

## 6.1 Why Docker is used

Docker is used so the trading runtime is consistent.

It avoids needing to install Nautilus Trader and all dependencies directly on the host Python environment.

## 6.2 Dockerfile

Located at:

```text
infra/docker/Dockerfile
```

Typical design:

- start from Nautilus Jupyter image
- install Nautilus Trader IB dependencies
- run strategy scripts inside container

## 6.3 Why strategies are not baked into image

Strategies are mounted from the host via:

```text
-v /home/dell-home-server/Documents/trading-system:/work
```

That means:

- strategy files can be edited on host
- container sees latest files
- no image rebuild required for every strategy edit

---

# 7. Live runner

## `live/run_live.py`

This is the main entry point for paper/live strategy execution.

Responsibilities:

1. Read environment variables passed by launcher
2. Import selected strategy config module dynamically
3. Detect the config class inside that strategy module
4. Build instrument provider config
5. Build IB data client config
6. Build IB execution client config
7. Build `TradingNodeConfig`
8. Register Nautilus IB factories
9. Build and run the node
10. Optionally auto-stop after configured time

Key environment variables used:

- `STRATEGY_NAME`
- `TRADING_ACCOUNT_TYPE`
- `IB_HOST`
- `IB_PORT`
- `IB_CLIENT_ID`
- `IB_ACCOUNT_ID`
- `TRADER_ID_SUFFIX`
- `MARKET_DATA_TYPE`
- `ENABLE_ORDER_PLACEMENT`
- `LOG_QUOTES`
- `RUN_SECONDS`

---

# 8. Backtest runner

## `backtests/run_backtest.py`

This is the backtest entry point.

Currently it is a simplified placeholder, but the intended pattern is:

1. Read `STRATEGY_NAME`
2. Dynamically import that strategy’s config and core modules
3. Load backtest data
4. Instantiate backtest engine / strategy
5. Run and save results

---

# 9. Logging system

The logging system has three layers.

## 9.1 Raw run logs

Stored under:

```text
logs/runs/<strategy_name>/
```

These contain everything printed during the run, including:

- Nautilus logs
- IB logs
- strategy logs
- warnings/errors

They are timestamped per run.

Purpose:

- full debugging
- forensic review
- environment diagnosis

## 9.2 Strategy event logs

Stored under:

```text
logs/strategies/
```

Example:

```text
aapl_one_shot_buy_events.log
```

These are intentionally cleaner than raw logs.

Typical entries:

- START
- SUBMIT\_CHECK
- BUY\_SIGNAL
- SELL\_SIGNAL
- STOP

Purpose:

- quickly see what the strategy itself decided

## 9.3 Order logs

Stored under:

```text
logs/orders/
```

Example:

```text
aapl_one_shot_buy_orders.log
```

Typical entries:

- ORDER\_NOT\_SENT
- ORDER\_SUBMITTED
- ORDER\_FAILED

Purpose:

- quickly confirm whether an order was actually sent

---

# 10. Existing strategies and what they taught us

## 10.1 `simple_price_watch`

A basic monitoring strategy.

Purpose:

- subscribe to symbols
- observe quote behavior
- help test general strategy plumbing

## 10.2 `aapl_threshold_cycle`

A threshold-based test strategy.

Purpose:

- buy when price is below threshold
- sell when price is above threshold
- repeatedly test logic flow

What was learned:

- the strategy structure worked
- the core logic worked
- but the delayed IB market data feed did **not** populate usable `bid/ask` values in cache
- timer-based polling confirmed repeated `bid=None` and `ask=None`
- therefore the strategy never entered a buy condition

This was a valuable test because it separated:

- logic problems from
- data availability problems

## 10.3 `aapl_one_shot_buy`

A simple fresh test strategy.

Purpose:

- subscribe to AAPL quotes
- wait a few seconds
- submit a single market buy order for 1 share
- stop immediately after submission

What was learned:

- strategy lifecycle works
- timer works
- Nautilus order submission works
- IB paper accepted the order
- when market is closed, IB accepts the order and queues it for the next market open

This strategy proved the end-to-end system works for order submission even though quote data was not available.

---

# 11. Important behavior discovered during testing

## 11.1 Paper delayed market data may not produce usable bid/ask

In this setup, IB paper with delayed data often produced:

- warnings about delayed market data
- volume warnings
- but no usable bid/ask in strategy cache

This means a strategy that depends on live quote cache may not work reliably in this specific environment.

## 11.2 Order placement can still work without quote data

The one-shot buy strategy proved that you can still submit a market order even if bid/ask is missing in strategy logs.

## 11.3 Existing paper account positions/orders create noise

The paper account already had old AAPL state, which caused repeated startup reconciliation warnings such as:

- residual position
- residual order
- overfill warnings

These do not necessarily break strategy execution, but they make logs noisy and can confuse testing.

## 11.4 The strategy stopping does not necessarily cancel the broker order

For the one-shot buy strategy:

- the strategy submitted the order
- IB accepted it
- the strategy then stopped
- the accepted broker order still remained at IB

This is important: stopping the strategy does not automatically mean the accepted broker-side order disappears.

---

# 12. Environment variables and what they mean

## `STRATEGY_NAME`

The selected strategy folder name.

Used by `run_live.py` / `run_backtest.py` to dynamically import:

- `strategies.<name>.config`
- `strategies.<name>.nautilus_strategy`

## `TRADING_ACCOUNT_TYPE`

Usually `paper` or `live`.

Used for logging and for understanding mode.

## `IB_HOST`

IB Gateway host, usually `127.0.0.1`.

## `IB_PORT`

The IB Gateway port.

Typical pattern:

- paper: `4002`
- live: `4001`

## `IB_CLIENT_ID`

The client id used when connecting to IB.

Useful for keeping different processes distinct.

## `IB_ACCOUNT_ID`

The IB account id, for example paper account like `DUP...`.

Required by Nautilus execution client.

## `TRADER_ID_SUFFIX`

A suffix such as `PAPER` or `LIVE` used in trader id.

## `MARKET_DATA_TYPE`

Usually:

- `DELAYED`
- `REALTIME`

For paper testing in this setup, delayed data was commonly used.

## `ENABLE_ORDER_PLACEMENT`

Critical flag.

If `false`:

- strategies can log signals
- but will not send real/paper broker orders

If `true`:

- strategies can submit broker orders

## `LOG_QUOTES`

Controls whether quote-related debug lines are logged.

## `RUN_SECONDS`

How long the live runner should run before stopping.

Convention used:

- `0` means run forever
- positive integer means auto-stop after that many seconds

---

# 13. Run profiles

The launcher uses three logical run profiles.

## 13.1 `quick_test`

Purpose:

- quick validation that strategy starts and runs

Typical behavior:

- quote logging off
- default run time around 300 seconds unless overridden

## 13.2 `debug`

Purpose:

- inspect data flow and strategy logic

Typical behavior:

- quote logging on
- default run time around 300 seconds unless overridden

## 13.3 `long_run`

Purpose:

- keep strategy alive for extended runtime

Typical behavior:

- quote logging off by default
- default run time of 0 (nonstop) unless overridden

---

# 14. How a new strategy should be written

A new strategy should follow the same pattern.

## Step 1: create a folder

Example:

```text
strategies/my_new_strategy/
```

## Step 2: add `config.py`

Define constants and tunable parameters.

## Step 3: add `core.py`

Define:

- state
- signal enum
- pure logic methods

## Step 4: add `nautilus_strategy.py`

Implement Nautilus-specific behavior:

- load config
- subscribe to data
- read env vars
- call core logic
- submit orders if needed
- log events

## Step 5: optionally add `README.md`

Document what the strategy is for.

---

# 15. Recommended strategy writing rules

To keep future strategies consistent, follow these rules.

## 15.1 Keep logic in `core.py`

Do not bury all decision logic inside Nautilus callbacks if it can be kept cleanly in `core.py`.

## 15.2 Keep Nautilus integration in `nautilus_strategy.py`

This file should be the runtime shell around your core logic.

## 15.3 Log important events explicitly

At minimum log:

- START
- critical checks
- BUY/SELL signals
- ORDER\_SUBMITTED / ORDER\_FAILED / ORDER\_NOT\_SENT
- STOP

## 15.4 Make strategy parameters configurable in `config.py`

Do not hardcode everything directly in Nautilus callbacks.

## 15.5 Assume market data may be missing

Especially in paper/delayed environments, build strategies defensively.

For example:

- log missing price data
- allow fallback sources if needed
- do not assume quote cache is always populated

---

# 16. Known pain points

## 16.1 IB delayed quote data in paper mode

This is currently the biggest data-side limitation.

Some strategies may need a different data source than quote ticks if the account lacks proper subscriptions.

## 16.2 Existing broker state causes noisy startup

Old positions/orders in the paper account lead to repeated reconciliation warnings and noise.

## 16.3 Logs can be noisy without separation

Raw Nautilus/IB logs are useful, but strategy event logs and order logs are much easier to read.

## 16.4 Stopping strategy immediately after submit may hide later events

For one-shot strategies, if the strategy stops right after order submission, later events like fill/cancel may not be seen inside that strategy instance unless the order remains externally visible in IB.

---

# 17. What has already been proven to work

The following are confirmed working in this system:

- launcher can select strategies and modes
- Docker runtime works
- `run_live.py` can dynamically import strategies
- Nautilus connects to IB Gateway
- paper account can be found and used
- strategy startup lifecycle works
- timer-based callbacks work
- order submission from strategy works
- IB paper can accept a submitted order
- raw logs and per-strategy logs can be written

---

# 18. What is not fully solved yet

The following remain open/imperfect:

- reliable quote price availability in paper delayed mode
- cleaner management of existing broker account state
- robust backtesting implementation
- strategy-level handling of fills/accept/reject callbacks in a reusable way
- central shared abstractions for more advanced strategy/order management

---

# 19. Suggested next evolution of the project

A sensible next step would be to add shared utilities for:

- order submission helpers
- standard event logging mixins/helpers
- optional broker state sync on startup
- shared base strategy patterns
- a more robust backtest engine path

This could eventually become a higher-level shared layer for all strategies.

---

# 20. Recommended use of README vs other docs

## Using `README.md`

A top-level `README.md` is a good idea for:

- explaining the whole system
- onboarding a new chat or a new developer
- describing architecture and workflow

## Better structure recommendation

The best long-term approach is:

- top-level `README.md` → short overview and quick start
- `docs/ARCHITECTURE.md` → deep system explanation
- `docs/STRATEGY_GUIDE.md` → how to write new strategies
- per-strategy `README.md` → strategy-specific notes

That said, if the immediate goal is to paste one document into a new chat, then a single detailed `README.md` is completely fine.

---

# 21. Best summary for a future chat

This system is a Docker-run, Nautilus Trader + IB Gateway based strategy framework. Strategies live under `strategies/<strategy_name>/` and are split into `config.py`, `core.py`, and `nautilus_strategy.py`. The launcher chooses a strategy and runtime mode, passes environment variables into Docker, and runs either `live/run_live.py` or `backtests/run_backtest.py`. Logging is split into raw run logs, strategy event logs, and order logs. Paper delayed quote data has been unreliable for bid/ask-driven strategies, but a one-shot market buy strategy has already proven that order submission from Nautilus through IB Gateway paper mode works successfully.

---

# 22. Final note for future strategy generation

If a future chat is asked to write a new strategy for this system, it should:

1. create a new strategy folder under `strategies/`
2. write `config.py`
3. write `core.py`
4. write `nautilus_strategy.py`
5. assume launcher + Docker + `run_live.py` already exist
6. use environment variables provided by launcher
7. write to strategy event log and order log
8. avoid assuming quote data is always available in paper delayed mode

