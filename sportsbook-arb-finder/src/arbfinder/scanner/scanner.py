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
        self._active_arbs: dict[MarketGroupKey, tuple[str, str, float | None]] = {}

    def _close_if_active(self, group_key: MarketGroupKey) -> None:
        if group_key in self._active_arbs:
            canon_id, market_type, line = self._active_arbs.pop(group_key)
            for sink in self._sinks:
                try:
                    sink.emit_close(canon_id, market_type, line)
                except Exception:
                    logger.exception(
                        "Sink %r failed to emit close for %s",
                        sink,
                        canon_id,
                    )

    def sweep_active_arbs(self, now: datetime | None = None) -> None:
        """Periodically evaluate all active arbs to evict stale ones."""
        if now is None:
            now = datetime.now(timezone.utc)

        for group_key in list(self._active_arbs.keys()):
            if group_key.market_type.lower() in self._thresholds.excluded_markets:
                self._close_if_active(group_key)
                continue

            expected = self._expected.get(group_key.market_type)
            if expected is None or not self._grouper.is_complete(group_key, expected):
                self._close_if_active(group_key)
                continue

            group = self._grouper.get_group(group_key)
            filtered_group = {}
            excluded = self._thresholds.excluded_books
            
            for sel, ms in group.items():
                filtered_ms = self._staleness.filter_stale_books(ms, now)
                if filtered_ms is None:
                    break
                    
                if excluded:
                    to_remove = [b for b in filtered_ms.book_odds if b.lower() in excluded]
                    for b in to_remove:
                        filtered_ms.book_odds.pop(b, None)
                        filtered_ms.updated_at.pop(b, None)
                        
                    if not filtered_ms.book_odds:
                        break
                        
                filtered_group[sel] = filtered_ms

            if len(filtered_group) < len(group):
                self._close_if_active(group_key)
                continue

            result = check_arbitrage(filtered_group)
            if not result.is_arbitrage or result.margin < self._thresholds.min_margin:
                self._close_if_active(group_key)
                continue

            if has_single_book_conflict(result):
                self._close_if_active(group_key)

    def process(self, matched: MatchedSelection, now: datetime | None = None) -> Opportunity | None:
        """Process a single *matched* selection through the full pipeline.

        Returns an :class:`Opportunity` if an arb is detected and passes
        all filters, or ``None`` otherwise.
        """
        if matched.market_type.lower() in self._thresholds.excluded_markets:
            return None

        if now is None:
            now = datetime.now(timezone.utc)

        # 1. Add to grouper, get group_key
        group_key = self._grouper.add(matched)

        # 2. Check completeness
        expected = self._expected.get(matched.market_type)
        if expected is None:
            self._close_if_active(group_key)
            return None
        if not self._grouper.is_complete(group_key, expected):
            self._close_if_active(group_key)
            return None

        # 3. Staleness check and excluded books filtering
        group = self._grouper.get_group(group_key)
        filtered_group = {}
        excluded = self._thresholds.excluded_books
        
        for sel, ms in group.items():
            filtered_ms = self._staleness.filter_stale_books(ms, now)
            if filtered_ms is None:
                self._close_if_active(group_key)
                return None
                
            if excluded:
                to_remove = [b for b in filtered_ms.book_odds if b.lower() in excluded]
                for b in to_remove:
                    filtered_ms.book_odds.pop(b, None)
                    filtered_ms.updated_at.pop(b, None)
                    
                if not filtered_ms.book_odds:
                    self._close_if_active(group_key)
                    return None
                    
            filtered_group[sel] = filtered_ms

        # 4. Arbitrage check
        result = check_arbitrage(filtered_group)
        if not result.is_arbitrage or result.margin < self._thresholds.min_margin:
            self._close_if_active(group_key)
            return None

        # 5. Single-book conflict check
        if has_single_book_conflict(result):
            self._close_if_active(group_key)
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
        # Pick any MatchedSelection in the filtered group for shared fields
        # (they're identical across the group by construction).
        representative = next(iter(filtered_group.values()))

        legs = []
        for sel, (book_id, decimal_odds) in result.best_odds_by_selection.items():
            ms = filtered_group[sel]
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

        # Record as active
        self._active_arbs[group_key] = (
            opportunity.canonical_game_id,
            opportunity.market_type,
            opportunity.line,
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
