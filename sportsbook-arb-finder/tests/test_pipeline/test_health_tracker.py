"""Tests for HealthTracker with injectable fake clock."""

from datetime import datetime, timedelta, timezone

from arbfinder.pipeline.health import HealthTracker


class _FakeClock:
    """Injectable clock for deterministic health-tracker tests."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


class TestHealthTracker:
    """Verify per-book health tracking logic."""

    def _make(self):
        clock = _FakeClock(datetime(2024, 1, 1, tzinfo=timezone.utc))
        return HealthTracker(clock=clock), clock

    # ------------------------------------------------------------------
    # mark_connected
    # ------------------------------------------------------------------
    def test_mark_connected(self):
        tracker, _ = self._make()
        tracker.mark_connected("bookA")
        h = tracker.get_all()["bookA"]
        assert h.connected is True
        assert h.consecutive_errors == 0
        assert h.last_error is None

    def test_mark_connected_resets_errors(self):
        tracker, _ = self._make()
        tracker.mark_error("bookA", "fail")
        tracker.mark_error("bookA", "fail2")
        tracker.mark_connected("bookA")
        h = tracker.get_all()["bookA"]
        assert h.consecutive_errors == 0
        assert h.last_error is None

    # ------------------------------------------------------------------
    # mark_initialized
    # ------------------------------------------------------------------
    def test_mark_initialized(self):
        tracker, _ = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_initialized("bookA")
        assert tracker.get_all()["bookA"].initialized is True

    # ------------------------------------------------------------------
    # mark_update
    # ------------------------------------------------------------------
    def test_mark_update(self):
        tracker, clock = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_update("bookA")
        h = tracker.get_all()["bookA"]
        assert h.last_update_at == clock()
        assert h.consecutive_errors == 0

    def test_mark_update_resets_error_count(self):
        tracker, _ = self._make()
        tracker.mark_error("bookA", "e1")
        tracker.mark_error("bookA", "e2")
        tracker.mark_update("bookA")
        assert tracker.get_all()["bookA"].consecutive_errors == 0

    # ------------------------------------------------------------------
    # mark_error
    # ------------------------------------------------------------------
    def test_mark_error_increments(self):
        tracker, _ = self._make()
        tracker.mark_error("bookA", "fail1")
        tracker.mark_error("bookA", "fail2")
        h = tracker.get_all()["bookA"]
        assert h.consecutive_errors == 2
        assert h.last_error == "fail2"

    # ------------------------------------------------------------------
    # mark_disconnected
    # ------------------------------------------------------------------
    def test_mark_disconnected_resets_state(self):
        tracker, _ = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_initialized("bookA")
        tracker.mark_disconnected("bookA")
        h = tracker.get_all()["bookA"]
        assert h.connected is False
        assert h.initialized is False

    # ------------------------------------------------------------------
    # get_stale_books
    # ------------------------------------------------------------------
    def test_stale_after_silence(self):
        tracker, clock = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_update("bookA")
        clock.advance(120)
        stale = tracker.get_stale_books(max_silence_seconds=60)
        assert "bookA" in stale

    def test_not_stale_when_recently_updated(self):
        tracker, clock = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_update("bookA")
        clock.advance(10)
        stale = tracker.get_stale_books(max_silence_seconds=60)
        assert "bookA" not in stale

    def test_stale_ignores_disconnected(self):
        tracker, clock = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_update("bookA")
        tracker.mark_disconnected("bookA")
        clock.advance(120)
        stale = tracker.get_stale_books(max_silence_seconds=60)
        assert "bookA" not in stale

    def test_stale_connected_never_updated(self):
        tracker, _ = self._make()
        tracker.mark_connected("bookA")
        # Never received any data
        stale = tracker.get_stale_books(max_silence_seconds=60)
        assert "bookA" in stale

    def test_multiple_books_mixed(self):
        tracker, clock = self._make()
        tracker.mark_connected("bookA")
        tracker.mark_connected("bookB")
        tracker.mark_update("bookA")
        tracker.mark_update("bookB")
        clock.advance(90)
        tracker.mark_update("bookB")  # bookB is fresh
        stale = tracker.get_stale_books(max_silence_seconds=60)
        assert "bookA" in stale
        assert "bookB" not in stale
