"""Scanner package — arbitrage detection from matched selections."""

from arbfinder.scanner.dedup_tracker import DedupTracker
from arbfinder.scanner.market_grouper import MarketGrouper, MarketGroupKey
from arbfinder.scanner.scanner import Scanner
from arbfinder.scanner.schema import Leg, Opportunity
from arbfinder.scanner.sinks import ConsoleSink, OpportunitySink, StorageSink
from arbfinder.scanner.staleness_filter import StalenessFilter
from arbfinder.scanner.threshold_config import ScannerThresholds, load_scanner_thresholds

__all__ = [
    "ConsoleSink",
    "DedupTracker",
    "Leg",
    "MarketGroupKey",
    "MarketGrouper",
    "Opportunity",
    "OpportunitySink",
    "Scanner",
    "ScannerThresholds",
    "StalenessFilter",
    "StorageSink",
    "load_scanner_thresholds",
]
