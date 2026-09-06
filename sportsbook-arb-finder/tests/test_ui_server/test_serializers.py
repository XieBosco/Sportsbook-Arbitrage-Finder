"""Tests for serialize_opportunity — field mapping, rounding, types."""

from __future__ import annotations

from datetime import datetime, timezone

from arbfinder.scanner.schema import Leg, Opportunity
from arbfinder.ui_server.serializers import serialize_opportunity


def _make_opportunity() -> Opportunity:
    """Build a realistic Opportunity fixture."""
    return Opportunity(
        opportunity_id="abc-123",
        canonical_game_id="game-789",
        sport_key="baseball_mlb",
        league_key="MLB",
        home_team="Philadelphia Phillies",
        away_team="Los Angeles Angels",
        market_type="moneyline",
        line=None,
        margin=0.031256789,
        legs=[
            Leg(
                book_id="DraftKings",
                selection="home",
                odds_decimal=2.15678,
                stake=48.12345,
                captured_at=datetime(2026, 8, 30, 14, 30, 0, tzinfo=timezone.utc),
            ),
            Leg(
                book_id="FanDuel",
                selection="away",
                odds_decimal=1.89123,
                stake=51.87655,
                captured_at=datetime(2026, 8, 30, 14, 30, 5, tzinfo=timezone.utc),
            ),
        ],
        detected_at=datetime(2026, 8, 30, 14, 30, 10, tzinfo=timezone.utc),
        expires_hint_seconds=5.0,
    )


def test_top_level_fields():
    opp = _make_opportunity()
    result = serialize_opportunity(opp)

    assert result["opportunity_id"] == "abc-123"
    assert result["canonical_game_id"] == "game-789"
    assert result["sport_key"] == "baseball_mlb"
    assert result["league_key"] == "MLB"
    assert result["home_team"] == "Philadelphia Phillies"
    assert result["away_team"] == "Los Angeles Angels"
    assert result["start_time"] is None
    assert result["market_type"] == "moneyline"
    assert result["line"] is None
    assert result["expires_hint_seconds"] == 5.0


def test_start_time_serialization():
    opp = _make_opportunity()
    st = datetime(2026, 1, 23, 22, 0, 0, tzinfo=timezone.utc)
    opp_with_st = Opportunity(
        opportunity_id=opp.opportunity_id,
        canonical_game_id=opp.canonical_game_id,
        sport_key=opp.sport_key,
        league_key=opp.league_key,
        home_team=opp.home_team,
        away_team=opp.away_team,
        market_type=opp.market_type,
        line=opp.line,
        margin=opp.margin,
        legs=opp.legs,
        detected_at=opp.detected_at,
        expires_hint_seconds=opp.expires_hint_seconds,
        start_time=st,
    )
    result = serialize_opportunity(opp_with_st)
    assert result["start_time"] == "2026-01-23T22:00:00+00:00"


def test_margin_rounding():
    opp = _make_opportunity()
    result = serialize_opportunity(opp)

    assert result["margin"] == 0.0313  # 4 dp
    assert result["margin_pct"] == 3.13  # 2 dp


def test_datetime_fields_are_iso_strings():
    opp = _make_opportunity()
    result = serialize_opportunity(opp)

    assert isinstance(result["detected_at"], str)
    assert "2026-08-30" in result["detected_at"]

    for leg in result["legs"]:
        assert isinstance(leg["captured_at"], str)
        assert "2026-08-30" in leg["captured_at"]


def test_leg_rounding():
    opp = _make_opportunity()
    result = serialize_opportunity(opp)
    leg0 = result["legs"][0]
    leg1 = result["legs"][1]

    assert leg0["odds_decimal"] == 2.16  # 2 dp
    assert leg0["stake"] == 48.12        # 2 dp
    assert leg1["odds_decimal"] == 1.89
    assert leg1["stake"] == 51.88


def test_leg_fields_complete():
    opp = _make_opportunity()
    result = serialize_opportunity(opp)

    for leg in result["legs"]:
        assert "book_id" in leg
        assert "selection" in leg
        assert "odds_decimal" in leg
        assert "stake" in leg
        assert "captured_at" in leg
        assert "deeplink" in leg


def test_line_with_value():
    """Verify line is rounded to 1dp when present."""
    opp = Opportunity(
        opportunity_id="x",
        canonical_game_id="g",
        sport_key="s",
        league_key="l",
        home_team="H",
        away_team="A",
        market_type="run_line",
        line=-1.567,
        margin=0.02,
        legs=[],
        detected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        expires_hint_seconds=None,
    )
    result = serialize_opportunity(opp)
    assert result["line"] == -1.6
    assert result["expires_hint_seconds"] is None
