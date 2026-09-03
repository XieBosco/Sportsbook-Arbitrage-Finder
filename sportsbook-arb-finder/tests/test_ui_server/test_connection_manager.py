"""Tests for ConnectionManager — broadcast, prune, connect/disconnect lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from arbfinder.ui_server.connection_manager import ConnectionManager


# ------------------------------------------------------------------
# Helpers — lightweight WebSocket stub
# ------------------------------------------------------------------

def _make_ws(*, fail_send: bool = False) -> MagicMock:
    """Return a mock WebSocket that optionally raises on ``send_json``."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    if fail_send:
        ws.send_json = AsyncMock(side_effect=RuntimeError("connection lost"))
    else:
        ws.send_json = AsyncMock()
    return ws


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_connect_registers_client():
    mgr = ConnectionManager()
    ws = _make_ws()

    await mgr.connect(ws)

    assert mgr.active_count == 1
    ws.accept.assert_awaited_once()


@pytest.mark.asyncio
async def test_disconnect_removes_client():
    mgr = ConnectionManager()
    ws = _make_ws()
    await mgr.connect(ws)

    await mgr.disconnect(ws)

    assert mgr.active_count == 0


@pytest.mark.asyncio
async def test_disconnect_absent_is_noop():
    mgr = ConnectionManager()
    ws = _make_ws()

    # Should not raise
    await mgr.disconnect(ws)
    assert mgr.active_count == 0


@pytest.mark.asyncio
async def test_broadcast_delivers_to_all():
    mgr = ConnectionManager()
    ws1 = _make_ws()
    ws2 = _make_ws()
    await mgr.connect(ws1)
    await mgr.connect(ws2)

    msg = {"type": "opportunity", "data": {"margin": 0.03}}
    await mgr.broadcast(msg)

    ws1.send_json.assert_awaited_once_with(msg)
    ws2.send_json.assert_awaited_once_with(msg)


@pytest.mark.asyncio
async def test_broadcast_prunes_dead_client_without_affecting_others():
    mgr = ConnectionManager()
    healthy = _make_ws()
    dead = _make_ws(fail_send=True)
    await mgr.connect(healthy)
    await mgr.connect(dead)
    assert mgr.active_count == 2

    msg = {"type": "test", "data": {}}
    await mgr.broadcast(msg)

    # Healthy client received the message
    healthy.send_json.assert_awaited_once_with(msg)

    # Dead client was pruned
    assert mgr.active_count == 1


@pytest.mark.asyncio
async def test_broadcast_empty_is_noop():
    mgr = ConnectionManager()
    # No clients — should not raise
    await mgr.broadcast({"type": "test"})
