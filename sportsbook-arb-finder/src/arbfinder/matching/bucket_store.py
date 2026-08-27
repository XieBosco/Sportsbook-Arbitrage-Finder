"""Thread-safe in-memory bucket store."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone

from arbfinder.matching.bucket import Bucket, BucketKey, compute_time_window
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.models import NormalizedOddsUpdate

__all__ = ["BucketStore"]


class BucketStore:
    """In-memory store keyed by :class:`BucketKey`.

    Provides exact-key lookup, time-tolerant lookup (checks neighbouring
    15-minute windows), and thread-safe bucket creation.
    """

    def __init__(self) -> None:
        self._index: dict[BucketKey, Bucket] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------
    def get(self, key: BucketKey) -> Bucket | None:
        """Exact key lookup."""
        return self._index.get(key)

    def get_time_tolerant(
        self,
        key: BucketKey,
        resolver: TimeResolver,
        incoming_start_time: datetime | None = None,
    ) -> Bucket | None:
        """Check neighbouring time-window buckets for a match.

        Builds ``BucketKey`` variants whose ``time_window`` is shifted
        by ±15 minutes.  For each candidate that exists in the store,
        checks whether the *actual* ``start_time`` of an existing entry
        is within the resolver's tolerance of *incoming_start_time*.
        """
        base_dt = datetime.fromisoformat(key.time_window)
        compare_dt = incoming_start_time if incoming_start_time is not None else base_dt

        for delta in (timedelta(minutes=-15), timedelta(minutes=15)):
            neighbour_tw = compute_time_window(base_dt + delta)
            neighbour_key = BucketKey(
                sport_key=key.sport_key,
                league_key=key.league_key,
                time_window=neighbour_tw,
                home_team=key.home_team,
                away_team=key.away_team,
                market_type=key.market_type,
                selection=key.selection,
                line=key.line,
            )
            bucket = self._index.get(neighbour_key)
            if bucket is None:
                continue

            # Compare actual start_times in the bucket against the
            # incoming update's real start_time.
            for entry in bucket.entries.values():
                if resolver.is_within_tolerance(entry.start_time, compare_dt):
                    return bucket

        return None

    # ------------------------------------------------------------------
    # Creation
    # ------------------------------------------------------------------
    def create(
        self,
        key: BucketKey,
        first_entry: NormalizedOddsUpdate,
    ) -> Bucket:
        """Create a new bucket, guarded against duplicate-creation races.

        If another thread created the same bucket between the caller's
        ``get()`` and this ``create()`` call, the existing bucket is
        returned instead of creating a second one.
        """
        with self._lock:
            existing = self._index.get(key)
            if existing is not None:
                return existing

            now = datetime.now(timezone.utc)
            bucket = Bucket(
                key=key,
                canonical_game_id=str(uuid.uuid4()),
                entries={first_entry.book_id: first_entry},
                created_at=now,
                last_updated=now,
            )
            self._index[key] = bucket
            return bucket
