"""CDP discovery utilities."""

import requests


__all__ = ["list_tabs", "find_tab"]


def list_tabs(port: int = 19222) -> list[dict]:
    """List all available tabs from the CDP browser."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []


def find_tab(url_pattern: str, port: int = 19222) -> dict | None:
    """Find a specific tab matching the given URL pattern."""
    pattern_lower = url_pattern.lower()
    tabs = list_tabs(port)
    for tab in tabs:
        if tab.get("type") == "page" and not tab.get("url", "").startswith(
            "devtools://"
        ):
            url = tab.get("url", "").lower()
            title = tab.get("title", "").lower()
            if pattern_lower in url or pattern_lower in title:
                return tab

    return None
