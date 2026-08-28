"""Scanner — orchestrates arb detection for incoming MatchedSelection objects."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from arbfinder.core.arbitrage import check_arbitrage, has_single_book_conflict
from arbfinder.core.stake_calculator import compute_stakes
from arbfinder.matching.output import MatchedSelection
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGroupKey, MarketGrouper
from arbfinder.scanner.schema import Leg, Opportunity
from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.scanner.threshold_config import ScannerThresholds

__all__ = ["Scanner"]

logger = logging.getLogger(__name__)


class Scanner:
    """Stateful scanner that processes :class:`MatchedSelection` objects
    one at a time and emits :class:`Opportunity` objects when an
    arbitrage is detected.

    Parameters
    ----------
    grouper:
        Groups selections by game/market/line.
    thresholds:
        Validated scanner thresholds (margin, staleness, etc.).
    staleness_filter:
        Rejects groups with stale book timestamps.
    dedup:
        Prevents re-alerting on the same still-open arb.
    sinks:
        List of output sinks (console, storage, webhook, …).
    expected_selections_by_market:
        Mapping of ``market_type -> set of expected selections``,
        e.g. ``{"moneyline": {"home", "away"}}``.
    stake_budget_fn:
        Injected function returning the available stake budget for a
        given :class:`MarketGroupKey`.
    """

    def __init__(
        self,
        grouper: MarketGrouper,
        thresholds: ScannerThresholds,
        staleness_filter: StalenessFilter,
        dedup: DedupTracker,
        sinks: list[OpportunitySink],
        expected_selections_by_market: dict[str, set[str]],
        stake_budget_fn: Callable[[MarketGroupKey], float],
    ) -> None:
        self._grouper = grouper
        self._thresholds = thresholds
        self._staleness = staleness_filter
        self._dedup = dedup
        self._sinks = sinks
        self._expected = expected_selections_by_market
        self._budget_fn = stake_budget_fn

    def process(self, matched: MatchedSelection) -> Opportunity | None:
        """Process a single *matched* selection through the full pipeline.

        Returns an :class:`Opportunity` if an arb is detected and passes
        all filters, or ``None`` otherwise.
        """
        now = datetime.now(timezone.utc)

        # 1. Add to grouper, get group_key
        group_key = self._grouper.add(matched)

        # 2. Check completeness
        expected = self._expected.get(matched.market_type)
        if expected is None:
            return None
        if not self._grouper.is_complete(group_key, expected):
            return None

        # 3. Staleness check on all legs in the group
        group = self._grouper.get_group(group_key)
        for ms in group.values():
            if not self._staleness.is_fresh(ms, now):
                return None

        # 4. Arbitrage check
        result = check_arbitrage(group)
        if not result.is_arbitrage or result.margin < self._thresholds.min_margin:
            return None

        # 5. Single-book conflict check
        if has_single_book_conflict(result):
            return None

        # 6. Dedup check
        if not self._dedup.should_emit(group_key, now):
            return None

        # 7. Compute stakes
        total_stake = self._budget_fn(group_key)
        odds_by_selection = {
            sel: odds for sel, (_, odds) in result.best_odds_by_selection.items()
        }
        stakes = compute_stakes(odds_by_selection, total_stake)

        # 8. Build Opportunity
        # Pick any MatchedSelection in the group for shared fields
        # (they're identical across the group by construction).
        representative = next(iter(group.values()))

        legs = []
        for sel, (book_id, decimal_odds) in result.best_odds_by_selection.items():
            ms = group[sel]
            captured_at = ms.updated_at.get(book_id, now)
            legs.append(
                Leg(
                    book_id=book_id,
                    selection=sel,
                    odds_decimal=decimal_odds,
                    stake=stakes[sel],
                    captured_at=captured_at,
                )
            )

        opportunity = Opportunity(
            opportunity_id=str(uuid.uuid4()),
            canonical_game_id=representative.canonical_game_id,
            sport_key=representative.sport_key,
            league_key=representative.league_key,
            home_team=representative.home_team,
            away_team=representative.away_team,
            market_type=representative.market_type,
            line=representative.line,
            margin=result.margin,
            legs=legs,
            detected_at=now,
            expires_hint_seconds=self._thresholds.max_odds_age_seconds,
        )

        # 9. Emit to all sinks (catch per-sink exceptions)
        for sink in self._sinks:
            try:
                sink.emit(opportunity)
            except Exception:
                logger.exception(
                    "Sink %r failed for opportunity %s",
                    sink,
                    opportunity.opportunity_id,
                )

        return opportunity
