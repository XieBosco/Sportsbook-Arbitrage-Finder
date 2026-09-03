"""Health tracking for sportsbook feeds.

Monitors feed-level liveness (is the book connected and sending data?),
which is distinct from the ``StalenessFilter`` that operates on individual
odds updates already in the pipeline.  A book that's connected but silent
is a known real failure mode ("hanging feed") per the Developer Guide.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

__all__ = ["BookHealth", "HealthTracker"]


@dataclass
class BookHealth:
    """Health status for a single sportsbook feed."""

    book_id: str
    connected: bool = False
    initialized: bool = False
    last_update_at: datetime | None = None
    last_error: str | None = None
    consecutive_errors: int = 0


class HealthTracker:
    """Thread-safe tracker for per-book feed health.

    Parameters
    ----------
    clock:
        Optional callable returning ``datetime`` — injectable for
        deterministic testing.  Defaults to ``datetime.now(timezone.utc)``.
    """

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._books: dict[str, BookHealth] = {}
        self._lock = threading.Lock()
        self._clock = clock

    def _now(self) -> datetime:
        if self._clock is not None:
            return self._clock()
        return datetime.now(timezone.utc)

    def _ensure_book(self, book_id: str) -> BookHealth:
        if book_id not in self._books:
            self._books[book_id] = BookHealth(book_id=book_id)
        return self._books[book_id]

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------
    def mark_connected(self, book_id: str) -> None:
        """Record that the CDP connection for *book_id* is established."""
        with self._lock:
            health = self._ensure_book(book_id)
            health.connected = True
            health.consecutive_errors = 0
            health.last_error = None

    def mark_initialized(self, book_id: str) -> None:
        """Record that the parser has processed its initial-state payload."""
        with self._lock:
            health = self._ensure_book(book_id)
            health.initialized = True

    def mark_update(self, book_id: str) -> None:
        """Record a successful payload processing for *book_id*."""
        with self._lock:
            health = self._ensure_book(book_id)
            health.last_update_at = self._now()
            health.consecutive_errors = 0

    def mark_error(self, book_id: str, error: str) -> None:
        """Record an error for *book_id*."""
        with self._lock:
            health = self._ensure_book(book_id)
            health.last_error = error
            health.consecutive_errors += 1

    def mark_disconnected(self, book_id: str) -> None:
        """Record that the CDP connection for *book_id* has dropped."""
        with self._lock:
            health = self._ensure_book(book_id)
            health.connected = False
            health.initialized = False

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_all(self) -> dict[str, BookHealth]:
        """Return a snapshot of all book health statuses."""
        with self._lock:
            return dict(self._books)

    def get_stale_books(self, max_silence_seconds: float) -> list[str]:
        """Return book_ids that are connected but haven't sent data recently.

        A book that is connected but silent is a known failure mode
        ("hanging feed"), independent of the per-update ``StalenessFilter``
        which already happens inside the scanner.
        """
        now = self._now()
        stale: list[str] = []
        with self._lock:
            for book_id, health in self._books.items():
                if not health.connected:
                    continue
                if health.last_update_at is None:
                    # Connected but never received data
                    stale.append(book_id)
                    continue
                silence = (now - health.last_update_at).total_seconds()
                if silence > max_silence_seconds:
                    stale.append(book_id)
        return stale
