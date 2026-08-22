"""Team name normalization and aliasing."""

import json
import os
import re

__all__ = ["normalize_team_name", "load_alias_table"]

# Global cache for the alias table
_ALIAS_TABLE: dict[str, str] = {}


def normalize_team_name(raw_name: str, sport: str = "") -> str:
    """Normalize a team name to its canonical form."""
    clean_name = re.sub(r"\s+", " ", raw_name.lower().strip())

    if clean_name in _ALIAS_TABLE:
        return _ALIAS_TABLE[clean_name]

    return raw_name.title()


def load_alias_table(path: str) -> dict[str, str]:
    """Load the team alias mapping from a file."""
    global _ALIAS_TABLE
    if not os.path.exists(path):
        return _ALIAS_TABLE

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            for canonical, aliases in data.items():
                if isinstance(aliases, list):
                    for alias in aliases:
                        _ALIAS_TABLE[alias.lower().strip()] = canonical
                elif isinstance(aliases, str):
                    _ALIAS_TABLE[aliases.lower().strip()] = canonical
    except json.JSONDecodeError:
        pass

    return _ALIAS_TABLE
