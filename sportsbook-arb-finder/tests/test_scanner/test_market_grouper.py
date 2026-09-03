"""Tests for scanner/market_grouper.py."""

from datetime import datetime, timezone

from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.market_grouper import MarketGrouper, MarketGroupKey


def _ms(
    selection: str,
    *,
    canonical_game_id: str = "game-1",
    market_type: str = "moneyline",
    line: float | None = None,
) -> MatchedSelection:
    """Build a minimal MatchedSelection for testing."""
    now = datetime.now(timezone.utc)
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
        book_odds={"BookA": -150},
        updated_at={"BookA": now},
    )


class TestMarketGrouper:
    """Verify selection grouping by market key."""

    def test_matching_keys_group_together(self) -> None:
        grouper = MarketGrouper()
        ms_home = _ms("home")
        ms_away = _ms("away")

        key1 = grouper.add(ms_home)
        key2 = grouper.add(ms_away)

        assert key1 == key2
        group = grouper.get_group(key1)
        assert set(group.keys()) == {"home", "away"}
        assert group["home"] is ms_home
        assert group["away"] is ms_away

    def test_different_market_types_separate(self) -> None:
        """Different market_type → different groups."""
        grouper = MarketGrouper()
        key1 = grouper.add(_ms("home", market_type="moneyline"))
        key2 = grouper.add(_ms("over", market_type="total", line=5.5))

        assert key1 != key2
        assert len(grouper.get_group(key1)) == 1
        assert len(grouper.get_group(key2)) == 1

    def test_different_lines_separate(self) -> None:
        """Same market_type, different lines → different groups."""
        grouper = MarketGrouper()
        key1 = grouper.add(_ms("over", market_type="total", line=5.5))
        key2 = grouper.add(_ms("over", market_type="total", line=6.5))

        assert key1 != key2

    def test_different_games_separate(self) -> None:
        """Different actual games (different teams) → different groups."""
        grouper = MarketGrouper()
        now = datetime.now(timezone.utc)
        ms1 = MatchedSelection(
            canonical_game_id="game-1",
            sport_key="Baseball",
            league_key="MLB",
            home_team="Team A",
            away_team="Team B",
            time_window="full_game",
            market_type="moneyline",
            selection="home",
            line=None,
            book_odds={"BookA": -150},
            updated_at={"BookA": now},
        )
        ms2 = MatchedSelection(
            canonical_game_id="game-2",
            sport_key="Baseball",
            league_key="MLB",
            home_team="Team C",
            away_team="Team D",
            time_window="full_game",
            market_type="moneyline",
            selection="home",
            line=None,
            book_odds={"BookA": -150},
            updated_at={"BookA": now},
        )
        key1 = grouper.add(ms1)
        key2 = grouper.add(ms2)

        assert key1 != key2

    def test_is_complete_true(self) -> None:
        grouper = MarketGrouper()
        key = grouper.add(_ms("home"))
        grouper.add(_ms("away"))

        assert grouper.is_complete(key, {"home", "away"}) is True

    def test_is_complete_false(self) -> None:
        grouper = MarketGrouper()
        key = grouper.add(_ms("home"))

        assert grouper.is_complete(key, {"home", "away"}) is False

    def test_get_group_missing_key(self) -> None:
        grouper = MarketGrouper()
        key = MarketGroupKey(
            sport_key="Baseball",
            league_key="MLB",
            home_team="Nobody",
            away_team="Nobody",
            time_window="full_game",
            market_type="moneyline",
            line=None,
        )
        assert grouper.get_group(key) == {}

    def test_update_replaces_selection(self) -> None:
        """Adding the same selection again updates the group entry."""
        grouper = MarketGrouper()
        ms1 = _ms("home")
        ms2 = _ms("home")  # different object, same selection

        grouper.add(ms1)
        key = grouper.add(ms2)

        group = grouper.get_group(key)
        assert group["home"] is ms2  # replaced with newer

    def test_sign_flipped_spread_lines_group_together(self) -> None:
        """Home at line=-1.5 and away at line=+1.5 should share a group
        because abs(line) is the same.
        """
        grouper = MarketGrouper()
        key1 = grouper.add(_ms("home", market_type="run_line", line=-1.5))
        key2 = grouper.add(_ms("away", market_type="run_line", line=1.5))

        assert key1 == key2
        group = grouper.get_group(key1)
        assert set(group.keys()) == {"home", "away"}

    def test_different_canonical_game_ids_still_group(self) -> None:
        """Selections from different buckets (different UUIDs) but for the
        same game should group together because we key on game identity
        fields, not canonical_game_id.
        """
        grouper = MarketGrouper()
        ms1 = _ms("home", canonical_game_id="uuid-aaa")
        ms2 = _ms("away", canonical_game_id="uuid-bbb")

        key1 = grouper.add(ms1)
        key2 = grouper.add(ms2)

        assert key1 == key2
        group = grouper.get_group(key1)
        assert set(group.keys()) == {"home", "away"}

