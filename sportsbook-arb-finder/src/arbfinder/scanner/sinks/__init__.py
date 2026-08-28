"""Opportunity sinks package."""

from arbfinder.scanner.sinks.base_sink import OpportunitySink
from arbfinder.scanner.sinks.console_sink import ConsoleSink
from arbfinder.scanner.sinks.storage_sink import StorageSink

__all__ = ["ConsoleSink", "OpportunitySink", "StorageSink"]
