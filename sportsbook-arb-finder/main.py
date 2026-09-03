"""Entry point for the Sportsbook Arbitrage Finder.

Minimal — all testable logic lives in :mod:`arbfinder.pipeline.orchestrator`.
"""

import asyncio
import sys
from pathlib import Path

from arbfinder.pipeline.config import load_config
from arbfinder.pipeline.orchestrator import run


def main() -> None:
    """Load configuration and run the pipeline."""
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    try:
        config = load_config(path=config_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Configuration validation failed:\n{exc}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass  # Clean exit on Ctrl+C


if __name__ == "__main__":
    main()
