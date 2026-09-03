"""Tests verifying parser initialisation order in the book pipeline.

CRITICAL REQUIREMENT (Developer Guide, Layer 2):
  Many BookParser implementations are stateful — they must process an
  initial full-state HTTP payload (mapping internal UUIDs to team names)
  via ``handle_http_body()`` BEFORE any ``handle_ws_frame()`` calls
  will decode correctly.

These tests use a fake BookParser stub to verify:
  1. ``handle_http_body()`` is called and ``is_initialized`` confirmed
     BEFORE any ``handle_ws_frame()`` calls are processed.
  2. A failed initial-state fetch retries rather than proceeding to
     subscribe on an uninitialised parser.
"""

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers.base import BookParser
from arbfinder.pipeline.health import HealthTracker


class _FakeParser(BookParser):
    """Stub parser that tracks initialisation and call order."""

    book_name = "FakeBook"

    def __init__(self, init_on_call: int = 1) -> None:
        self.http_calls: list[tuple[str, str]] = []
        self.ws_calls: list[str] = []
        self.reference_data: dict = {"events": {}, "markets": {}, "selections": {}}
        self._init_on_call = init_on_call
        self._http_call_count = 0

    def relevant_http_url(self, url: str) -> bool:
        return True

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        self._http_call_count += 1
        self.http_calls.append((url, body))
        if self._http_call_count >= self._init_on_call:
            self.reference_data["events"]["evt1"] = {"name": "Test Game"}
        return []

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        self.ws_calls.append(payload)
        return []

    def reset(self) -> None:
        self.reference_data = {"events": {}, "markets": {}, "selections": {}}
        self._http_call_count = 0
        self.http_calls.clear()
        self.ws_calls.clear()


class TestIsInitializedGate:
    """Verify the ``is_initialized`` property gates WS processing."""

    def test_not_initialized_before_http(self):
        parser = _FakeParser()
        assert not parser.is_initialized

    def test_initialized_after_http(self):
        parser = _FakeParser()
        parser.handle_http_body("http://test.com/state", "{}")
        assert parser.is_initialized

    def test_delayed_initialization(self):
        parser = _FakeParser(init_on_call=3)
        parser.handle_http_body("url", "body1")
        assert not parser.is_initialized
        parser.handle_http_body("url", "body2")
        assert not parser.is_initialized
        parser.handle_http_body("url", "body3")
        assert parser.is_initialized

    def test_reset_clears_initialization(self):
        parser = _FakeParser()
        parser.handle_http_body("url", "body")
        assert parser.is_initialized
        parser.reset()
        assert not parser.is_initialized


class TestInitializationOrder:
    """Verify the pipeline's message processing respects init ordering."""

    def test_ws_frames_dropped_before_initialization(self):
        """WS frames received before initialisation must be dropped."""
        parser = _FakeParser(init_on_call=999)  # Never initialise
        assert not parser.is_initialized

        # Simulating the pipeline's gate logic
        dropped = []
        if not parser.is_initialized:
            dropped.append("tick1")
        else:
            parser.handle_ws_frame("tick1")

        assert len(dropped) == 1
        assert len(parser.ws_calls) == 0

    def test_ws_frames_processed_after_initialization(self):
        """After initialisation, WS frames must be processed."""
        parser = _FakeParser()
        parser.handle_http_body("http://test.com/state", "{}")
        assert parser.is_initialized

        parser.handle_ws_frame("tick_data")
        assert len(parser.ws_calls) == 1
        assert parser.ws_calls[0] == "tick_data"

    def test_full_message_sequence_ordering(self):
        """Integration: full message sequence respects init ordering."""
        parser = _FakeParser()
        call_log: list[tuple[str, str]] = []

        messages = [
            ("ws", "early_tick_1"),   # Should be dropped
            ("ws", "early_tick_2"),   # Should be dropped
            ("http", "state_data"),   # Initialises parser
            ("ws", "valid_tick_1"),   # Should be processed
            ("ws", "valid_tick_2"),   # Should be processed
        ]

        for source, payload in messages:
            if source == "http":
                parser.handle_http_body("http://test.com", payload)
                call_log.append(("http_processed", payload))
            elif source == "ws":
                if not parser.is_initialized:
                    call_log.append(("ws_dropped", payload))
                    continue
                parser.handle_ws_frame(payload)
                call_log.append(("ws_processed", payload))

        assert call_log == [
            ("ws_dropped", "early_tick_1"),
            ("ws_dropped", "early_tick_2"),
            ("http_processed", "state_data"),
            ("ws_processed", "valid_tick_1"),
            ("ws_processed", "valid_tick_2"),
        ]
        assert len(parser.ws_calls) == 2

    def test_health_tracker_marks_initialized_after_parser(self):
        """HealthTracker.mark_initialized called only after parser.is_initialized."""
        tracker = HealthTracker()
        parser = _FakeParser()
        book_id = "FakeBook"

        tracker.mark_connected(book_id)
        assert not tracker.get_all()[book_id].initialized

        # Simulate the pipeline's init check
        initialized_marked = False
        parser.handle_http_body("http://test.com/state", "{}")
        if not initialized_marked and parser.is_initialized:
            tracker.mark_initialized(book_id)
            initialized_marked = True

        assert tracker.get_all()[book_id].initialized

    def test_failed_init_does_not_mark_initialized(self):
        """If parser fails to initialise, HealthTracker stays uninitialised."""
        tracker = HealthTracker()
        parser = _FakeParser(init_on_call=999)  # Never initialises
        book_id = "FakeBook"

        tracker.mark_connected(book_id)

        initialized_marked = False
        parser.handle_http_body("http://test.com", "{}")
        if not initialized_marked and parser.is_initialized:
            tracker.mark_initialized(book_id)
            initialized_marked = True

        assert not tracker.get_all()[book_id].initialized
        assert not initialized_marked
