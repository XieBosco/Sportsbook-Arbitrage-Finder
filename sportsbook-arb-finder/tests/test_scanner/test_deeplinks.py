"""Tests for sportsbook deeplink generation."""

from __future__ import annotations

from arbfinder.utils.deeplinks import generate_deeplink


def test_draftkings_deeplink():
    # With selection_id and event_id
    url = generate_deeplink(
        book_id="DraftKings",
        selection_id="0HC85399015P250_1",
        event_id="123456",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
    )
    assert url == "https://sportsbook.draftkings.com/event/123456?outcomes=0HC85399015P250_1"

    # With only selection_id
    url_sel_only = generate_deeplink(book_id="DraftKings", selection_id="0HC85399015P250_1")
    assert url_sel_only == "https://sportsbook.draftkings.com/?outcomes=0HC85399015P250_1"

    # Fallback
    assert generate_deeplink(book_id="DraftKings") == "https://sportsbook.draftkings.com/"


def test_fanduel_deeplink():
    # With market_id and selection_id
    url = generate_deeplink(
        book_id="FanDuel",
        market_id="1.234567",
        selection_id="987654",
    )
    assert url == "https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=1.234567&selectionId[0]=987654"

    # With only selection_id
    url_sel_only = generate_deeplink(book_id="FanDuel", selection_id="987654")
    assert url_sel_only == "https://on.sportsbook.fanduel.ca/addToBetslip?selectionId[0]=987654"

    # Fallback
    assert generate_deeplink(book_id="FanDuel") == "https://on.sportsbook.fanduel.ca/"


def test_betmgm_deeplink():
    # With event_id, market_id, selection_id
    url = generate_deeplink(
        book_id="BetMGM",
        event_id="19766272",
        market_id="201196265",
        selection_id="762963230",
    )
    assert url == "https://www.on.betmgm.ca/en/sports?options=19766272-201196265-762963230"

    # With selection_id only
    url_sel_only = generate_deeplink(book_id="BetMGM", selection_id="762963230")
    assert url_sel_only == "https://www.on.betmgm.ca/en/sports?options=762963230"

    # Fallback
    assert generate_deeplink(book_id="BetMGM") == "https://www.on.betmgm.ca/en/sports"


def test_caesars_deeplink():
    # With selection UUID
    url = generate_deeplink(
        book_id="Caesars",
        selection_id="9dc72c90-b2e2-3194-8265-8a9f65905e09",
    )
    assert url == "https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds=9dc72c90-b2e2-3194-8265-8a9f65905e09"

    # Fallback
    assert generate_deeplink(book_id="Caesars") == "https://sportsbook.caesars.com/ca/on/bet"


def test_betano_deeplink():
    # With event_id and teams
    url = generate_deeplink(
        book_id="Betano",
        event_id="88363620",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
    )
    assert url == "https://www.betano.ca/live/toronto-blue-jays-vs-cleveland-guardians/88363620/"

    # Fallback
    assert generate_deeplink(book_id="Betano") == "https://www.betano.ca/"


