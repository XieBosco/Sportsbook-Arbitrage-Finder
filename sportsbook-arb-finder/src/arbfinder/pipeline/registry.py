"""Component registry — builds and wires all pipeline components from config."""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.pipeline.config import AppConfig
from arbfinder.pipeline.health import HealthTracker
from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGroupKey, MarketGrouper
from arbfinder.scanner.scanner import Scanner
from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.scanner.sinks.console_sink import ConsoleSink
from arbfinder.scanner.sinks.storage_sink import StorageSink
from arbfinder.scanner.sinks.websocket_sink import WebSocketSink
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.ui_server.app import create_app
from arbfinder.ui_server.connection_manager import ConnectionManager

__all__ = ["PipelineComponents", "build_pipeline_components"]

logger = logging.getLogger(__name__)

# Default expected selections by market type — matches the conventions
# used in test_replay.py and the existing normalizer outputs.
EXPECTED_SELECTIONS_BY_MARKET: dict[str, set[str]] = {
    "moneyline": {"home", "away"},
    "run_line": {"home", "away"},
    "total": {"over", "under"},
    "spread": {"home", "away"},
    "two-way-handicap": {"home", "away"},
}

# Dedup cooldown — how long before re-alerting on the same open arb.
# _DEDUP_COOLDOWN_SECONDS = 5.0
_DEDUP_COOLDOWN_SECONDS = 0.1


def _import_class(dotted_path: str):
    """Dynamically import a class from a dotted module path."""
    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


@dataclass
class PipelineComponents:
    """Container for all shared pipeline components."""

    normalizer: Normalizer
    matcher: Matcher
    scanner: Scanner
    health_tracker: HealthTracker
    sinks: list[OpportunitySink]
    app: object | None = None  # FastAPI app (when websocket sink is enabled)


def build_pipeline_components(config: AppConfig) -> PipelineComponents:
    """Instantiate and wire all shared pipeline components from *config*.

    Raises on import failures so that misconfigured books are caught at
    startup rather than silently failing at runtime.
    """
    # ------------------------------------------------------------------
    # Per-book normaliser registry
    # ------------------------------------------------------------------
    normalizer_map: dict[str, BaseNormalizer] = {}
    for book in config.books:
        if not book.enabled:
            continue
        try:
            normalizer_cls = _import_class(book.normalizer_class)
            normalizer_map[book.name] = normalizer_cls()
            logger.info(
                "Registered normalizer for %s: %s", book.name, book.normalizer_class,
            )
        except Exception:
            logger.exception(
                "Failed to import normalizer for %s: %s",
                book.name,
                book.normalizer_class,
            )
            raise

    normalizer = Normalizer(normalizer_map)

    # ------------------------------------------------------------------
    # Matcher (shared BucketStore + TimeResolver)
    # ------------------------------------------------------------------
    bucket_store = BucketStore()
    time_resolver = TimeResolver()
    matcher = Matcher(bucket_store, time_resolver)

    # ------------------------------------------------------------------
    # Sinks
    # ------------------------------------------------------------------
    sinks: list[OpportunitySink] = []
    if config.sinks.console_enabled:
        sinks.append(ConsoleSink(sinks_config=config.sinks))
        logger.info("Console sink enabled")
    if config.sinks.file_enabled:
        sinks.append(StorageSink())
        logger.info("File/storage sink enabled")
    app = None
    if config.sinks.websocket_enabled:
        connection_manager = ConnectionManager()
        ws_sink = WebSocketSink(connection_manager, sinks_config=config.sinks)
        sinks.append(ws_sink)
        app = create_app(connection_manager, config=config)
        logger.info(
            "WebSocket sink enabled — UI at http://%s:%d",
            config.server.host,
            config.server.port,
        )
    if config.sinks.execution_enabled:
        logger.warning(
            "⚠️  EXECUTION SINK ENABLED — real money bets will be placed!  "
            "(Not yet implemented, this is a placeholder warning)"
        )

    # ------------------------------------------------------------------
    # Scanner
    # ------------------------------------------------------------------
    staleness_filter = StalenessFilter(
        thresholds=config.scanner,
    )
    dedup = DedupTracker(cooldown_seconds=_DEDUP_COOLDOWN_SECONDS)
    grouper = MarketGrouper()

    def stake_budget_fn(key: MarketGroupKey) -> float:
        return config.arbitrage.total_bet_amount

    scanner = Scanner(
        grouper=grouper,
        thresholds=config.scanner,
        staleness_filter=staleness_filter,
        dedup=dedup,
        sinks=sinks,
        expected_selections_by_market=EXPECTED_SELECTIONS_BY_MARKET,
        stake_budget_fn=stake_budget_fn,
    )

    # ------------------------------------------------------------------
    # Health tracker
    # ------------------------------------------------------------------
    health_tracker = HealthTracker()

    return PipelineComponents(
        normalizer=normalizer,
        matcher=matcher,
        scanner=scanner,
        health_tracker=health_tracker,
        sinks=sinks,
        app=app,
    )
