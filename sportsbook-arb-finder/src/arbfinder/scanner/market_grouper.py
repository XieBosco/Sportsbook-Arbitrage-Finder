"""Market grouper — groups MatchedSelection objects by game, market, and line."""

from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime, timezone

from arbfinder.matching.output import MatchedSelection

__all__ = ["MarketGroupKey", "MarketGrouper"]


@dataclass(frozen=True)
class MarketGroupKey:
    """Composite key identifying a group of related selections.

    Uses actual game identity fields rather than ``canonical_game_id``
    because each :class:`MatchedSelection` receives a unique UUID per
    bucket (i.e. per selection), so complementary sides of the same
    market would never match on UUID alone.

    ``line`` stores the line from the home team's perspective so that
    sign-flipped spread lines (e.g. home -1.5 / away +1.5) are grouped
    together under -1.5, while home +1.5 / away -1.5 are grouped under 1.5.
    """

    sport_key: str
    league_key: str
    time_window: str
    home_team: str
    away_team: str
    market_type: str
    line: float | None  # home team's line


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
        if selection.line is not None:
            raw_line = -selection.line if selection.selection == "away" else selection.line
            group_line = round(raw_line, 2)
        else:
            group_line = None

        key = MarketGroupKey(
            sport_key=selection.sport_key,
            league_key=selection.league_key,
            time_window=selection.time_window,
            home_team=selection.home_team,
            away_team=selection.away_team,
            market_type=selection.market_type,
            line=group_line,
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

    def evict_expired(
        self, max_age_seconds: float = 86400.0, now: datetime | None = None
    ) -> int:
        """Evict groups whose newest selection timestamp is older than max_age_seconds."""
        if now is None:
            now = datetime.now(timezone.utc)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        keys_to_remove = []
        for key, group in self._groups.items():
            newest_ts = None
            for sel in group.values():
                for ts in sel.updated_at.values():
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if newest_ts is None or ts > newest_ts:
                        newest_ts = ts
            if newest_ts is not None and (now - newest_ts).total_seconds() > max_age_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._groups[key]

        return len(keys_to_remove)

