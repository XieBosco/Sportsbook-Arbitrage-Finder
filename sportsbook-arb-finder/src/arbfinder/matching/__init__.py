"""Matching engine — cross-book bucket matching for arbitrage detection."""

from arbfinder.matching.bucket import Bucket, BucketKey, compute_time_window
from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.output import MatchedSelection, MatchOutputBuilder
from arbfinder.matching.time_resolver import TimeResolver

__all__ = [
    "Bucket",
    "BucketKey",
    "BucketStore",
    "MatchedSelection",
    "MatchOutputBuilder",
    "Matcher",
    "TimeResolver",
    "compute_time_window",
]
