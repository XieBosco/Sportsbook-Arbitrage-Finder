"""Tests for the bucket matching pipeline (Stage 2).

Covers:
 • Two updates from different books for the same game land in the same bucket.
 • A start_time 3 minutes apart still matches via get_time_tolerant.
 • A genuinely different game creates a new bucket.
 • Concurrent bucket creation for the same key doesn't produce duplicates.
"""

import threading
from datetime import datetime, timezone

from arbfinder.matching.bucket import BucketKey, compute_time_window
from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.models import NormalizedOddsUpdate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_normalized(
    *,
    book_id: str = "bookA",
    home_team: str = "Los Angeles Lakers",
    away_team: str = "Brooklyn Nets",
    start_time: datetime | None = None,
    market_type: str = "moneyline",
    selection: str = "home",
    line: float | None = None,
    odds: float = 1.67,
) -> NormalizedOddsUpdate:
    if start_time is None:
        start_time = datetime(2024, 6, 15, 19, 0, tzinfo=timezone.utc)
    return NormalizedOddsUpdate(
        book_id=book_id,
        book_event_id="evt-001",
        sport_key="basketball",
        league_key="NBA",
        home_team=home_team,
        away_team=away_team,
        start_time=start_time,
        market_type=market_type,
        selection=selection,
        line=line,
        odds=odds,
        captured_at=datetime(2024, 6, 15, 18, 55, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestComputeTimeWindow:
    """Tests for the time-window flooring helper."""

    def test_floors_to_15_min(self) -> None:
        dt = datetime(2024, 6, 15, 19, 7, 30, tzinfo=timezone.utc)
        assert compute_time_window(dt) == "2024-06-15T19:00:00+00:00"

    def test_exact_boundary(self) -> None:
        dt = datetime(2024, 6, 15, 19, 15, 0, tzinfo=timezone.utc)
        assert compute_time_window(dt) == "2024-06-15T19:15:00+00:00"

    def test_just_before_boundary(self) -> None:
        dt = datetime(2024, 6, 15, 19, 14, 59, tzinfo=timezone.utc)
        assert compute_time_window(dt) == "2024-06-15T19:00:00+00:00"


class TestSameGameSameBucket:
    """Two updates from different books for the same game/market/selection
    should land in the same bucket."""

    def test_same_game_same_bucket(self) -> None:
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)

        update_a = _make_normalized(book_id="bookA", odds=1.67)
        update_b = _make_normalized(book_id="bookB", odds=2.10)

        bucket_a = matcher.assign(update_a)
        bucket_b = matcher.assign(update_b)

        assert bucket_a is bucket_b
        assert "bookA" in bucket_a.entries
        assert "bookB" in bucket_a.entries


class TestTimeTolerantMatch:
    """A start_time 3 minutes apart from an existing bucket still matches
    via get_time_tolerant."""

    def test_3_min_apart_matches(self) -> None:
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)

        # First update at exactly the 15-minute boundary
        t1 = datetime(2024, 6, 15, 19, 0, 0, tzinfo=timezone.utc)
        # Second update 3 minutes before the boundary — floors to 18:45 window
        t2 = datetime(2024, 6, 15, 18, 57, 0, tzinfo=timezone.utc)

        update_a = _make_normalized(book_id="bookA", start_time=t1)
        update_b = _make_normalized(book_id="bookB", start_time=t2)

        bucket_a = matcher.assign(update_a)
        bucket_b = matcher.assign(update_b)

        # They should be in the same bucket despite different time windows
        assert bucket_a is bucket_b
        assert len(bucket_a.entries) == 2


class TestDifferentGameNewBucket:
    """A genuinely different game creates a new bucket."""

    def test_different_teams_different_bucket(self) -> None:
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)

        update_a = _make_normalized(
            book_id="bookA",
            home_team="Los Angeles Lakers",
            away_team="Brooklyn Nets",
        )
        update_b = _make_normalized(
            book_id="bookA",
            home_team="Boston Celtics",
            away_team="Toronto Raptors",
        )

        bucket_a = matcher.assign(update_a)
        bucket_b = matcher.assign(update_b)

        assert bucket_a is not bucket_b
        assert bucket_a.canonical_game_id != bucket_b.canonical_game_id


class TestConcurrentCreation:
    """Concurrent bucket creation for the same key doesn't produce duplicates."""

    def test_no_duplicate_buckets(self) -> None:
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)

        results: list = []
        errors: list = []

        def assign_and_record(book_id: str) -> None:
            try:
                update = _make_normalized(book_id=book_id)
                bucket = matcher.assign(update)
                results.append(bucket)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=assign_and_record, args=("bookA",)),
            threading.Thread(target=assign_and_record, args=("bookB",)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 2
        # Both threads should have gotten the same bucket
        assert results[0].canonical_game_id == results[1].canonical_game_id


class TestTimeResolver:
    """Tests for TimeResolver.is_within_tolerance."""

    def test_within_tolerance(self) -> None:
        resolver = TimeResolver()
        t1 = datetime(2024, 6, 15, 19, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 15, 19, 4, tzinfo=timezone.utc)
        assert resolver.is_within_tolerance(t1, t2)

    def test_outside_tolerance(self) -> None:
        resolver = TimeResolver()
        t1 = datetime(2024, 6, 15, 19, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 15, 21, 6, tzinfo=timezone.utc)
        assert not resolver.is_within_tolerance(t1, t2)

    def test_exact_boundary(self) -> None:
        resolver = TimeResolver()
        t1 = datetime(2024, 6, 15, 19, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 15, 19, 5, tzinfo=timezone.utc)
        assert resolver.is_within_tolerance(t1, t2)
