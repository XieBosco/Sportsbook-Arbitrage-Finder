"""Unit tests for newly added eviction, precision, and health endpoint features."""

from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient

from arbfinder.core.arbitrage import check_arbitrage
from arbfinder.matching.bucket import BucketKey
from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.output import MatchedSelection
from arbfinder.normalization.models import NormalizedOddsUpdate
from arbfinder.pipeline.config import load_config
from arbfinder.pipeline.health import HealthTracker
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGrouper, MarketGroupKey
from arbfinder.ui_server.app import create_app
from arbfinder.ui_server.connection_manager import ConnectionManager


def _make_ms(
    selection: str,
    book_odds: dict[str, float | str],
    *,
    line: float | None = None,
    ts: datetime | None = None,
) -> MatchedSelection:
    now = ts or datetime.now(timezone.utc)
    return MatchedSelection(
        canonical_game_id="game-test-1",
        sport_key="Baseball",
        league_key="MLB",
        home_team="Team H",
        away_team="Team A",
        time_window="full_game",
        market_type="total",
        selection=selection,
        line=line,
        book_odds=book_odds,
        updated_at={book: now for book in book_odds},
    )


class TestMarketGrouperEvictionAndPrecision:
    """Test MarketGrouper TTL eviction and floating-point line precision."""

    def test_line_rounding_groups_identical_float_representations(self) -> None:
        grouper = MarketGrouper()
        # 8.500000000000002 vs 8.5
        ms1 = _make_ms("over", {"BookA": -110}, line=8.500000000000002)
        ms2 = _make_ms("under", {"BookB": -110}, line=8.5)

        k1 = grouper.add(ms1)
        k2 = grouper.add(ms2)

        assert k1 == k2
        assert k1.line == 8.5
        assert grouper.is_complete(k1, {"over", "under"})

    def test_market_grouper_evict_expired(self) -> None:
        now = datetime.now(timezone.utc)
        old_time = now - timedelta(hours=30)
        recent_time = now - timedelta(minutes=10)

        grouper = MarketGrouper()
        ms_old = _make_ms("over", {"BookA": -110}, line=7.5, ts=old_time)
        ms_recent = _make_ms("over", {"BookB": -110}, line=8.5, ts=recent_time)

        k_old = grouper.add(ms_old)
        k_recent = grouper.add(ms_recent)

        assert len(grouper._groups) == 2
        evicted = grouper.evict_expired(max_age_seconds=86400.0, now=now)

        assert evicted == 1
        assert k_old not in grouper._groups
        assert k_recent in grouper._groups


class TestBucketStoreEviction:
    """Test BucketStore memory pruning."""

    def test_bucket_store_evict_expired(self) -> None:
        store = BucketStore()
        now = datetime.now(timezone.utc)

        key1 = BucketKey(
            sport_key="Baseball",
            league_key="MLB",
            time_window="2026-09-01T20:00:00+00:00",
            home_team="Team A",
            away_team="Team B",
            market_type="moneyline",
            selection="home",
            line=None,
        )
        entry1 = NormalizedOddsUpdate(
            book_id="BookA",
            book_event_id="e1",
            sport_key="Baseball",
            league_key="MLB",
            home_team="Team A",
            away_team="Team B",
            start_time=now,
            market_type="moneyline",
            selection="home",
            line=None,
            odds=2.0,
            captured_at=now - timedelta(days=2),
        )

        bucket = store.create(key1, entry1)
        # Simulate an old bucket
        bucket.last_updated = now - timedelta(days=2)

        assert len(store._index) == 1
        evicted = store.evict_expired(max_age_seconds=86400.0, now=now)
        assert evicted == 1
        assert len(store._index) == 0


class TestDedupTrackerPrune:
    """Test DedupTracker expired key pruning."""

    def test_prune_expired(self) -> None:
        now = datetime.now(timezone.utc)
        dedup = DedupTracker(cooldown_seconds=0.1)

        key = MarketGroupKey(
            sport_key="Baseball",
            league_key="MLB",
            time_window="full_game",
            home_team="Team H",
            away_team="Team A",
            market_type="moneyline",
            line=None,
        )

        assert dedup.should_emit(key, now - timedelta(seconds=5)) is True
        assert len(dedup._last_emitted) == 1

        pruned = dedup.prune_expired(now=now)
        assert pruned == 1
        assert len(dedup._last_emitted) == 0


class TestArbitrageOddsFlexibility:
    """Test check_arbitrage handling canonical decimal odds."""

    def test_native_decimal_odds(self) -> None:
        group = {
            "home": _make_ms("home", {"BookA": 3.5}),
            "away": _make_ms("away", {"BookB": 1.5}),
        }
        res = check_arbitrage(group)
        assert res.is_arbitrage is True
        assert res.best_odds_by_selection["home"][1] == 3.5
        assert res.best_odds_by_selection["away"][1] == 1.5

    def test_longshot_odds_10000(self) -> None:
        """Verify that +10000 odds (decimal 101.0) and +50000 (501.0) are preserved accurately without being misconverted."""
        group = {
            "underdog": _make_ms("underdog", {"BookA": 101.0}),
            "favorite": _make_ms("favorite", {"BookB": 1.02}),
        }
        res = check_arbitrage(group)
        assert res.best_odds_by_selection["underdog"][1] == 101.0  # Must be 101.0, NOT 2.01!

        group_extreme = {
            "underdog": _make_ms("underdog", {"BookA": 501.0}),
            "favorite": _make_ms("favorite", {"BookB": 1.01}),
        }
        res_extreme = check_arbitrage(group_extreme)
        assert res_extreme.best_odds_by_selection["underdog"][1] == 501.0

    def test_decimal_odds_pipeline_invariance(self) -> None:
        """Verify that normalizers produce decimal float odds without roundtripping to American strings."""
        from arbfinder.normalization.book_normalizers.draftkings_normalizer import DraftKingsNormalizer
        from arbfinder.normalization.models import OddsUpdate

        norm = DraftKingsNormalizer()
        raw = OddsUpdate(
            book_id="DraftKings",
            raw_event_id="e1",
            raw_sport_code="7",
            raw_league_name="84240",
            raw_home_team="LA Angels",
            raw_away_team="HOU Astros",
            raw_start_time="2026-09-01T19:00:00Z",
            raw_market_type="Moneyline",
            raw_selection="LA Angels",
            raw_line=None,
            odds_value="+150",
            odds_format="american",
            captured_at=datetime.now(timezone.utc),
        )
        norm_update = norm.normalize(raw)
        assert norm_update is not None
        assert isinstance(norm_update.odds, float)
        assert norm_update.odds == 2.5  # Canonical decimal float, not American string "+150"


class TestHealthEndpoint:
    """Test /api/health and /health endpoint responses with HealthTracker."""

    def test_api_health_endpoint(self) -> None:
        tracker = HealthTracker()
        tracker.mark_connected("DraftKings")
        tracker.mark_initialized("DraftKings")

        manager = ConnectionManager()
        from pathlib import Path
        config_path = Path(__file__).resolve().parents[2] / "config" / "settings.yaml"
        config = load_config(config_path)

        app = create_app(manager, config=config, health_tracker=tracker)
        client = TestClient(app)

        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "sportsbooks" in data
        assert data["sportsbooks"]["DraftKings"]["is_connected"] is True
        assert data["sportsbooks"]["DraftKings"]["is_initialized"] is True
