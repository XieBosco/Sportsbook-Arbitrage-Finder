"""CDP discovery utilities."""

__all__ = ["list_tabs", "find_tab"]

def list_tabs(port: int = 19222) -> list[dict]:
    """List all available tabs from the CDP browser."""
    pass

def find_tab(url_pattern: str, port: int = 19222) -> dict | None:
    """Find a specific tab matching the given URL pattern."""
    pass
