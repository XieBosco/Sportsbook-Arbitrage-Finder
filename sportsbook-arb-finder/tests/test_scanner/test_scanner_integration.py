"""Integration test — end-to-end Scanner.process() from MatchedSelections."""

from datetime import datetime, timedelta, timezone

from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGrouper
from arbfinder.scanner.scanner import Scanner
from arbfinder.scanner.sinks.storage_sink import StorageSink
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.scanner.threshold_config import ScannerThresholds


def _fresh_now() -> datetime:
    return datetime.now(timezone.utc)


def _ms(
    selection: str,
    book_odds: dict[str, float],
    *,
    canonical_game_id: str = "game-1",
    market_type: str = "moneyline",
    line: float | None = None,
    ts: datetime | None = None,
) -> MatchedSelection:
    """Build a MatchedSelection with timestamps near *ts* (default: now)."""
    ts = ts or _fresh_now()
    return MatchedSelection(
        canonical_game_id=canonical_game_id,
        sport_key="Baseball",
        league_key="MLB",
        home_team="Team A",
        away_team="Team B",
        market_type=market_type,
        selection=selection,
        line=line,
        book_odds=book_odds,
        updated_at={book: ts for book in book_odds},
    )


def _make_scanner(
    *,
    min_margin: float = 0.001,
    max_age: float = 60.0,
    cooldown: float = 30.0,
    sink: StorageSink | None = None,
) -> tuple[Scanner, StorageSink]:
    """Build a Scanner wired for testing."""
    storage = sink or StorageSink()
    thresholds = ScannerThresholds(
        min_margin=min_margin,
        max_odds_age_seconds=max_age,
    )
    scanner = Scanner(
        grouper=MarketGrouper(),
        thresholds=thresholds,
        staleness_filter=StalenessFilter(max_age),
        dedup=DedupTracker(cooldown),
        sinks=[storage],
        expected_selections_by_market={
            "moneyline": {"home", "away"},
            "total": {"over", "under"},
        },
        stake_budget_fn=lambda _key: 100.0,
    )
    return scanner, storage


