"""Top-level orchestrator — startup, run loop, graceful shutdown.

Wires all components and manages the lifecycle of per-book pipeline
tasks, the health monitor, and signal-based shutdown.

Also exposes :func:`handle_raw_payload` for deterministic testing of
the parse → normalise → match chain without a live CDP connection.
"""

from __future__ import annotations

import asyncio
import logging
import logging.config
import signal
import sys
from pathlib import Path

import yaml

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.output import MatchOutputBuilder, MatchedSelection
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.parsers.base import BookParser
from arbfinder.pipeline.book_pipeline import run_book_pipeline
from arbfinder.pipeline.config import AppConfig
from arbfinder.pipeline.health import HealthTracker
from arbfinder.pipeline.registry import build_pipeline_components

__all__ = ["run", "handle_raw_payload"]

logger = logging.getLogger(__name__)

# Constants
HEALTH_POLL_INTERVAL_SECONDS = 30.0
STALE_FEED_THRESHOLD_SECONDS = 60.0
SHUTDOWN_TIMEOUT_SECONDS = 15.0
SHUTDOWN_FORCE_CANCEL_TIMEOUT_SECONDS = 5.0


# ------------------------------------------------------------------
# Logging bootstrap
# ------------------------------------------------------------------

def _resolve_handler_paths(log_config: dict, project_root: Path) -> None:
    """Make every file handler's ``filename`` absolute and ensure its dir exists.

    Mutates *log_config* in place so relative paths in the YAML are resolved
    against *project_root* rather than the process's current working
    directory, which would otherwise vary depending on how the app is
    launched.
    """
    for handler in log_config.get("handlers", {}).values():
        if "filename" not in handler:
            continue
        log_file = Path(handler["filename"])
        if not log_file.is_absolute():
            log_file = project_root / log_file
            handler["filename"] = str(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)


