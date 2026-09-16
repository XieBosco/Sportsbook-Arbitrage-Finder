"""Artificial data generators for benchmarking and latency testing.

Generates realistic, synthetic sportsbook odds updates across multiple
layers of the pipeline:
1. Raw `OddsUpdate` (for end-to-end and normalizer testing)
2. `NormalizedOddsUpdate` (for matcher + scanner testing)
3. `MatchedSelection` (for scanner and arb-detection isolation testing)
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from arbfinder.matching.bucket import compute_time_window
from arbfinder.matching.output import MatchedSelection
from arbfinder.normalization.models import NormalizedOddsUpdate, OddsUpdate

# Canonical MLB matchups based on team_aliases.json
MLB_MATCHUPS = [
    ("Houston Astros", "Texas Rangers"),
    ("Los Angeles Angels", "Oakland Athletics"),
    ("Detroit Tigers", "Miami Marlins"),
    ("Milwaukee Brewers", "Washington Nationals"),
    ("Atlanta Braves", "Philadelphia Phillies"),
    ("New York Yankees", "Boston Red Sox"),
    ("Los Angeles Dodgers", "San Francisco Giants"),
    ("Chicago Cubs", "St. Louis Cardinals"),
    ("San Diego Padres", "Arizona Diamondbacks"),
    ("Toronto Blue Jays", "Baltimore Orioles"),
]

# Book-specific alias mappings for artificial raw OddsUpdate generation
BOOK_TEAM_ALIASES = {
    "DraftKings": {
        "Houston Astros": "HOU Astros",
        "Texas Rangers": "TEX Rangers",
        "Los Angeles Angels": "LA Angels",
        "Oakland Athletics": "Athletics",
        "Detroit Tigers": "DET Tigers",
        "Miami Marlins": "MIA Marlins",
        "Milwaukee Brewers": "MIL Brewers",
        "Washington Nationals": "WAS Nationals",
        "Atlanta Braves": "ATL Braves",
    },
    "FanDuel": {
        "Houston Astros": "Houston Astros",
        "Texas Rangers": "Texas Rangers",
        "Los Angeles Angels": "Los Angeles Angels",
        "Oakland Athletics": "Athletics",
        "Detroit Tigers": "Detroit Tigers",
        "Miami Marlins": "Miami Marlins",
        "Milwaukee Brewers": "Milwaukee Brewers",
        "Washington Nationals": "Washington Nationals",
        "Atlanta Braves": "Atlanta Braves",
    },
    "Caesars": {
        "Houston Astros": "Houston Astros",
        "Texas Rangers": "Texas Rangers",
        "Los Angeles Angels": "Los Angeles Angels",
        "Oakland Athletics": "Athletics",
        "Detroit Tigers": "Detroit Tigers",
        "Miami Marlins": "Miami Marlins",
        "Milwaukee Brewers": "Milwaukee Brewers",
        "Washington Nationals": "Washington Nationals",
        "Atlanta Braves": "Atlanta Braves",
    },
    "BetMGM": {
        "Houston Astros": "Houston Astros",
        "Texas Rangers": "Texas Rangers",
        "Los Angeles Angels": "Los Angeles Angels",
        "Oakland Athletics": "Athletics",
        "Detroit Tigers": "Detroit Tigers",
        "Miami Marlins": "Miami Marlins",
        "Milwaukee Brewers": "Milwaukee Brewers",
        "Atlanta Braves": "Atlanta Braves",
    },
    "Betano": {
        "Houston Astros": "Houston Astros",
        "Texas Rangers": "Texas Rangers",
        "Los Angeles Angels": "Los Angeles Angels",
        "Oakland Athletics": "Athletics",
        "Detroit Tigers": "Detroit Tigers",
        "Miami Marlins": "Miami Marlins",
        "Milwaukee Brewers": "Milwaukee Brewers",
        "Washington Nationals": "Washington Nationals",
        "Atlanta Braves": "Atlanta Braves",
    },
}

BOOK_MARKET_ALIASES = {
    "DraftKings": {"moneyline": "Moneyline", "total": "Total"},
    "FanDuel": {"moneyline": "MONEY_LINE", "total": "TOTAL_POINTS_(OVER/UNDER)"},
    "Caesars": {"moneyline": "Money Line", "total": "Total Runs"},
    "BetMGM": {"moneyline": "Moneyline", "total": "Totals"},
    "Betano": {"moneyline": "Winner", "total": "Over/Under Total Goals"},
}

BOOK_METADATA = {
    "DraftKings": {"sport": "7", "league": "84240"},
    "FanDuel": {"sport": "7511", "league": "11196870"},
    "Caesars": {"sport": "Baseball", "league": "MLB"},
    "BetMGM": {"sport": "Baseball", "league": "MLB"},
    "Betano": {"sport": "BASE", "league": "1662"},
}


@dataclass
class ArbScenarioPair:
    """Pair of matched selections where the second selection triggers an arbitrage."""

    setup_selection: MatchedSelection
    arb_trigger_selection: MatchedSelection
    expected_margin: float


def create_synthetic_raw_odds_update(
    book_id: str,
    home_team: str,
    away_team: str,
    market_type: str = "moneyline",
    selection: str = "home",
    line: float | None = None,
    odds_value: int | float | str = 105,
    odds_format: Literal["decimal", "american", "fractional"] = "american",
    game_idx: int = 0,
    captured_at: datetime | None = None,
) -> OddsUpdate:
    """Create a raw OddsUpdate with valid book-specific aliases."""
    captured_at = captured_at or datetime.now(timezone.utc)
    raw_home = BOOK_TEAM_ALIASES.get(book_id, {}).get(home_team, home_team)
    raw_away = BOOK_TEAM_ALIASES.get(book_id, {}).get(away_team, away_team)
    raw_market = BOOK_MARKET_ALIASES.get(book_id, {}).get(market_type, market_type)
    meta = BOOK_METADATA.get(book_id, {"sport": "Baseball", "league": "MLB"})

    if selection == "home":
        raw_sel = raw_home
    elif selection == "away":
        raw_sel = raw_away
    elif selection in ("over", "Over"):
        raw_sel = "Over"
    elif selection in ("under", "Under"):
        raw_sel = "Under"
    else:
        raw_sel = selection

    start_time_iso = (captured_at + timedelta(hours=2)).isoformat()

    return OddsUpdate(
        book_id=book_id,
        raw_event_id=f"event-{game_idx}",
        raw_sport_code=meta["sport"],
        raw_league_name=meta["league"],
        raw_home_team=raw_home,
        raw_away_team=raw_away,
        raw_start_time=start_time_iso,
        raw_market_type=raw_market,
        raw_selection=raw_sel,
        raw_line=line,
        odds_value=odds_value,
        odds_format=odds_format,
        captured_at=captured_at,
    )


def create_synthetic_normalized_update(
    book_id: str,
    home_team: str,
    away_team: str,
    market_type: str = "moneyline",
    selection: str = "home",
    line: float | None = None,
    decimal_odds: float = 1.95,
    game_idx: int = 0,
    start_time: datetime | None = None,
    captured_at: datetime | None = None,
) -> NormalizedOddsUpdate:
    """Create a canonical NormalizedOddsUpdate directly."""
    captured_at = captured_at or datetime.now(timezone.utc)
    start_time = start_time or (captured_at + timedelta(hours=3))

    return NormalizedOddsUpdate(
        book_id=book_id,
        book_event_id=f"game-{game_idx}",
        sport_key="Baseball",
        league_key="MLB",
        home_team=home_team,
        away_team=away_team,
        start_time=start_time,
        market_type=market_type,
        selection=selection,
        line=line,
        odds=decimal_odds,
        captured_at=captured_at,
        deeplink=f"https://{book_id.lower()}.com/bet/{game_idx}",
    )


def create_synthetic_matched_selection(
    canonical_game_id: str,
    home_team: str,
    away_team: str,
    selection: str,
    book_odds: dict[str, float],
    market_type: str = "moneyline",
    line: float | None = None,
    start_time: datetime | None = None,
    captured_at: datetime | None = None,
) -> MatchedSelection:
    """Create a MatchedSelection with specified multi-book odds."""
    captured_at = captured_at or datetime.now(timezone.utc)
    start_time = start_time or (captured_at + timedelta(hours=3))
    time_window = compute_time_window(start_time)

    return MatchedSelection(
        canonical_game_id=canonical_game_id,
        sport_key="Baseball",
        league_key="MLB",
        home_team=home_team,
        away_team=away_team,
        time_window=time_window,
        market_type=market_type,
        selection=selection,
        line=line,
        book_odds=book_odds,
        updated_at={book: captured_at for book in book_odds},
        start_time=start_time,
        book_deeplinks={book: f"https://{book.lower()}.com" for book in book_odds},
    )


def generate_non_arb_stream(
    count: int = 1000,
    num_games: int = 20,
    books: list[str] | None = None,
    random_seed: int = 42,
) -> list[MatchedSelection]:
    """Generate a sequence of routine odds updates that do not form arbitrage opportunities.

    Simulates normal market vig (implied sum ~ 104% to 108%).
    """
    rng = random.Random(random_seed)
    books = books or ["DraftKings", "FanDuel", "Caesars", "BetMGM"]
    stream: list[MatchedSelection] = []
    base_time = datetime.now(timezone.utc)

    for i in range(count):
        game_idx = i % num_games
        home, away = MLB_MATCHUPS[game_idx % len(MLB_MATCHUPS)]
        selection = "home" if (i % 2 == 0) else "away"
        game_id = f"sim-game-{game_idx}"

        # Standard non-arb odds with typical book vig (e.g. decimal 1.85 to 1.95)
        book_odds = {}
        for book in books:
            # Vary each book's odds slightly around typical prices
            jitter = rng.uniform(-0.04, 0.04)
            book_odds[book] = round(1.90 + jitter, 2)

        ts = base_time + timedelta(milliseconds=i * 5)
        stream.append(
            create_synthetic_matched_selection(
                canonical_game_id=game_id,
                home_team=home,
                away_team=away,
                selection=selection,
                book_odds=book_odds,
                captured_at=ts,
            )
        )

    return stream


def generate_arb_triggering_pairs(
    count: int = 200,
    target_margin: float = 0.035,  # 3.5% margin
    book_a: str = "DraftKings",
    book_b: str = "FanDuel",
    random_seed: int = 42,
) -> list[ArbScenarioPair]:
    """Generate pairs of updates where the second selection completes an arbitrage.

    Calculates exact complementary odds so that:
    Implied sum = (1 / odds_a) + (1 / odds_b) = 1.0 - target_margin
    """
    rng = random.Random(random_seed)
    pairs: list[ArbScenarioPair] = []
    base_time = datetime.now(timezone.utc)

    target_implied_sum = 1.0 - target_margin

    for i in range(count):
        game_id = f"arb-game-{i}"
        home, away = MLB_MATCHUPS[i % len(MLB_MATCHUPS)]

        # Underdog on Book A
        odds_a = round(rng.uniform(2.10, 2.40), 2)
        implied_a = 1.0 / odds_a
        implied_b = target_implied_sum - implied_a
        odds_b = round(1.0 / implied_b, 2)

        actual_margin = 1.0 - ((1.0 / odds_a) + (1.0 / odds_b))
        ts = base_time + timedelta(milliseconds=i * 10)

        # Setup side: Home selection on Book A (and lower price on Book B)
        setup = create_synthetic_matched_selection(
            canonical_game_id=game_id,
            home_team=home,
            away_team=away,
            selection="home",
            book_odds={book_a: odds_a, book_b: 1.80},
            captured_at=ts,
        )

        # Trigger side: Away selection on Book B (and lower price on Book A)
        trigger = create_synthetic_matched_selection(
            canonical_game_id=game_id,
            home_team=home,
            away_team=away,
            selection="away",
            book_odds={book_b: odds_b, book_a: 1.70},
            captured_at=ts + timedelta(milliseconds=2),
        )

        pairs.append(
            ArbScenarioPair(
                setup_selection=setup,
                arb_trigger_selection=trigger,
                expected_margin=actual_margin,
            )
        )

    return pairs
