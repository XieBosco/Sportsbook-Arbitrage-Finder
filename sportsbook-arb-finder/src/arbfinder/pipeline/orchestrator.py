"""Pipeline orchestrator — raw payload → matched selections."""

from __future__ import annotations

import json
import logging

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.output import MatchedSelection, MatchOutputBuilder
from arbfinder.normalization.normalizer import Normalizer
from arbfinder.parsers.base import BookParser

__all__ = ["handle_raw_payload"]

logger = logging.getLogger(__name__)


def handle_raw_payload(
    book_id: str,
    raw_payload: bytes,
    parser_registry: dict[str, BookParser],
    normalizer: Normalizer,
    matcher: Matcher,
    bucket_store: BucketStore,
) -> list[MatchedSelection]:
    """Run the full **parse → normalise → match → output** pipeline.

    Parameters
    ----------
    book_id:
        Identifier of the sportsbook that sent this payload.
    raw_payload:
        Raw bytes received from the book (JSON-encoded).
    parser_registry:
        Mapping of ``book_id → BookParser`` instances.
    normalizer:
        The batch :class:`Normalizer` (holds per-book normalizers).
    matcher:
        The :class:`Matcher` wrapping a :class:`BucketStore`.
    bucket_store:
        The :class:`BucketStore` (passed separately so the caller
        can inspect it after the call).

    Returns
    -------
    list[MatchedSelection]
        One :class:`MatchedSelection` per **unique bucket** touched
        by this payload (de-duplicated by bucket key).
    """
    # --- 1. Look up parser ---
    parser = parser_registry.get(book_id)
    if parser is None:
        logger.warning("No parser registered for book %r", book_id)
        return []

    # --- 2. Parse raw payload ---
    try:
        body = raw_payload.decode("utf-8")
    except UnicodeDecodeError:
        logger.error("Cannot decode payload for book %r", book_id)
        return []

    # Try HTTP body first (all parsers support it), then fall back to
    # WebSocket frame parsing if the HTTP handler returns nothing.
    updates = parser.handle_http_body("", body)
    if not updates:
        updates = parser.handle_ws_frame(body)
    if not updates:
        return []

    # --- 3. Normalise ---
    normalised = normalizer.normalize_batch(updates)
    if not normalised:
        return []

    # --- 4. Match & collect touched buckets (deduplicated) ---
    seen_keys: set = set()
    touched_buckets = []
    for update in normalised:
        bucket = matcher.assign(update)
        if bucket.key not in seen_keys:
            seen_keys.add(bucket.key)
            touched_buckets.append(bucket)

    # --- 5. Build output ---
    return [MatchOutputBuilder.from_bucket(b) for b in touched_buckets]
