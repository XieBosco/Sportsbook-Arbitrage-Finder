"""Scanner threshold configuration — pydantic-validated, loaded from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator

__all__ = ["ScannerThresholds", "load_scanner_thresholds"]


class ScannerThresholds(BaseModel):
    """Runtime thresholds for the arbitrage scanner.

    Validated via pydantic — invalid config raises ``ValidationError``
    at startup rather than silently falling back to defaults.
    """

    min_margin: float = 0.01
    max_odds_age_seconds: float = 5.0
    dedup_cooldown_seconds: float = 0.1
    min_legs_required: int = 2
    excluded_book_pairs: set[tuple[str, str]] = set()
    excluded_books: set[str] = set()
    excluded_markets: set[str] = set()

    @field_validator("excluded_markets", mode="before")
    @classmethod
    def _coerce_excluded_markets(cls, v: Any) -> set[str]:
        """Accept a list of strings and coerce to lowercase set."""
        if isinstance(v, (list, set)):
            return {str(market).lower() for market in v}
        return v

    @field_validator("excluded_books", mode="before")
    @classmethod
    def _coerce_excluded_books(cls, v: Any) -> set[str]:
        """Accept a list of strings and coerce to lowercase set."""
        if isinstance(v, (list, set)):
            return {str(book).lower() for book in v}
        return v

    @field_validator("excluded_book_pairs", mode="before")
    @classmethod
    def _coerce_pairs(cls, v: Any) -> set[tuple[str, str]]:
        """Accept YAML-friendly list-of-lists and convert to set-of-tuples."""
        if isinstance(v, (list, set)):
            return {tuple(pair) for pair in v}
        return v


def load_scanner_thresholds(path: Path) -> ScannerThresholds:
    """Load and validate scanner thresholds from a YAML file.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    pydantic.ValidationError
        If the YAML content fails schema validation.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    return ScannerThresholds(**raw)
