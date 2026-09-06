"""Tests for core/arbitrage.py — arb detection and single-book conflict."""

from datetime import datetime, timezone

from arbfinder.core.arbitrage import ArbCheckResult, check_arbitrage, has_single_book_conflict
from arbfinder.matching.output import MatchedSelection
from arbfinder.normalization.odds_math import american_to_decimal


def _ms(
    selection: str,
    book_odds: dict[str, float],
    *,
    canonical_game_id: str = "game-1",
    market_type: str = "moneyline",
    line: float | None = None,
) -> MatchedSelection:
    """Build a minimal MatchedSelection for testing."""
    now = datetime.now(timezone.utc)
    decimal_book_odds = {}
    for book, odds in book_odds.items():
        if odds <= 0 or odds >= 100:
            decimal_book_odds[book] = american_to_decimal(int(round(odds)))
        else:
            decimal_book_odds[book] = float(odds)

    return MatchedSelection(
        canonical_game_id=canonical_game_id,
        sport_key="Baseball",
        league_key="MLB",
        home_team="Team A",
        away_team="Team B",
        time_window="full_game",
        market_type=market_type,
        selection=selection,
        line=line,
        book_odds=decimal_book_odds,
        updated_at={book: now for book in book_odds},
    )


# ------------------------------------------------------------------
# Two-way arb / non-arb
# ------------------------------------------------------------------


class TestTwoWayArbitrage:
    """Verify two-way arb detection with hand-computed margins."""

    def test_positive_margin(self) -> None:
        """Home +250 (BookA) / Away -200 (BookB)
        Decimal: 3.5 / 1.5
        Implied: 1/3.5 + 1/1.5 = 0.2857 + 0.6667 = 0.9524
        Margin: 1 - 0.9524 = 0.0476  (~4.76%)
        """
        group = {
            "home": _ms("home", {"BookA": 250, "BookB": -110}),
            "away": _ms("away", {"BookA": -300, "BookB": -200}),
        }
        result = check_arbitrage(group)

        assert result.is_arbitrage is True
        # BookA +250 → 3.50 is best for home
        assert result.best_odds_by_selection["home"] == ("BookA", 3.5)
        # BookB -200 → 1.50 is best for away
        assert result.best_odds_by_selection["away"] == ("BookB", 1.5)
        # Margin ≈ 4.76%
        assert abs(result.margin - (1.0 - (1 / 3.5 + 1 / 1.5))) < 1e-9

    def test_negative_margin(self) -> None:
        """Home -200 / Away +150 → no arb.
        Decimal: 1.50 / 2.50
        Implied: 1/1.5 + 1/2.5 = 0.6667 + 0.40 = 1.0667
        Margin: -0.0667 (negative → not arb)
        """
        group = {
            "home": _ms("home", {"BookA": -200}),
            "away": _ms("away", {"BookA": 150}),
        }
        result = check_arbitrage(group)

        assert result.is_arbitrage is False
        assert result.margin < 0

    def test_best_odds_picked_across_books(self) -> None:
        """Ensure we pick the highest decimal odds from each book."""
        group = {
            "home": _ms("home", {"BookA": 200, "BookB": 250}),
            "away": _ms("away", {"BookA": -150, "BookB": -200}),
        }
        result = check_arbitrage(group)

        # BookB +250 → 3.50 beats BookA +200 → 3.00 for home
        assert result.best_odds_by_selection["home"][0] == "BookB"
        # BookA -150 → 1.667 beats BookB -200 → 1.50 for away
        assert result.best_odds_by_selection["away"][0] == "BookA"


# ------------------------------------------------------------------
# Three-way arb
# ------------------------------------------------------------------


class TestThreeWayArbitrage:
    """Verify three-way arb detection (e.g. soccer with draw)."""

    def test_three_way_positive_margin(self) -> None:
        """Home +250 / Draw +400 / Away +300
        Decimal: 3.50 / 5.00 / 4.00
        Implied: 1/3.5 + 1/5.0 + 1/4.0 = 0.2857 + 0.20 + 0.25 = 0.7357
        Margin: 0.2643  (~26.4%)
        """
        group = {
            "home": _ms("home", {"BookA": 250}),
            "draw": _ms("draw", {"BookB": 400}),
            "away": _ms("away", {"BookC": 300}),
        }
        result = check_arbitrage(group)

        assert result.is_arbitrage is True
        expected_margin = 1.0 - (1 / 3.5 + 1 / 5.0 + 1 / 4.0)
        assert abs(result.margin - expected_margin) < 1e-9

    def test_three_way_negative_margin(self) -> None:
        """Home -200 / Draw +200 / Away +150
        Decimal: 1.50 / 3.00 / 2.50
        Implied: 1/1.5 + 1/3.0 + 1/2.5 = 0.667 + 0.333 + 0.400 = 1.400
        Margin: -0.400 (negative → not arb)
        """
        group = {
            "home": _ms("home", {"BookA": -200}),
            "draw": _ms("draw", {"BookA": 200}),
            "away": _ms("away", {"BookA": 150}),
        }
        result = check_arbitrage(group)

        assert result.is_arbitrage is False
        assert result.margin < 0


# ------------------------------------------------------------------
# Single-book conflict
# ------------------------------------------------------------------


class TestSingleBookConflict:
    """Verify has_single_book_conflict correctly flags same-book-both-legs."""

    def test_same_book_both_legs(self) -> None:
        """Same book offers best price for both selections → conflict."""
        result = ArbCheckResult(
            is_arbitrage=True,
            margin=0.05,
            best_odds_by_selection={
                "home": ("BookA", 3.0),
                "away": ("BookA", 2.0),
            },
        )
        assert has_single_book_conflict(result) is True

    def test_different_books(self) -> None:
        """Different books → no conflict."""
        result = ArbCheckResult(
            is_arbitrage=True,
            margin=0.05,
            best_odds_by_selection={
                "home": ("BookA", 3.0),
                "away": ("BookB", 2.0),
            },
        )
        assert has_single_book_conflict(result) is False

    def test_three_way_one_book_repeated(self) -> None:
        """Three selections where one book appears twice → conflict."""
        result = ArbCheckResult(
            is_arbitrage=True,
            margin=0.05,
            best_odds_by_selection={
                "home": ("BookA", 3.0),
                "draw": ("BookB", 4.0),
                "away": ("BookA", 2.5),
            },
        )
        assert has_single_book_conflict(result) is True

    def test_three_way_all_different(self) -> None:
        """Three selections, three different books → no conflict."""
        result = ArbCheckResult(
            is_arbitrage=True,
            margin=0.05,
            best_odds_by_selection={
                "home": ("BookA", 3.0),
                "draw": ("BookB", 4.0),
                "away": ("BookC", 2.5),
            },
        )
        assert has_single_book_conflict(result) is False
