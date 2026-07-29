"""Notification interfaces and implementations."""
from abc import ABC, abstractmethod

__all__ = ["Notifier", "WebhookNotifier", "TelegramNotifier"]

class Notifier(ABC):
    """Abstract base class for notifiers."""

    @abstractmethod
    def send(self, opportunity: dict) -> None:
        """Send a notification for an arbitrage opportunity."""
        pass

class WebhookNotifier(Notifier):
    """Notifier that sends a POST request to a webhook."""

    def __init__(self, webhook_url: str) -> None:
        """Initialize the webhook notifier."""
        pass

    def send(self, opportunity: dict) -> None:
        """Send the notification to the webhook."""
        pass

class TelegramNotifier(Notifier):
    """Notifier that sends a message via Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        """Initialize the Telegram notifier."""
        pass

    def send(self, opportunity: dict) -> None:
        """Send the notification via Telegram."""
        pass
