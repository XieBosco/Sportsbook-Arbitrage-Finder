"""Main entry point for the arbitrage finder."""
from typing import Callable
from arbfinder.parsers.base import BookParser
from arbfinder.engine.store import OddsStore

__all__ = ["build_parser_registry", "make_dispatcher", "main"]

def build_parser_registry() -> dict[str, type[BookParser]]:
    """Build and return a registry of available sportsbook parsers."""
    pass

def make_dispatcher(parser: BookParser, store: OddsStore) -> Callable[[dict], None]:
    """Create a dispatcher function for a given parser and store."""
    pass

def main() -> None:
    """Run the main application."""
    pass
