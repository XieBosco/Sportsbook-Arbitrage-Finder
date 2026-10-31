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


def test_static_team_logos_json_served(client: TestClient):
    resp = client.get("/static/team_logos.json")
    assert resp.status_code == 200
    assert "application/json" in resp.headers["content-type"]
    data = resp.json()
    assert "mlb" in data
    assert "nhl" in data
    assert "boston bruins" in data["nhl"]
    assert "vegas golden knights" in data["nhl"]
    assert "new york yankees" in data["mlb"]


def test_static_team_logos_js_served(client: TestClient):
    resp = client.get("/static/team_logos.js")
    assert resp.status_code == 200
    assert "MLB_TEAM_LOGOS" in resp.text
    assert "NHL_TEAM_LOGOS" in resp.text
    assert "TEAM_LOGOS" in resp.text


def test_static_nhl_and_mlb_logo_images_served(client: TestClient):
    # Test NHL logo
    nhl_resp = client.get("/static/nhl_team_logos/boston_bruins.png")
    assert nhl_resp.status_code == 200
    assert "image/png" in nhl_resp.headers["content-type"]

    # Test MLB logo
    mlb_resp = client.get("/static/mlb_team_logos/new_york_yankees.png")
    assert mlb_resp.status_code == 200
    assert "image/png" in mlb_resp.headers["content-type"]

