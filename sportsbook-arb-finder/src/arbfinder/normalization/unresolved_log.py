"""Unresolved-update logging — feeds the manual review queue.

Records updates that could not be normalized (unknown book or failed field
resolution) to both an in-memory list (for programmatic inspection / tests)
and a rotating log file (for offline review).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from arbfinder.normalization.models import OddsUpdate

__all__ = [
    "record_failed_normalization",
    "record_unknown_book",
    "record_unresolved_variable",
    "unknown_book_records",
    "failed_normalization_records",
    "unresolved_variable_records",
]

# ---------------------------------------------------------------------------
# In-memory queues (lists of dicts) — test-inspectable
# ---------------------------------------------------------------------------
unknown_book_records: list[dict] = []
failed_normalization_records: list[dict] = []
unresolved_variable_records: list[dict] = []

# ---------------------------------------------------------------------------
# File logger — rotating log under logs/
# ---------------------------------------------------------------------------
_LOG_DIR = Path(__file__).resolve().parents[3] / "logs"  # <project>/logs
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_file_logger = logging.getLogger("arbfinder.normalization.unresolved_log.file")
_file_logger.setLevel(logging.INFO)
_file_logger.propagate = False

if not _file_logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_DIR / "unresolved.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _file_logger.addHandler(_handler)

# Regular module logger for console output
logger = logging.getLogger(__name__)


def _update_to_dict(update: OddsUpdate) -> dict:
    """Serialise an OddsUpdate to a JSON-friendly dict."""
    return {
        "book_id": update.book_id,
        "raw_event_id": update.raw_event_id,
        "raw_sport_code": update.raw_sport_code,
        "raw_league_name": update.raw_league_name,
        "raw_home_team": update.raw_home_team,
        "raw_away_team": update.raw_away_team,
        "raw_start_time": update.raw_start_time,
        "raw_market_type": update.raw_market_type,
        "raw_selection": update.raw_selection,
        "raw_line": update.raw_line,
        "odds_value": str(update.odds_value),
        "odds_format": update.odds_format,
        "captured_at": update.captured_at.isoformat(),
    }


def _record(reason: str, store: list[dict], update: OddsUpdate, extra: dict | None = None) -> None:
    """Build a record for *update*, append it to *store*, and write it to the file log.

    *extra* fields (if any) are placed between ``timestamp`` and the
    serialised update fields, matching each reason's record layout.
    """
    record = {
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(extra or {}),
        **_update_to_dict(update),
    }
    store.append(record)
    _file_logger.info(json.dumps(record))


def record_unknown_book(update: OddsUpdate) -> None:
    """Record an update whose ``book_id`` has no registered normalizer."""
    _record("unknown_book", unknown_book_records, update)
    logger.warning(
        "No normalizer registered for book %r (event %s)",
        update.book_id,
        update.raw_event_id,
    )


def record_failed_normalization(update: OddsUpdate) -> None:
    """Record an update whose normalizer returned ``None``."""
    _record("failed_normalization", failed_normalization_records, update)
    logger.warning(
        "Normalization failed for book %r event %s (team: %s / %s)",
        update.book_id,
        update.raw_event_id,
        update.raw_home_team,
        update.raw_away_team,
    )


def record_unresolved_variable(update: OddsUpdate, field: str, raw_value: str) -> None:
    """Record an update that failed because a specific field couldn't be resolved."""
    _record(
        "unresolved_variable",
        unresolved_variable_records,
        update,
        extra={"unresolved_field": field, "unresolved_value": raw_value},
    )
    logger.warning(
        "Unresolved %s '%s' for book %r (event %s)",
        field,
        raw_value,
        update.book_id,
        update.raw_event_id,
    )