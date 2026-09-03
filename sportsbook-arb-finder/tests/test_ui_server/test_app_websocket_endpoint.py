"""Tests for the FastAPI app — health endpoint and WebSocket connectivity."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from arbfinder.ui_server.app import create_app
from arbfinder.ui_server.connection_manager import ConnectionManager
from arbfinder.pipeline.config import AppConfig


@pytest.fixture()
def client():
    mgr = ConnectionManager()
    config = AppConfig(books=[])
    app = create_app(mgr, config)
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["connected_clients"] == 0


def test_index_serves_html(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Arbitrage Finder" in resp.text


def test_static_css_served(client: TestClient):
    resp = client.get("/static/style.css")
    assert resp.status_code == 200
    assert "text/css" in resp.headers["content-type"]


def test_websocket_connect(client: TestClient):
    with client.websocket_connect("/ws/opportunities") as ws:
        # Connection succeeded — verify health shows 1 client
        resp = client.get("/health")
        assert resp.json()["connected_clients"] == 1
