"""Scanner output data structures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = ["Leg", "Opportunity"]


@dataclass(frozen=True)
class Leg:
    """A single leg of an arbitrage opportunity."""

    book_id: str
    selection: str
    odds_decimal: float
    stake: float
    captured_at: datetime


@dataclass(frozen=True)
class Opportunity:
    """A detected arbitrage opportunity across books."""

    opportunity_id: str  # uuid4
    canonical_game_id: str
    sport_key: str
    league_key: str
    home_team: str
    away_team: str
    market_type: str
    line: float | None
    margin: float
    legs: list[Leg]
    detected_at: datetime
    expires_hint_seconds: float | None