def test_end_to_end_deeplink_propagation():
    """Verify that deeplinks propagate from NormalizedOddsUpdate -> Bucket -> MatchedSelection -> Opportunity -> Leg."""
    from datetime import datetime, timezone
    from arbfinder.normalization.models import NormalizedOddsUpdate
    from arbfinder.matching.bucket import Bucket, BucketKey
    from arbfinder.matching.output import MatchOutputBuilder
    from arbfinder.scanner.market_grouper import MarketGrouper
    from arbfinder.scanner.scanner import Scanner
    from arbfinder.scanner.sinks.base_sink import OpportunitySink
    from arbfinder.scanner.schema import Opportunity
    from arbfinder.ui_server.serializers import serialize_opportunity

    now = datetime(2026, 8, 30, 20, 0, 0, tzinfo=timezone.utc)

    # 1. Bucket with DraftKings and FanDuel
    key_home = BucketKey(
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
        time_window="2026-08-30T22:00:00+00:00",
        market_type="moneyline",
        selection="home",
        line=None,
    )
    b_home = Bucket(canonical_game_id="game1", key=key_home)
    b_home.entries["DraftKings"] = NormalizedOddsUpdate(
        book_id="DraftKings",
        book_event_id="123456",
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
        start_time=now,
        market_type="moneyline",
        selection="home",
        line=None,
        odds=2.50,
        captured_at=now,
        deeplink="https://sportsbook.draftkings.com/event/123456?outcomes=0HC85399015P250_1",
    )

    key_away = BucketKey(
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
        time_window="2026-08-30T22:00:00+00:00",
        market_type="moneyline",
        selection="away",
        line=None,
    )
    b_away = Bucket(canonical_game_id="game1", key=key_away)
    b_away.entries["FanDuel"] = NormalizedOddsUpdate(
        book_id="FanDuel",
        book_event_id="99999",
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Cleveland Guardians",
        away_team="Toronto Blue Jays",
        start_time=now,
        market_type="moneyline",
        selection="away",
        line=None,
        odds=2.10,
        captured_at=now,
        deeplink="https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=market111&selectionId[0]=runner999",
    )

    # 2. Build MatchedSelection
    ms_home = MatchOutputBuilder.from_bucket(b_home)
    ms_away = MatchOutputBuilder.from_bucket(b_away)
    assert ms_home.book_deeplinks["DraftKings"] == "https://sportsbook.draftkings.com/event/123456?outcomes=0HC85399015P250_1"
    assert ms_away.book_deeplinks["FanDuel"] == "https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=market111&selectionId[0]=runner999"

    # 3. Process through Scanner
    from arbfinder.scanner.sinks.storage_sink import StorageSink
    from arbfinder.scanner.threshold_config import ScannerThresholds
    from arbfinder.scanner.staleness_filter import StalenessFilter
    from arbfinder.scanner.dedup_tracker import DedupTracker

    storage = StorageSink()
    thresholds = ScannerThresholds(
        min_margin=0.001,
        max_odds_age_seconds=60.0,
    )
    scanner = Scanner(
        grouper=MarketGrouper(),
        thresholds=thresholds,
        staleness_filter=StalenessFilter(thresholds),
        dedup=DedupTracker(30.0),
        sinks=[storage],
        expected_selections_by_market={
            "moneyline": {"home", "away"},
        },
        stake_budget_fn=lambda _key: (100.0, 1),
    )

    scanner.process(ms_home, now=now)
    opp = scanner.process(ms_away, now=now)

    assert opp is not None
    assert len(opp.legs) == 2

    # Check that each leg has its exact parameterized deeplink!
    leg_dk = next(l for l in opp.legs if l.book_id == "DraftKings")
    leg_fd = next(l for l in opp.legs if l.book_id == "FanDuel")

    assert leg_dk.deeplink == "https://sportsbook.draftkings.com/event/123456?outcomes=0HC85399015P250_1"
    assert leg_fd.deeplink == "https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=market111&selectionId[0]=runner999"

    # 4. Serialize for UI
    serialized = serialize_opportunity(opp)
    s_dk = next(l for l in serialized["legs"] if l["book_id"] == "DraftKings")
    s_fd = next(l for l in serialized["legs"] if l["book_id"] == "FanDuel")
    assert s_dk["deeplink"] == "https://sportsbook.draftkings.com/event/123456?outcomes=0HC85399015P250_1"
    assert s_fd["deeplink"] == "https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=market111&selectionId[0]=runner999"


def test_missing_deeplink_fallback_hash():
    """Verify that when a book has no deeplink, it defaults to '#'."""
    from datetime import datetime, timezone
    from arbfinder.matching.output import MatchedSelection
    from arbfinder.scanner.market_grouper import MarketGrouper
    from arbfinder.scanner.scanner import Scanner
    from arbfinder.scanner.sinks.storage_sink import StorageSink
    from arbfinder.scanner.threshold_config import ScannerThresholds
    from arbfinder.scanner.staleness_filter import StalenessFilter
    from arbfinder.scanner.dedup_tracker import DedupTracker

    now = datetime(2026, 8, 30, 20, 0, 0, tzinfo=timezone.utc)

    ms1 = MatchedSelection(
        canonical_game_id="g1",
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Team A",
        away_team="Team B",
        time_window="2026-08-30T22:00:00+00:00",
        market_type="moneyline",
        selection="home",
        line=None,
        book_odds={"DraftKings": 2.20},
        updated_at={"DraftKings": now},
        start_time=now,
        book_deeplinks={},  # No deeplink
    )
    ms2 = MatchedSelection(
        canonical_game_id="g1",
        sport_key="baseball_mlb",
        league_key="mlb",
        home_team="Team A",
        away_team="Team B",
        time_window="2026-08-30T22:00:00+00:00",
        market_type="moneyline",
        selection="away",
        line=None,
        book_odds={"FanDuel": 2.10},
        updated_at={"FanDuel": now},
        start_time=now,
        book_deeplinks={"FanDuel": ""},  # Empty string deeplink
    )

    storage = StorageSink()
    thresholds = ScannerThresholds(min_margin=0.001, max_odds_age_seconds=60.0)
    scanner = Scanner(
        grouper=MarketGrouper(),
        thresholds=thresholds,
        staleness_filter=StalenessFilter(thresholds),
        dedup=DedupTracker(30.0),
        sinks=[storage],
        expected_selections_by_market={"moneyline": {"home", "away"}},
        stake_budget_fn=lambda _key: (100.0, 1),
    )

    scanner.process(ms1, now=now)
    opp = scanner.process(ms2, now=now)

    assert opp is not None
    assert len(opp.legs) == 2
    assert all(leg.deeplink == "#" for leg in opp.legs)

