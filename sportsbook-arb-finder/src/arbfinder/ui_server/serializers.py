"""Serializers — convert scanner data-classes to JSON-safe dicts.

Rounding conventions
--------------------
- ``margin``: 4 decimal places (e.g. 0.0312)
- ``margin_pct``: ``margin * 100``, 2 dp (e.g. 3.12)
- ``odds_decimal``: 2 dp per leg
- ``stake``: 2 dp per leg
- ``line``: 1 dp (when present)
- ``datetime`` fields: ISO 8601 strings
"""

from __future__ import annotations

from arbfinder.scanner.schema import Leg, Opportunity
from arbfinder.utils.odds import format_odds

__all__ = ["serialize_opportunity"]


def _serialize_leg(leg: Leg, odds_format: str) -> dict:
    return {
        "book_id": leg.book_id,
        "selection": leg.selection,
        "odds_decimal": round(leg.odds_decimal, 2),
        "odds_formatted": format_odds(leg.odds_decimal, odds_format),
        "stake": round(leg.stake, 2),
        "captured_at": leg.captured_at.isoformat(),
    }


def serialize_opportunity(opp: Opportunity, odds_format: str = "american") -> dict:
    """Convert an :class:`Opportunity` into a JSON-safe dictionary.

    Every field of the dataclass is mapped 1-to-1, plus a derived
    ``margin_pct`` convenience field for display purposes.
    """
    return {
        "opportunity_id": opp.opportunity_id,
        "canonical_game_id": opp.canonical_game_id,
        "sport_key": opp.sport_key,
        "league_key": opp.league_key,
        "home_team": opp.home_team,
        "away_team": opp.away_team,
        "market_type": opp.market_type,
        "line": round(opp.line, 1) if opp.line is not None else None,
        "margin": round(opp.margin, 4),
        "margin_pct": round(opp.margin * 100, 2),
        "legs": [_serialize_leg(leg, odds_format) for leg in opp.legs],
        "detected_at": opp.detected_at.isoformat(),
        "expires_hint_seconds": opp.expires_hint_seconds,
    }