def _fallback_logging() -> None:
    """Minimal ``basicConfig`` used when no dictConfig file is available."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _configure_logging(config_path: str | None) -> None:
    """Set up logging from a YAML dictConfig file, or fall back to basicConfig."""
    if not config_path:
        _fallback_logging()
        return

    project_root = Path(__file__).resolve().parents[3]
    path = Path(config_path)
    if not path.is_absolute():
        path = project_root / path

    if not path.exists():
        print(
            f"WARNING: Logging config not found at {path}, using defaults",
            file=sys.stderr,
        )
        _fallback_logging()
        return

    with path.open(encoding="utf-8") as fh:
        log_config = yaml.safe_load(fh)

    _resolve_handler_paths(log_config, project_root)
    logging.config.dictConfig(log_config)


# ------------------------------------------------------------------
# Background health monitor
# ------------------------------------------------------------------

async def _health_monitor(
    health_tracker: HealthTracker,
    stop_event: asyncio.Event,
) -> None:
    """Background task polling feed health every ~30 s."""
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=HEALTH_POLL_INTERVAL_SECONDS,
            )
            break  # stop_event was set
        except asyncio.TimeoutError:
            pass  # Normal timeout — perform health check

        stale_books = health_tracker.get_stale_books(STALE_FEED_THRESHOLD_SECONDS)
        if stale_books:
            logger.warning(
                "Stale feeds detected (no data for >%.0fs): %s",
                STALE_FEED_THRESHOLD_SECONDS,
                ", ".join(stale_books),
            )

        all_health = health_tracker.get_all()

        disconnected = [b for b, h in all_health.items() if not h.connected]
        if disconnected:
            logger.warning("Disconnected books: %s", ", ".join(disconnected))

        uninit = [
            b for b, h in all_health.items()
            if h.connected and not h.initialized
        ]
        if uninit:
            logger.warning(
                "Connected but not initialised (missing initial state): %s",
                ", ".join(uninit),
            )


# ------------------------------------------------------------------
# Top-level orchestrator
# ------------------------------------------------------------------

async def run(config: AppConfig) -> None:
    """Top-level orchestrator: start all book pipelines and manage lifecycle.

    1. Configure logging.
    2. Build shared pipeline components.
    3. Launch one ``asyncio.Task`` per enabled book.
    4. Background health-polling task (~30 s interval).
    5. SIGINT / SIGTERM handlers set *stop_event*.
    6. Await shutdown, gather results, log failures.
    """
    _configure_logging(config.logging_config_path)

    banner = "=" * 60
    logger.info(banner)
    logger.info("Sportsbook Arbitrage Finder — starting up")
    logger.info(banner)

    # Build shared components
    components = build_pipeline_components(config)

    enabled_books = [b for b in config.books if b.enabled]
    if not enabled_books:
        logger.error("No books enabled in configuration — nothing to do.")
        return

    logger.info(
        "Enabled books: %s",
        ", ".join(b.name for b in enabled_books),
    )

    # Shared stop event
    stop_event = asyncio.Event()

    # ------ Signal handlers (Unix) ------
    loop = asyncio.get_running_loop()

    def _request_shutdown() -> None:
        if not stop_event.is_set():
            logger.info("Shutdown signal received")
            stop_event.set()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, _request_shutdown)
    except NotImplementedError:
        pass  # Windows — KeyboardInterrupt handled via CancelledError

    # ------ Launch per-book pipeline tasks ------
    book_tasks: list[asyncio.Task] = [
        asyncio.create_task(
            run_book_pipeline(
                book_config=book,
                normalizer=components.normalizer,
                matcher=components.matcher,
                scanner=components.scanner,
                health_tracker=components.health_tracker,
                stop_event=stop_event,
                cdp_port=config.cdp_port,
            ),
            name=f"book-{book.name}",
        )
        for book in enabled_books
    ]

    # Health monitor
    health_task = asyncio.create_task(
        _health_monitor(components.health_tracker, stop_event),
        name="health-monitor",
    )

    # ------ Wait for shutdown ------
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        # Windows: KeyboardInterrupt causes CancelledError on the main task
        stop_event.set()

    # ------ Graceful shutdown ------
    logger.info(
        "Initiating graceful shutdown (timeout=%ds)…",
        SHUTDOWN_TIMEOUT_SECONDS,
    )

    # Stop health monitor immediately
    health_task.cancel()

    # Wait for book tasks to finish (they check stop_event in their loops)
    if book_tasks:
        done, pending = await asyncio.wait(
            book_tasks, timeout=SHUTDOWN_TIMEOUT_SECONDS,
        )
        for task in pending:
            logger.warning(
                "Task %s did not exit within timeout, cancelling",
                task.get_name(),
            )
            task.cancel()
        if pending:
            await asyncio.wait(
                pending, timeout=SHUTDOWN_FORCE_CANCEL_TIMEOUT_SECONDS,
            )

    # Log final task statuses
    all_tasks = book_tasks + [health_task]
    for task in all_tasks:
        if task.done():
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                continue
            if exc is not None:
                logger.error(
                    "Task %s exited with error: %s",
                    task.get_name(),
                    exc,
                    exc_info=exc,
                )

    logger.info("Pipeline shutdown complete.")


# ------------------------------------------------------------------
# Sync utility (used by tests — no live CDP required)
# ------------------------------------------------------------------

def handle_raw_payload(
    book_id: str,
    raw_payload: bytes,
    parser_registry: dict[str, BookParser],
    normalizer: Normalizer,
    matcher: Matcher,
    bucket_store: BucketStore,
) -> list[MatchedSelection]:
    """Process a raw byte payload through parse → normalise → match.

    Designed for deterministic testing (no CDP, no async).  Returns
    :class:`MatchedSelection` objects suitable for feeding to the
    scanner.

    Parameters
    ----------
    book_id:
        Key into *parser_registry*.
    raw_payload:
        Raw bytes (typically JSON) as captured by CDP.
    parser_registry:
        ``{book_id: BookParser}`` mapping.
    normalizer:
        The batch :class:`Normalizer`.
    matcher:
        The shared :class:`Matcher` instance.
    bucket_store:
        The shared :class:`BucketStore` (passed for signature
        compatibility — the matcher already owns a reference to it).
    """
    parser = parser_registry.get(book_id)
    if parser is None:
        logger.warning("No parser registered for book_id=%s", book_id)
        return []

    body = raw_payload.decode("utf-8", errors="replace")

    try:
        updates = parser.handle_http_body("", body)
    except Exception:
        logger.exception("Parser error for book_id=%s", book_id)
        return []

    if not updates:
        return []

    normalized = normalizer.normalize_batch(updates)
    if not normalized:
        return []

    return [
        MatchOutputBuilder.from_bucket(matcher.assign(norm_update))
        for norm_update in normalized
    ]