class TestScannerIntegration:
    """End-to-end integration tests for Scanner.process()."""

    def test_no_emit_until_group_complete(self) -> None:
        """Processing only one selection should not emit."""
        scanner, storage = _make_scanner()
        ts = _fresh_now()

        result = scanner.process(
            _ms("home", {"BookA": 250}, ts=ts)
        )

        assert result is None
        assert len(storage.get_all()) == 0

    def test_real_arb_produces_one_opportunity(self) -> None:
        """A real two-way arb across books should emit exactly once.

        Home +250 (BookA) → decimal 3.50
        Away -200 (BookB) → decimal 1.50
        Implied: 1/3.5 + 1/1.5 ≈ 0.952 → margin ~4.8%
        """
        scanner, storage = _make_scanner()
        ts = _fresh_now()

        # Process home side first — no emit yet
        r1 = scanner.process(
            _ms("home", {"BookA": 250}, ts=ts)
        )
        assert r1 is None

        # Process away side — should trigger arb detection
        r2 = scanner.process(
            _ms("away", {"BookB": -200}, ts=ts)
        )
        assert r2 is not None
        assert r2.margin > 0
        assert len(r2.legs) == 2
        assert len(storage.get_all()) == 1

        # Verify opportunity fields
        assert r2.sport_key == "Baseball"
        assert r2.league_key == "MLB"
        assert r2.home_team == "Team A"
        assert r2.away_team == "Team B"
        assert r2.market_type == "moneyline"

    def test_repeat_within_cooldown_no_reemit(self) -> None:
        """A repeated scan of the same still-open arb within cooldown
        should not re-emit.
        """
        scanner, storage = _make_scanner(cooldown=60.0)
        ts = _fresh_now()

        # First complete group → emits
        scanner.process(_ms("home", {"BookA": 250}, ts=ts))
        r1 = scanner.process(_ms("away", {"BookB": -200}, ts=ts))
        assert r1 is not None

        # Update the same selections (same group key) — within cooldown
        r2 = scanner.process(
            _ms("home", {"BookA": 260}, ts=ts)
        )
        # Even though we updated, the group was already complete and
        # the arb was already emitted within cooldown → None
        # Note: process re-checks completeness and arb, but dedup blocks re-emit
        r3 = scanner.process(
            _ms("away", {"BookB": -190}, ts=ts)
        )

        # Should not have emitted again
        assert len(storage.get_all()) == 1

    def test_margin_below_threshold_no_emit(self) -> None:
        """An arb with margin below min_margin should not emit.

        Home -200 / Away +150 → margin ≈ -6.7% (not even an arb)
        """
        scanner, storage = _make_scanner(min_margin=0.01)
        ts = _fresh_now()

        scanner.process(_ms("home", {"BookA": -200}, ts=ts))
        r = scanner.process(_ms("away", {"BookB": 150}, ts=ts))

        assert r is None
        assert len(storage.get_all()) == 0

    def test_stale_leg_no_emit(self) -> None:
        """A group with one stale leg should not emit."""
        scanner, storage = _make_scanner(max_age=5.0)
        now = _fresh_now()
        old = now - timedelta(seconds=30)

        # Home selection is fresh
        scanner.process(_ms("home", {"BookA": 250}, ts=now))
        # Away selection has stale timestamp
        r = scanner.process(_ms("away", {"BookB": -200}, ts=old))

        assert r is None
        assert len(storage.get_all()) == 0

    def test_single_book_conflict_no_emit(self) -> None:
        """Same book best on both sides → no emit."""
        scanner, storage = _make_scanner()
        ts = _fresh_now()

        # BookA is the only/best book for both selections
        scanner.process(_ms("home", {"BookA": 250}, ts=ts))
        r = scanner.process(_ms("away", {"BookA": -200}, ts=ts))

        # This is a single-book conflict — should be rejected
        assert r is None
        assert len(storage.get_all()) == 0

    def test_different_market_types_independent(self) -> None:
        """Moneyline and total markets should be processed independently."""
        scanner, storage = _make_scanner()
        ts = _fresh_now()

        # Complete a moneyline arb
        scanner.process(_ms("home", {"BookA": 250}, ts=ts))
        r1 = scanner.process(_ms("away", {"BookB": -200}, ts=ts))
        assert r1 is not None

        # Add a total — should not interfere; needs both over and under
        r2 = scanner.process(
            _ms("over", {"BookA": 110}, market_type="total", line=5.5, ts=ts)
        )
        assert r2 is None  # not complete yet

    def test_sink_exception_does_not_block(self) -> None:
        """A failing sink should not prevent the Opportunity from being returned."""
        from arbfinder.scanner.sinks.base_sink import OpportunitySink
        from arbfinder.scanner.schema import Opportunity

        class FailingSink(OpportunitySink):
            def emit(self, opportunity: Opportunity) -> None:
                raise RuntimeError("boom")

        storage = StorageSink()
        thresholds = ScannerThresholds(
            min_margin=0.001,
            max_odds_age_seconds=60.0,
        )
        scanner = Scanner(
            grouper=MarketGrouper(),
            thresholds=thresholds,
            staleness_filter=StalenessFilter(60.0),
            dedup=DedupTracker(30.0),
            sinks=[FailingSink(), storage],  # failing sink first
            expected_selections_by_market={"moneyline": {"home", "away"}},
            stake_budget_fn=lambda _: 100.0,
        )

        ts = _fresh_now()
        scanner.process(_ms("home", {"BookA": 250}, ts=ts))
        r = scanner.process(_ms("away", {"BookB": -200}, ts=ts))

        # Opportunity still returned and storage sink still received it
        assert r is not None
        assert len(storage.get_all()) == 1
