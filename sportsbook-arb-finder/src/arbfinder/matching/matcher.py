"""Matcher — assigns normalised updates to buckets."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from arbfinder.matching.bucket import Bucket, BucketKey, compute_time_window
from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.models import NormalizedOddsUpdate

__all__ = ["Matcher"]

logger = logging.getLogger(__name__)


class Matcher:
    """Assigns each :class:`NormalizedOddsUpdate` to a :class:`Bucket`.

    Lookup order:
    1. Exact :meth:`BucketStore.get` by computed ``BucketKey``.
    2. :meth:`BucketStore.get_time_tolerant` (neighbouring windows).
    3. :meth:`BucketStore.create` (new bucket).

    Never raises for a well-formed ``NormalizedOddsUpdate``.
    """

    def __init__(
        self,
        bucket_store: BucketStore,
        time_resolver: TimeResolver,
    ) -> None:
        self._store = bucket_store
        self._resolver = time_resolver

    def assign(self, update: NormalizedOddsUpdate) -> Bucket:
        """Assign *update* to an existing or new bucket and return it."""
        key = BucketKey(
            sport_key=update.sport_key,
            league_key=update.league_key,
            time_window=compute_time_window(update.start_time),
            home_team=update.home_team,
            away_team=update.away_team,
            market_type=update.market_type,
            selection=update.selection,
            line=update.line,
        )

        # 1. Exact match
        bucket = self._store.get(key)
        if bucket is not None:
            bucket.entries[update.book_id] = update
            bucket.last_updated = datetime.now(timezone.utc)
            return bucket

        # 2. Time-tolerant match
        bucket = self._store.get_time_tolerant(key, self._resolver, update.start_time)
        if bucket is not None:
            bucket.entries[update.book_id] = update
            bucket.last_updated = datetime.now(timezone.utc)
            return bucket

        # 3. Create new bucket
        bucket = self._store.create(key, update)
        return bucket
