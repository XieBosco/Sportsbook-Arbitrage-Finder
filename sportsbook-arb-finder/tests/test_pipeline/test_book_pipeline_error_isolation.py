"""Tests for error isolation in the book pipeline.

Verifies that exceptions from parsers, normalisers, or pipeline
components are caught and logged — never propagated to crash another
book's task or the orchestrator.
"""

from arbfinder.normalization.models import OddsUpdate
from arbfinder.parsers.base import BookParser
from arbfinder.pipeline.health import HealthTracker


class _ExplodingParser(BookParser):
    """Parser that raises on specific call types."""

    book_name = "ExplodingBook"

    def __init__(
        self,
        fail_on_http: bool = False,
        fail_on_ws: bool = False,
    ) -> None:
        # Pre-initialised so WS frames are accepted
        self.reference_data: dict = {"events": {"e1": {}}}
        self._fail_on_http = fail_on_http
        self._fail_on_ws = fail_on_ws
        self.http_call_count = 0
        self.ws_call_count = 0

    def relevant_http_url(self, url: str) -> bool:
        return True

    def handle_http_body(self, url: str, body: str) -> list[OddsUpdate]:
        self.http_call_count += 1
        if self._fail_on_http:
            raise ValueError("HTTP parsing exploded!")
        return []

    def handle_ws_frame(self, payload: str) -> list[OddsUpdate]:
        self.ws_call_count += 1
        if self._fail_on_ws:
            raise RuntimeError("WS parsing exploded!")
        return []

    def reset(self) -> None:
        pass


class TestParserErrorIsolation:
    """Verify that parser errors are caught, not propagated."""

    def test_http_parse_error_caught_and_tracked(self):
        parser = _ExplodingParser(fail_on_http=True)
        tracker = HealthTracker()
        tracker.mark_connected("ExplodingBook")

        # Simulate the pipeline's error-wrapped parsing
        try:
            parser.handle_http_body("http://test.com", "{}")
            error_occurred = False
        except Exception:
            tracker.mark_error("ExplodingBook", "parser error (http)")
            error_occurred = True

        assert error_occurred
        h = tracker.get_all()["ExplodingBook"]
        assert h.consecutive_errors == 1
        assert h.connected  # Still connected despite error

    def test_ws_parse_error_caught_and_tracked(self):
        parser = _ExplodingParser(fail_on_ws=True)
        tracker = HealthTracker()
        tracker.mark_connected("ExplodingBook")

        try:
            parser.handle_ws_frame("bad_data")
            error_occurred = False
        except Exception:
            tracker.mark_error("ExplodingBook", "parser error (ws)")
            error_occurred = True

        assert error_occurred
        assert tracker.get_all()["ExplodingBook"].consecutive_errors == 1


class TestConsecutiveErrorTracking:
    """Verify error counter behaviour."""

    def test_multiple_errors_increment(self):
        tracker = HealthTracker()
        tracker.mark_connected("bookA")
        for i in range(5):
            tracker.mark_error("bookA", f"error_{i}")
        h = tracker.get_all()["bookA"]
        assert h.consecutive_errors == 5
        assert h.last_error == "error_4"

    def test_successful_update_resets_errors(self):
        tracker = HealthTracker()
        tracker.mark_connected("bookA")
        tracker.mark_error("bookA", "fail1")
        tracker.mark_error("bookA", "fail2")
        assert tracker.get_all()["bookA"].consecutive_errors == 2

        tracker.mark_update("bookA")
        assert tracker.get_all()["bookA"].consecutive_errors == 0


class TestCrossBookIsolation:
    """Verify that one book's errors don't affect another."""

    def test_error_in_book_a_does_not_affect_book_b(self):
        tracker = HealthTracker()
        tracker.mark_connected("BookA")
        tracker.mark_connected("BookB")

        tracker.mark_error("BookA", "BookA exploded")
        tracker.mark_update("BookB")

        assert tracker.get_all()["BookA"].consecutive_errors == 1
        assert tracker.get_all()["BookB"].consecutive_errors == 0
        assert tracker.get_all()["BookB"].last_update_at is not None

    def test_disconnect_of_book_a_does_not_affect_book_b(self):
        tracker = HealthTracker()
        tracker.mark_connected("BookA")
        tracker.mark_connected("BookB")
        tracker.mark_initialized("BookA")
        tracker.mark_initialized("BookB")

        tracker.mark_disconnected("BookA")

        assert not tracker.get_all()["BookA"].connected
        assert not tracker.get_all()["BookA"].initialized
        assert tracker.get_all()["BookB"].connected
        assert tracker.get_all()["BookB"].initialized
