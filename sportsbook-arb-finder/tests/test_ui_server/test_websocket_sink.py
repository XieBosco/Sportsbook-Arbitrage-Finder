"""Tests for WebSocketSink — emit serialises and schedules broadcast."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from arbfinder.scanner.schema import Leg, Opportunity
from arbfinder.scanner.sinks.websocket_sink import WebSocketSink
from arbfinder.pipeline.config import SinksConfig


class FakeConnectionManager:
    """Records broadcast calls for assertion."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.broadcast = AsyncMock(side_effect=self._record)

    async def _record(self, message: dict) -> None:
        self.calls.append(message)


def _make_opportunity() -> Opportunity:
    return Opportunity(
        opportunity_id="opp-1",
        canonical_game_id="game-1",
        sport_key="baseball_mlb",
        league_key="MLB",
        home_team="Phillies",
        away_team="Angels",
        market_type="moneyline",
        line=None,
        margin=0.025,
        legs=[
            Leg(
                book_id="DraftKings",
                selection="home",
                odds_decimal=2.10,
                stake=50.0,
                captured_at=datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc),
            ),
        ],
        detected_at=datetime(2026, 8, 30, 12, 0, 5, tzinfo=timezone.utc),
        expires_hint_seconds=5.0,
    )


@pytest.mark.asyncio
async def test_emit_broadcasts_correct_shape():
    fake_mgr = FakeConnectionManager()
    config = SinksConfig()
    sink = WebSocketSink(fake_mgr, sinks_config=config)

    opp = _make_opportunity()
    sink.emit(opp)

    # emit() creates a task — we need to let the loop run it
    await asyncio.sleep(0)

    assert len(fake_mgr.calls) == 1
    msg = fake_mgr.calls[0]
    assert msg["type"] == "opportunity"
    assert "data" in msg

    data = msg["data"]
    assert data["opportunity_id"] == "opp-1"
    assert data["canonical_game_id"] == "game-1"
    assert data["margin"] == 0.025
    assert data["margin_pct"] == 2.5
    assert isinstance(data["legs"], list)
    assert len(data["legs"]) == 1
