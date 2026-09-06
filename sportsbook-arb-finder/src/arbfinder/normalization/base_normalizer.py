"""Abstract base class for book-specific normalizers."""

from abc import ABC, abstractmethod

from datetime import datetime
import zoneinfo

from arbfinder.normalization.models import OddsUpdate
from arbfinder.normalization.models import NormalizedOddsUpdate
from arbfinder.normalization.odds_math import convert_odds

__all__ = ["BaseNormalizer"]


class BaseNormalizer(ABC):
    """Converts a raw ``OddsUpdate`` into a canonical ``NormalizedOddsUpdate``.

    Concrete subclasses implement book-specific parsing quirks (timestamp
    formats, odds formats, team-name conventions, line-sign semantics).

    The contract is *soft*: ``normalize`` returns ``None`` — it never raises —
    when a field (e.g. an unknown team name) cannot be resolved.
    """

    def __init__(self, target_odds_format: str = "decimal", target_timezone: str = "America/New_York") -> None:
        self.target_odds_format = target_odds_format
        self.target_timezone = target_timezone
        self._tz = zoneinfo.ZoneInfo(self.target_timezone)

    def _format_odds(self, decimal_odds: float) -> float | str:
        """Format the parsed decimal odds to the configured target format."""
        if self.target_odds_format == "decimal":
            return decimal_odds
        return convert_odds(decimal_odds, self.target_odds_format)

    def _format_datetime(self, dt: datetime) -> datetime:
        """Convert a timezone-aware datetime to the configured target timezone."""
        return dt.astimezone(self._tz)

    @abstractmethod
    def normalize(self, update: OddsUpdate) -> NormalizedOddsUpdate | None:
        """Normalize a single raw update.

        Returns ``None`` (does **not** raise) when any required field
        cannot be resolved to a canonical value.
        """
