"""Batch normalizer — dispatches to per-book normalizers."""

from __future__ import annotations

import logging

from arbfinder.normalization.base_normalizer import BaseNormalizer
from arbfinder.normalization.models import OddsUpdate, NormalizedOddsUpdate
from arbfinder.normalization.unresolved_log import (
    record_failed_normalization,
    record_unknown_book,
)

__all__ = ["Normalizer"]

logger = logging.getLogger(__name__)


class Normalizer:
    """Dispatches raw ``OddsUpdate`` objects to the correct per-book
    normalizer and collects the results.

    Books whose ``book_id`` has no registered normalizer, or whose
    normalizer returns ``None``, are logged and silently skipped.
    """

    def __init__(self, normalizers: dict[str, BaseNormalizer]) -> None:
        self._normalizers = normalizers

    def normalize_batch(
        self, updates: list[OddsUpdate]
    ) -> list[NormalizedOddsUpdate]:
        """Normalize a batch of raw updates.

        Returns only the successfully normalized updates.  Failures are
        recorded via :mod:`~arbfinder.normalization.unresolved_log` and
        skipped.
        """
        results: list[NormalizedOddsUpdate] = []
        for update in updates:
            normalizer = self._normalizers.get(update.book_id)
            if normalizer is None:
                record_unknown_book(update)
                continue

            normalized = normalizer.normalize(update)
            if normalized is None:
                record_failed_normalization(update)
                continue

            results.append(normalized)
        return results
