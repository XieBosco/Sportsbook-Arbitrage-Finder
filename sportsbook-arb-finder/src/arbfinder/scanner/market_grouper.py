"""Market grouper — groups MatchedSelection objects by game, market, and line."""

from __future__ import annotations

from dataclasses import dataclass

from arbfinder.matching.output import MatchedSelection

__all__ = ["MarketGroupKey", "MarketGrouper"]


@dataclass(frozen=True)
class MarketGroupKey:
    """Composite key identifying a group of related selections.

    Uses actual game identity fields rather than ``canonical_game_id``
    because each :class:`MatchedSelection` receives a unique UUID per
    bucket (i.e. per selection), so complementary sides of the same
    market would never match on UUID alone.

    ``line`` stores ``abs(line)`` so that sign-flipped spread lines
    (e.g. home −1.5 / away +1.5) are grouped together.
    """

    sport_key: str
    league_key: str
    home_team: str
    away_team: str
    market_type: str
    line: float | None  # abs(line) for proper grouping


class MarketGrouper:
    """Groups incoming :class:`MatchedSelection` objects by market.

    Internally maintains a mapping from :class:`MarketGroupKey` to a dict
    of ``selection -> MatchedSelection``, so that all selections for the
    same game + market + line are grouped together.
    """

    def __init__(self) -> None:
        self._groups: dict[MarketGroupKey, dict[str, MatchedSelection]] = {}

    def add(self, selection: MatchedSelection) -> MarketGroupKey:
        """Insert or update *selection* in its group, returning the key."""
        key = MarketGroupKey(
            sport_key=selection.sport_key,
            league_key=selection.league_key,
            home_team=selection.home_team,
            away_team=selection.away_team,
            market_type=selection.market_type,
            line=abs(selection.line) if selection.line is not None else None,
        )
        group = self._groups.setdefault(key, {})
        group[selection.selection] = selection
        return key

    def get_group(self, key: MarketGroupKey) -> dict[str, MatchedSelection]:
        """Return the group for *key*, or an empty dict if absent."""
        return self._groups.get(key, {})

    def is_complete(
        self, key: MarketGroupKey, expected_selections: set[str]
    ) -> bool:
        """Return True if all *expected_selections* are present in the group."""
        group = self._groups.get(key, {})
        return expected_selections.issubset(group.keys())

