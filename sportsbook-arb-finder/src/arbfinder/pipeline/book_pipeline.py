"""Per-book pipeline: CDP connect → initial state → parse → normalize → match → scan.

Each book runs in its own :func:`run_book_pipeline` coroutine.  The
blocking :class:`CDPClient` is bridged to asyncio via
``asyncio.to_thread`` with a queue-based callback relay.

CRITICAL ORDERING REQUIREMENT (Developer Guide, Layer 2):
  The parser's ``handle_http_body()`` MUST process the initial full-state
  payload (which maps internal UUIDs to team names) BEFORE any
  ``handle_ws_frame()`` calls will decode correctly.  Live ticks are
  minimal deltas keyed by those UUIDs, so decoding them against a missing
  ID map silently produces garbage.

  The implementation gates WS frame processing on
  ``parser.is_initialized`` and logs/drops frames received before the
  initial-state HTTP response arrives.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from arbfinder.cdp.client import CDPClient
from arbfinder.cdp.discovery import find_tab
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.output import MatchOutputBuilder
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.pipeline._import_utils import import_class
from arbfinder.pipeline.health import HealthTracker
from arbfinder.scanner.scanner import Scanner

if TYPE_CHECKING:
    from arbfinder.pipeline.config import BookConfig

__all__ = ["run_book_pipeline"]

logger = logging.getLogger(__name__)

# Exponential backoff bounds shared by session-level and tab-discovery retries.
_INITIAL_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0

# Truncation length for logged WS URLs (avoid dumping long query strings).
_WS_URL_LOG_CHARS = 80


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _backoff_wait(stop_event: asyncio.Event, seconds: float) -> None:
    """Wait for *seconds* unless *stop_event* fires first."""
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


class _ExponentialBackoff:
    """Tracks a doubling retry delay capped at *max_seconds*.

    Both the session retry loop and the tab-discovery loop need the same
    "wait, then double, cap at N" behaviour; this centralises it so the
    growth/cap values can't drift out of sync between the two call sites.
    """

    def __init__(
        self,
        initial_seconds: float = _INITIAL_BACKOFF_SECONDS,
        max_seconds: float = _MAX_BACKOFF_SECONDS,
    ) -> None:
        self._current = initial_seconds
        self._max = max_seconds

    @property
    def current_seconds(self) -> float:
        return self._current

    async def wait(self, stop_event: asyncio.Event) -> None:
        """Wait for the current delay, then grow it for next time."""
        await _backoff_wait(stop_event, self._current)
        self._current = min(self._current * 2, self._max)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

async def run_book_pipeline(
    book_config: BookConfig,
    normalizer: Normalizer,
    matcher: Matcher,
    scanner: Scanner,
    health_tracker: HealthTracker,
    stop_event: asyncio.Event,
    cdp_port: int = 19222,
) -> None:
    """Run the full pipeline for a single sportsbook.

    Connects via CDP, processes the initial state, then loops over live
    payloads until *stop_event* is set.  Never raises — all exceptions
    are caught, logged, and retried with exponential backoff so that no
    single book can crash another book's task or the orchestrator.
    """
    book_id = book_config.name
    parser = import_class(book_config.parser_class)()
    backoff = _ExponentialBackoff()

    while not stop_event.is_set():
        try:
            await _run_single_session(
                book_id,
                book_config,
                parser,
                normalizer,
                matcher,
                scanner,
                health_tracker,
                stop_event,
                cdp_port,
            )
        except asyncio.CancelledError:
            raise  # Propagate cancellation cleanly
        except Exception:
            logger.exception("[%s] Unhandled error in book pipeline", book_id)
            health_tracker.mark_error(book_id, "unhandled pipeline error")

        health_tracker.mark_disconnected(book_id)
        parser.reset()

        if not stop_event.is_set():
            logger.info(
                "[%s] Reconnecting in %.1fs…", book_id, backoff.current_seconds,
            )
            await backoff.wait(stop_event)


# ------------------------------------------------------------------
# Single CDP session
# ------------------------------------------------------------------

async def _run_single_session(
    book_id: str,
    book_config: BookConfig,
    parser,
    normalizer: Normalizer,
    matcher: Matcher,
    scanner: Scanner,
    health_tracker: HealthTracker,
    stop_event: asyncio.Event,
    cdp_port: int,
) -> None:
    """Connect, initialise, and process payloads for one CDP session."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    # ---- Step 1: Find browser tab (with exponential backoff) ----
    backoff = _ExponentialBackoff()
    tab = None
    while not stop_event.is_set():
        try:
            pattern = book_config.url_pattern.replace("*", "").strip()
            tab = await asyncio.to_thread(find_tab, pattern, cdp_port)
        except Exception as exc:
            health_tracker.mark_error(book_id, f"tab discovery: {exc}")
            logger.warning("[%s] Tab discovery error: %s", book_id, exc)
            await backoff.wait(stop_event)
            continue

        if tab and tab.get("webSocketDebuggerUrl"):
            break

        logger.debug(
            "[%s] No tab found, retrying in %.1fs", book_id, backoff.current_seconds,
        )
        await backoff.wait(stop_event)

    if stop_event.is_set() or tab is None:
        return

    ws_url = tab["webSocketDebuggerUrl"]
    logger.info(
        "[%s] Found tab, connecting to CDP: %s",
        book_id,
        ws_url[:_WS_URL_LOG_CHARS],
    )

    # ---- Step 2: Create CDP client with queue-bridged callbacks ----
    def _on_http_body(url: str, body: str) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, ("http", url, body))
        except RuntimeError:
            pass  # Event loop closed during shutdown

    def _on_ws_frame(payload: str) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, ("ws", "", payload))
        except RuntimeError:
            pass

    client = CDPClient(
        ws_url=ws_url,
        url_filter=parser.relevant_http_url,
        on_http_body=_on_http_body,
        on_ws_frame=_on_ws_frame,
        ws_url_filter=parser.relevant_ws_url,
    )

    health_tracker.mark_connected(book_id)

    # ---- Step 3: Run CDP in background thread ----
    cdp_future = asyncio.ensure_future(asyncio.to_thread(client.run))

    initialized_marked = False

    try:
        # ---- Step 4 + 5 + 6 + 7 + 8: Process queue ----
        while not stop_event.is_set():
            # Check if the CDP thread died
            if cdp_future.done():
                exc = cdp_future.exception() if not cdp_future.cancelled() else None
                if exc:
                    logger.error("[%s] CDP client died: %s", book_id, exc)
                else:
                    logger.info("[%s] CDP client disconnected", book_id)
                break

            # Drain queue with timeout (allows periodic stop_event check)
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            source, url, payload = msg

            # ---- Step 5: Parse (error-isolated per payload) ----
            try:
                if source == "http":
                    updates = parser.handle_http_body(url, payload)
                    # Gate: mark initialized the first time it becomes true
                    if not initialized_marked and parser.is_initialized:
                        health_tracker.mark_initialized(book_id)
                        initialized_marked = True
                        logger.info(
                            "[%s] Parser initialised with reference data",
                            book_id,
                        )
                else:
                    # CRITICAL: drop WS frames until parser has processed
                    # the initial full-state HTTP payload.
                    if not parser.is_initialized:
                        logger.debug(
                            "[%s] Dropping WS frame — parser not yet initialised",
                            book_id,
                        )
                        continue
                    updates = parser.handle_ws_frame(payload)
            except Exception:
                logger.exception(
                    "[%s] Parser error on %s payload", book_id, source,
                )
                health_tracker.mark_error(book_id, f"parser error ({source})")
                continue

            if not updates:
                continue

            # ---- Step 6: Normalize → Match → Scan (error-isolated) ----
            try:
                normalized = normalizer.normalize_batch(updates)
                for norm_update in normalized:
                    bucket = matcher.assign(norm_update)
                    matched = MatchOutputBuilder.from_bucket(bucket)
                    scanner.process(matched)
                health_tracker.mark_update(book_id)
            except Exception:
                logger.exception("[%s] Pipeline processing error", book_id)
                health_tracker.mark_error(book_id, "pipeline processing error")
                continue

    finally:
        # ---- Step 9: Clean disconnect ----
        logger.info("[%s] Disconnecting CDP client", book_id)
        client.close()
        if not cdp_future.done():
            cdp_future.cancel()
            try:
                await cdp_future
            except (asyncio.CancelledError, Exception):
                pass