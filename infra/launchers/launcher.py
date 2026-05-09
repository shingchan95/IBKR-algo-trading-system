from pathlib import Path
import subprocess
import sys

from infra.launchers.config import ROOT, IMAGE, get_gateway_config
from infra.launchers.logging_config import LoggingConfig
from infra.launchers.log_paths import run_log_path, strategy_event_log_path, order_log_path

LOGGING_CFG = LoggingConfig()

def to_container_path(host_path: Path) -> str:
    host_path = host_path.resolve()
    root_path = ROOT.resolve()

    try:
        relative = host_path.relative_to(root_path)
    except ValueError:
        print()
        print("Dataset must be inside the trading-system project folder.")
        print(f"Project root: {root_path}")
        print(f"Chosen file: {host_path}")
        sys.exit(1)

    return str(Path("/work") / relative)


def list_backtest_datasets() -> list[Path]:
    data_dir = ROOT / "data" / "historical"

    if not data_dir.exists():
        return []

    return sorted(data_dir.glob("*.csv"))


def choose_backtest_dataset() -> Path:
    datasets = list_backtest_datasets()

    if datasets:
        dataset_options = [str(p.relative_to(ROOT)) for p in datasets]
        dataset_options.append("manual_path")

        selected_dataset = choose_from_list(
            "Choose backtest dataset",
            dataset_options,
        )

        if selected_dataset == "manual_path":
            raw_data_path = input("Enter dataset CSV path: ").strip()

            if raw_data_path == "":
                print("No dataset selected.")
                sys.exit(1)

            path = Path(raw_data_path)

            if not path.is_absolute():
                path = ROOT / path

            return path

        return ROOT / selected_dataset

    print()
    print("No CSV datasets found in data/historical/")
    raw_data_path = input("Enter dataset CSV path: ").strip()

    if raw_data_path == "":
        print("No dataset selected.")
        sys.exit(1)

    path = Path(raw_data_path)

    if not path.is_absolute():
        path = ROOT / path

    return path

def run_with_logfile(cmd: list[str], logfile_path: Path) -> int:
    logfile_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Raw run log: {logfile_path}")

    with logfile_path.open("a", encoding="utf-8") as f:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert process.stdout is not None

        for line in process.stdout:
            print(line, end="")
            f.write(line)

        return process.wait()
    
