from dataclasses import dataclass


@dataclass(frozen=True)
class LoggingConfig:
    log_quotes_default: bool = False
    log_signals_only_default: bool = True