"""Unresolved-update logging for parsers.

Records when a parser receives an odds update (WebSocket message) but cannot
resolve a necessary ID (fixture, market, or selection) because it is missing
from the reference dictionaries built via HTTP payloads.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

__all__ = [
    "record_unresolved_parser_id",
    "unresolved_parser_records",
]

unresolved_parser_records: list[dict] = []

_LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

_file_logger = logging.getLogger("arbfinder.parsers.unresolved_log.file")
_file_logger.setLevel(logging.INFO)
_file_logger.propagate = False

if not _file_logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_DIR / "unresolved_parsers.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _file_logger.addHandler(_handler)

logger = logging.getLogger(__name__)


def record_unresolved_parser_id(
    book_id: str,
    id_type: str,
    missing_id: str,
    raw_payload: str | None = None,
) -> None:
    """Record a parsing failure due to an unresolved ID in the reference dictionary.

    Args:
        book_id: The sportsbook name (e.g., 'BetMGM').
        id_type: What kind of ID was missing ('fixture_id', 'market_id', 'selection_id').
        missing_id: The actual ID value that was not found.
        raw_payload: The raw string/JSON payload if available.
    """
    record = {
        "reason": "unresolved_parser_id",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "book_id": book_id,
        "id_type": id_type,
        "missing_id": missing_id,
    }
    if raw_payload:
        record["raw_payload"] = raw_payload

    unresolved_parser_records.append(record)
    if len(unresolved_parser_records) > 1000:
        del unresolved_parser_records[:-1000]
    _file_logger.propagate = False
    _file_logger.info(json.dumps(record))
    logger.debug(
        "Unresolved %s '%s' for book %r",
        id_type,
        missing_id,
        book_id,
    )