def list_strategies():
    strategies_dir = ROOT / "strategies"
    return sorted(
        p.name for p in strategies_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def choose_from_list(title: str, options: list[str]) -> str:
    print(f"\n{title}")
    for i, option in enumerate(options, start=1):
        print(f"  {i}. {option}")

    while True:
        raw = input("Choose number: ").strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Invalid choice, try again.")


def ask_run_seconds(default_seconds: int | None) -> int:
    if default_seconds is None:
        raw = input("Stop after how many seconds? Press Enter for nonstop: ").strip()
        if raw == "":
            return 0
    else:
        raw = input(
            f"Stop after how many seconds? Press Enter for default ({default_seconds}): "
        ).strip()
        if raw == "":
            return default_seconds

    if not raw.isdigit():
        print("Invalid value, using fallback.")
        return default_seconds if default_seconds is not None else 0

    return int(raw)


def docker_python_command(target_py: str, env_vars: dict[str, str] | None = None) -> list[str]:
    cmd = [
        "docker", "run", "--rm", "-it",
        "--network", "host",
        "-v", f"{ROOT}:/work",
        "-w", "/work",
        "-e", "PYTHONPATH=/work",
    ]

    if env_vars:
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

    cmd.extend([
        IMAGE,
        "python", target_py,
    ])
    return cmd


def ensure_strategy_files(strategy_name: str):
    strategy_dir = ROOT / "strategies" / strategy_name
    required = [
        strategy_dir / "config.py",
        strategy_dir / "core.py",
        strategy_dir / "nautilus_strategy.py",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print("\nMissing strategy files:")
        for item in missing:
            print(f"  - {item}")
        sys.exit(1)


def create_strategy_template():
    raw_name = input("\nEnter new strategy name (example: mean_reversion): ").strip()
    if not raw_name:
        print("No strategy name entered.")
        return

    strategy_name = raw_name.lower().replace(" ", "_").replace("-", "_")
    strategy_dir = ROOT / "strategies" / strategy_name

    if strategy_dir.exists():
        print(f"Strategy folder already exists: {strategy_dir}")
        return

    strategy_dir.mkdir(parents=True, exist_ok=True)

    class_prefix = "".join(part.capitalize() for part in strategy_name.split("_"))

    (strategy_dir / "__init__.py").write_text("", encoding="utf-8")

    (strategy_dir / "config.py").write_text(
        f'''from dataclasses import dataclass


@dataclass(frozen=True)
class {class_prefix}Config:
    symbol: str = "AAPL.NASDAQ"
    order_quantity: int = 1
''',
        encoding="utf-8",
    )

    (strategy_dir / "core.py").write_text(
        f'''from dataclasses import dataclass
from enum import Enum, auto

from strategies.{strategy_name}.config import {class_prefix}Config


class Signal(Enum):
    HOLD = auto()
    BUY = auto()
    SELL = auto()


@dataclass
class StrategyState:
    position_qty: int = 0
    last_signal: str | None = None


class {class_prefix}Core:
    def __init__(self, config: {class_prefix}Config):
        self.config = config

    def evaluate(self, **kwargs) -> Signal:
        return Signal.HOLD
''',
        encoding="utf-8",
    )

    (strategy_dir / "nautilus_strategy.py").write_text(
        f'''import os

from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from strategies.{strategy_name}.config import {class_prefix}Config
from strategies.{strategy_name}.core import {class_prefix}Core, StrategyState


class {class_prefix}NautilusStrategy(Strategy):
    def on_start(self):
        self.cfg = {class_prefix}Config()
        self.core = {class_prefix}Core(self.cfg)
        self.strategy_state = StrategyState()

        self.account_type = os.getenv("TRADING_ACCOUNT_TYPE", "paper")
        self.enable_order_placement = (
            os.getenv("ENABLE_ORDER_PLACEMENT", "false").lower() == "true"
        )
        self.log_quotes = os.getenv("LOG_QUOTES", "false").lower() == "true"

        self.instrument_id = InstrumentId.from_str(self.cfg.symbol)
        instrument = self.cache.instrument(self.instrument_id)

        if instrument is None:
            self.log.error(f"Missing instrument: {{self.instrument_id}}")
            self.stop()
            return

        self.subscribe_quote_ticks(self.instrument_id)
        self.log.info(f"Started strategy for {{self.cfg.symbol}}")

    def on_quote_tick(self, tick):
        if self.log_quotes:
            self.log.info(f"QUOTE {{tick.instrument_id}} bid={{tick.bid_price}} ask={{tick.ask_price}}")

    def on_stop(self):
        self.log.info("{class_prefix}NautilusStrategy stopped")
''',
        encoding="utf-8",
    )

    (strategy_dir / "README.md").write_text(
        f"# {strategy_name}\n\nStarter template strategy.\n",
        encoding="utf-8",
    )

    print(f"\nCreated strategy template: {strategy_name}")
    print(f"Folder: {strategy_dir}")


def main():
    area = choose_from_list(
        "What do you want to run?",
        ["test", "research", "strategy", "create_strategy"],
    )

    if area == "create_strategy":
        create_strategy_template()
        sys.exit(0)

    if area == "test":
        test_file = choose_from_list(
            "Choose test",
            [
                "tests/ib_market_data_test.py",
                "tests/ib_smoke_test.py",
                "tests/ib_tiny_order_test.py",
            ],
        )

        run_profile = choose_from_list(
            "Choose run profile",
            ["quick_test", "debug"],
        )

        log_quotes = run_profile == "debug"
        run_seconds = ask_run_seconds(default_seconds=300)

        env_vars = {
            "LOG_QUOTES": str(log_quotes).lower(),
            "RUN_SECONDS": str(run_seconds),
        }

        cmd = docker_python_command(test_file, env_vars)
        print("\nRunning:\n" + " ".join(cmd) + "\n")
        logfile = run_log_path("test_run")
        sys.exit(run_with_logfile(cmd, logfile))

    if area == "research":
        print("\nResearch mode is notebook/manual for now.")
        print("Use Jupyter separately.")
        sys.exit(0)

    strategy_name = choose_from_list("Choose strategy", list_strategies())
    ensure_strategy_files(strategy_name)

    mode = choose_from_list("Choose mode", ["backtest", "paper", "live"])

    env_vars = {
        "STRATEGY_NAME": strategy_name,
    }

    if mode == "backtest":
        run_profile = choose_from_list(
            "Choose run profile",
            ["quick_test", "debug"],
        )

        log_quotes = run_profile == "debug"
        run_seconds = ask_run_seconds(default_seconds=300)

        backtest_data_csv = choose_backtest_dataset()

        backtest_data_type = choose_from_list(
            "Choose backtest data type",
            ["quote_ticks"],
        )

        backtest_symbol = input(
            "Enter symbol, e.g. AAPL. Press Enter for AAPL: "
        ).strip().upper()

        if backtest_symbol == "":
            backtest_symbol = "AAPL"

        backtest_venue = input(
            "Enter venue, e.g. NASDAQ. Press Enter for NASDAQ: "
        ).strip().upper()

        if backtest_venue == "":
            backtest_venue = "NASDAQ"

        starting_balance = input(
            "Enter starting balance in USD. Press Enter for 100000: "
        ).strip()

        if starting_balance == "":
            starting_balance = "100000"

        env_vars.update({
            "LOG_QUOTES": str(log_quotes).lower(),
            "RUN_SECONDS": str(run_seconds),

            "BACKTEST_DATA_CSV": to_container_path(backtest_data_csv),
            "BACKTEST_DATA_TYPE": backtest_data_type,
            "BACKTEST_SYMBOL": backtest_symbol,
            "BACKTEST_VENUE": backtest_venue,
            "BACKTEST_STARTING_BALANCE": starting_balance,
            "BACKTEST_TRADER_ID": "BACKTESTER-001",
        })

        target = "backtests/run_backtest.py"
        cmd = docker_python_command(target, env_vars)

        print()
        print(f"Strategy: {strategy_name}")
        print(f"Mode: {mode}")
        print(f"Data CSV: {backtest_data_csv}")
        print(f"Container CSV: {to_container_path(backtest_data_csv)}")
        print(f"Data type: {backtest_data_type}")
        print(f"Symbol: {backtest_symbol}")
        print(f"Venue: {backtest_venue}")
        print(f"Starting balance: {starting_balance} USD")
        print(f"Log quotes: {log_quotes}")
        print(f"Run seconds: {run_seconds}")
        print()
        print("Running:\n" + " ".join(cmd) + "\n")

        logfile = run_log_path(strategy_name)
        sys.exit(run_with_logfile(cmd, logfile))
    
    gateway_cfg = get_gateway_config(mode)

    run_profile = choose_from_list(
        "Choose run profile",
        ["quick_test", "debug", "long_run"],
    )

    if run_profile == "quick_test":
        log_quotes = False
        run_seconds = ask_run_seconds(default_seconds=300)
    elif run_profile == "debug":
        log_quotes = True
        run_seconds = ask_run_seconds(default_seconds=300)
    else:
        log_quotes = False
        run_seconds = ask_run_seconds(default_seconds=None)

    env_vars.update({
        "TRADING_ACCOUNT_TYPE": gateway_cfg.mode,
        "IB_HOST": gateway_cfg.ib_host,
        "IB_PORT": str(gateway_cfg.ib_port),
        "IB_CLIENT_ID": str(gateway_cfg.ib_client_id),
        "IB_ACCOUNT_ID": gateway_cfg.ib_account_id,
        "TRADER_ID_SUFFIX": gateway_cfg.trader_id_suffix,
        "MARKET_DATA_TYPE": gateway_cfg.market_data_type,
        "ENABLE_ORDER_PLACEMENT": str(gateway_cfg.enable_order_placement).lower(),
        "LOG_QUOTES": str(log_quotes).lower(),
        "RUN_SECONDS": str(run_seconds),
    })

    target = "live/run_live.py"
    cmd = docker_python_command(target, env_vars)

    print()
    print(f"Strategy: {strategy_name}")
    print(f"Mode: {mode}")
    print(f"Detected port: {gateway_cfg.ib_port}")
    print(f"Market data type: {gateway_cfg.market_data_type}")
    print(f"Order placement enabled: {gateway_cfg.enable_order_placement}")
    print(f"Log quotes: {log_quotes}")
    print(f"Run seconds: {run_seconds} (0 means nonstop)")
    print()
    print("Running:\n" + " ".join(cmd) + "\n")

    logfile = run_log_path(strategy_name)
    sys.exit(run_with_logfile(cmd, logfile))


if __name__ == "__main__":
    main()