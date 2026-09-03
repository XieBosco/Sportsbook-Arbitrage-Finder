"""Pipeline configuration — pydantic-validated, loaded from YAML."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from arbfinder.scanner.threshold_config import ScannerThresholds

__all__ = [
    "AppConfig",
    "ArbitrageConfig",
    "BookConfig",
    "ServerConfig",
    "SinksConfig",
    "load_config",
]


class BookConfig(BaseModel):
    """Configuration for a single sportsbook."""

    name: str
    enabled: bool = True
    url_pattern: str
    parser_class: str
    normalizer_class: str

    model_config = {"frozen": True}


class ArbitrageConfig(BaseModel):
    """Arbitrage detection parameters."""

    min_profit_percentage: float = 2.5
    total_bet_amount: float = 100.0
    unit_size: float = 100.0
    stake_calculating_method: int = 2
    mainlines_only: bool = True
    kelly_bankroll: float = 1000.0
    kelly_multiplier: float = 0.25


class SinksConfig(BaseModel):
    """Sink toggle configuration."""

    console_enabled: bool = True
    file_enabled: bool = False
    websocket_enabled: bool = True
    execution_enabled: bool = False
    odds_format: str = "american"


class ServerConfig(BaseModel):
    """Web server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    ui_sort_by: str = "timecreated"


class AppConfig(BaseModel):
    """Top-level application configuration.

    Loaded from a unified YAML file.  Validation errors raise
    ``pydantic.ValidationError`` at startup — fail loudly rather
    than defaulting silently on required fields.
    """

    cdp_port: int = 19222
    books: list[BookConfig]
    arbitrage: ArbitrageConfig = ArbitrageConfig()
    scanner: ScannerThresholds = ScannerThresholds()
    sinks: SinksConfig = SinksConfig()
    server: ServerConfig = ServerConfig()
    logging_config_path: str | None = None

    model_config = {"frozen": True}


def load_config(path: str | Path = "config/settings.yaml") -> AppConfig:
    """Load and validate the application configuration from a YAML file.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ValueError
        If the configuration file is empty.
    pydantic.ValidationError
        If the YAML content fails schema validation.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raise ValueError(f"Configuration file is empty: {path}")

    return AppConfig(**raw)
