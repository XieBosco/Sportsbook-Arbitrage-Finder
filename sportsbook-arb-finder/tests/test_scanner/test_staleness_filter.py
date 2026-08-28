"""Tests for scanner/staleness_filter.py."""

from datetime import datetime, timedelta, timezone

from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.staleness_filter import StalenessFilter


def _ms(
    updated_at: dict[str, datetime],
) -> MatchedSelection:
    """Build a MatchedSelection with specific update timestamps."""
    return MatchedSelection(
        canonical_game_id="game-1",
        sport_key="Baseball",
        league_key="MLB",
        home_team="Team A",
        away_team="Team B",
        market_type="moneyline",
        selection="home",
        line=None,
        book_odds={book: -150 for book in updated_at},
        updated_at=updated_at,
    )


class TestStalenessFilter:
    """Verify staleness filtering logic."""

    def test_all_fresh(self) -> None:
        """All timestamps within max_age → fresh."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({
            "BookA": now - timedelta(seconds=2),
            "BookB": now - timedelta(seconds=3),
        })
        assert sf.is_fresh(ms, now) is True

    def test_one_stale_leg_rejected(self) -> None:
        """One stale leg among otherwise-fresh legs → rejected."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({
            "BookA": now - timedelta(seconds=2),  # fresh
            "BookB": now - timedelta(seconds=10),  # stale
        })
        assert sf.is_fresh(ms, now) is False

    def test_all_stale(self) -> None:
        """All timestamps stale → rejected."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({
            "BookA": now - timedelta(seconds=10),
            "BookB": now - timedelta(seconds=20),
        })
        assert sf.is_fresh(ms, now) is False

    def test_exactly_at_boundary(self) -> None:
        """Timestamp exactly at max_age boundary → still fresh (<=)."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({
            "BookA": now - timedelta(seconds=5),
        })
        assert sf.is_fresh(ms, now) is True

    def test_just_past_boundary(self) -> None:
        """Timestamp just past max_age → stale."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({
            "BookA": now - timedelta(seconds=5, microseconds=1),
        })
        assert sf.is_fresh(ms, now) is False

    def test_empty_updated_at(self) -> None:
        """No timestamps → not fresh."""
        now = datetime.now(timezone.utc)
        sf = StalenessFilter(max_age_seconds=5.0)
        ms = _ms({})
        assert sf.is_fresh(ms, now) is False
