"""Manager for CDP sessions."""
from typing import Callable

__all__ = ["SessionManager"]

class SessionManager:
    """Manages multiple CDP client sessions for different sportsbooks."""

    def __init__(self, books_config: list[dict], on_event: Callable[[str, dict], None]) -> None:
        """Initialize the session manager with sportsbook configurations."""
        pass

    def start(self) -> None:
        """Start managing CDP sessions."""
        pass

    def stop(self) -> None:
        """Stop managing CDP sessions."""
        pass

    def _reattach_loop(self) -> None:
        """Background loop to reconnect or poll for tabs."""
        pass
