"""Alias resolver — maps raw book-specific names to canonical names."""

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["AliasResolver"]

logger = logging.getLogger(__name__)


class AliasResolver:
    """Resolves raw book-specific values to canonical names.

    Loads a JSON file whose schema is::

        {
            "canonical_name": {
                "book_id": "raw_name",
                ...
            },
            ...
        }

    At load time a **reverse index** is built::

        (book_id_lower, raw_name_lower) -> canonical_name

    so that ``resolve("DraftKings", "LA Lakers")`` returns
    ``"Los Angeles Lakers"`` in O(1).
    """

    def __init__(self, json_path: str | Path) -> None:
        self._reverse: dict[tuple[str, str], str] = {}
        self._load_reverse_dict(json_path)

    def _load_reverse_dict(self, json_path: str | Path) -> None:
        """Populate ``self._reverse`` from the alias JSON file at *json_path*."""
        path = Path(json_path)
        if not path.exists():
            logger.warning("Alias file not found: %s", path)
            return
        with open(path, encoding="utf-8") as fh:
            data: dict[str, dict[str, str]] = json.load(fh)
        for canonical, book_map in data.items():
            for book_id, raw_name in book_map.items():
                key = (book_id.lower(), raw_name.lower())
                self._reverse[key] = canonical

    def resolve(self, book_id: str, raw_value: str) -> str | None:
        """Return the canonical name for *raw_value* as reported by *book_id*.

        The lookup is **case-insensitive** on both the book ID and the
        raw value.  Returns ``None`` on a miss.
        """
        return self._reverse.get((book_id.lower(), raw_value.lower()))
