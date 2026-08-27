"""Tests for the normalization pipeline (Stage 1)."""

from datetime import datetime, timezone
import zoneinfo
from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.models import OddsUpdate, NormalizedOddsUpdate
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.normalization import unresolved_log

class MockNormalizer(BaseNormalizer):
    def normalize(self, update: OddsUpdate) -> NormalizedOddsUpdate | None:
        if update.raw_home_team == "Nonexistent Team XYZ":
            unresolved_log.record_unresolved_variable(update, "home_team", update.raw_home_team)
            return None
        return NormalizedOddsUpdate(
            book_id=update.book_id,
            book_event_id=update.raw_event_id,
            sport_key="basketball",
            league_key="NBA",
            home_team="Los Angeles Lakers",
            away_team="Brooklyn Nets",
            start_time=datetime(2024, 6, 15, 15, 0, tzinfo=zoneinfo.ZoneInfo("America/New_York")),
            market_type="moneyline",
            selection="home",
            line=None,
            odds=1.6667,
            captured_at=datetime(2024, 6, 15, 18, 55, tzinfo=timezone.utc),
        )

def _make_good_update() -> OddsUpdate:
    return OddsUpdate(
        book_id="mock_book",
        raw_event_id="evt-001",
        raw_sport_code="basketball",
        raw_league_name="NBA",
        raw_home_team="LA Lakers",
        raw_away_team="Brooklyn Nets",
        raw_start_time="2024-06-15T19:00:00+00:00",
        raw_market_type="Moneyline",
        raw_selection="Home",
        raw_line=None,
        odds_value=-150,
        odds_format="american",
        captured_at=datetime(2024, 6, 15, 18, 55, tzinfo=timezone.utc),
    )

def _make_bad_team_update() -> OddsUpdate:
    return OddsUpdate(
        book_id="mock_book",
        raw_event_id="evt-002",
        raw_sport_code="basketball",
        raw_league_name="NBA",
        raw_home_team="Nonexistent Team XYZ",
        raw_away_team="Brooklyn Nets",
        raw_start_time="2024-06-15T19:00:00+00:00",
        raw_market_type="Moneyline",
        raw_selection="Home",
        raw_line=None,
        odds_value=-110,
        odds_format="american",
        captured_at=datetime(2024, 6, 15, 18, 55, tzinfo=timezone.utc),
    )

class TestNormalizerBatch:
    def setup_method(self) -> None:
        unresolved_log.unknown_book_records.clear()
        unresolved_log.failed_normalization_records.clear()

    def test_unknown_book_is_logged_and_skipped(self) -> None:
        normalizer = Normalizer(normalizers={"mock_book": MockNormalizer()})
        update = OddsUpdate(
            book_id="unknown_book",
            raw_event_id="evt-999",
            raw_sport_code="x",
            raw_league_name="x",
            raw_home_team="x",
            raw_away_team="x",
            raw_start_time="2024-01-01T00:00:00Z",
            raw_market_type="x",
            raw_selection="x",
            raw_line=None,
            odds_value=1.5,
            odds_format="decimal",
            captured_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        results = normalizer.normalize_batch([update])
        assert results == []
        assert len(unresolved_log.unknown_book_records) == 1
        assert unresolved_log.unknown_book_records[0]["book_id"] == "unknown_book"

    def test_failed_normalization_is_logged(self) -> None:
        normalizer = Normalizer(normalizers={"mock_book": MockNormalizer()})
        bad_update = _make_bad_team_update()
        results = normalizer.normalize_batch([bad_update])
        assert results == []
        assert len(unresolved_log.failed_normalization_records) == 1
        assert unresolved_log.failed_normalization_records[0]["raw_home_team"] == "Nonexistent Team XYZ"

    def test_mixed_batch(self) -> None:
        normalizer = Normalizer(normalizers={"mock_book": MockNormalizer()})
        good = _make_good_update()
        bad = _make_bad_team_update()
        results = normalizer.normalize_batch([good, bad])
        assert len(results) == 1
        assert results[0].home_team == "Los Angeles Lakers"
        assert len(unresolved_log.failed_normalization_records) == 1
