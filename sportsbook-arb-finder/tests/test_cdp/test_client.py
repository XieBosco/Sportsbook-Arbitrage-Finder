import json
import time
import base64
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from unittest.mock import MagicMock
from arbfinder.cdp.client import CDPClient
from arbfinder.cdp.session_manager import SessionManager
from arbfinder.parsers.base import BookParser

def test_cdp_client_ws_filtering():
    """Test WS frame filtering logic via synthetic JSON."""
    
    received_frames = []
    def on_ws_frame(frame: str):
        received_frames.append(frame)
        
    def ws_url_filter(url: str) -> bool:
        return "allowed" in url

    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: False,
        on_http_body=lambda u, b: None,
        on_ws_frame=on_ws_frame,
        ws_url_filter=ws_url_filter
    )
    
    # Simulate websocket created (allowed)
    client._on_message(None, json.dumps({
        "method": "Network.webSocketCreated",
        "params": {
            "requestId": "req1",
            "url": "wss://example.com/allowed"
        }
    }))
    
    # Simulate websocket created (blocked)
    client._on_message(None, json.dumps({
        "method": "Network.webSocketCreated",
        "params": {
            "requestId": "req2",
            "url": "wss://example.com/blocked"
        }
    }))
    
    # Simulate frame on allowed socket
    client._on_message(None, json.dumps({
        "method": "Network.webSocketFrameReceived",
        "params": {
            "requestId": "req1",
            "response": {"payloadData": "frame1"}
        }
    }))
    
    # Simulate frame on blocked socket
    client._on_message(None, json.dumps({
        "method": "Network.webSocketFrameReceived",
        "params": {
            "requestId": "req2",
            "response": {"payloadData": "frame2"}
        }
    }))
    
    assert len(received_frames) == 1
    assert received_frames[0] == "frame1"
    
    # Simulate closing socket
    client._on_message(None, json.dumps({
        "method": "Network.webSocketClosed",
        "params": {
            "requestId": "req1"
        }
    }))
    assert "req1" not in client.active_websockets


def test_cdp_client_untracked_socket_warning():
    """Test that untracked sockets drop frames and track warned requestIds."""
    received_frames = []
    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: False,
        on_http_body=lambda u, b: None,
        on_ws_frame=lambda f: received_frames.append(f)
    )
    
    # Frame arrives for an unobserved websocket
    client._on_message(None, json.dumps({
        "method": "Network.webSocketFrameReceived",
        "params": {
            "requestId": "untracked_123",
            "response": {"payloadData": "missed_frame"}
        }
    }))
    
    assert len(received_frames) == 0
    assert "untracked_123" in client._untracked_warned_sockets


def test_cdp_client_pending_requests_eviction():
    """Test pending_requests time-gated eviction logic."""
    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: False,
        on_http_body=lambda u, b: None,
        on_ws_frame=lambda f: None
    )
    
    old_time = time.time() - 35
    client.pending_requests[1] = ("old_url", old_time)
    client.pending_requests[2] = ("recent_url", time.time())
    
    # Force _last_sweep to be in the past (> 10s ago)
    client._last_sweep = time.time() - 15
    
    # Send a dummy message to trigger the loop
    client._on_message(None, json.dumps({"method": "Dummy"}))
    
    assert 1 not in client.pending_requests
    assert 2 in client.pending_requests


def test_cdp_client_http_response_handling_plain_text():
    """Test Network.responseReceived -> Network.getResponseBody -> on_http_body flow with plain text."""
    received_bodies = []
    def on_http_body(url: str, body: str):
        received_bodies.append((url, body))

    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: "target_api" in u,
        on_http_body=on_http_body,
        on_ws_frame=lambda f: None
    )
    mock_ws = MagicMock()
    client.ws = mock_ws

    # 1. Simulate responseReceived for matching URL
    client._on_message(None, json.dumps({
        "method": "Network.responseReceived",
        "params": {
            "requestId": "http_req_1",
            "response": {
                "url": "https://sportsbook.com/api/target_api/events"
            }
        }
    }))

    # Verify CDPClient sent Network.getResponseBody
    assert mock_ws.send.called
    sent_payload = json.loads(mock_ws.send.call_args[0][0])
    assert sent_payload["method"] == "Network.getResponseBody"
    assert sent_payload["params"] == {"requestId": "http_req_1"}
    cmd_id = sent_payload["id"]

    assert cmd_id in client.pending_requests
    assert client.pending_requests[cmd_id][0] == "https://sportsbook.com/api/target_api/events"

    # 2. Simulate getResponseBody result with plain text JSON
    sample_json = json.dumps({"events": [{"id": 101, "name": "Team A vs Team B"}]})
    client._on_message(None, json.dumps({
        "id": cmd_id,
        "result": {
            "body": sample_json,
            "base64Encoded": False
        }
    }))

    # Verify on_http_body received the plain text body
    assert len(received_bodies) == 1
    assert received_bodies[0][0] == "https://sportsbook.com/api/target_api/events"
    assert received_bodies[0][1] == sample_json

    # Verify cmd_id was removed from pending_requests
    assert cmd_id not in client.pending_requests


def test_cdp_client_http_response_handling_base64():
    """Test getResponseBody result decoding base64-encoded HTTP bodies."""
    received_bodies = []
    def on_http_body(url: str, body: str):
        received_bodies.append((url, body))

    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: True,
        on_http_body=on_http_body,
        on_ws_frame=lambda f: None
    )
    mock_ws = MagicMock()
    client.ws = mock_ws

    # 1. Trigger responseReceived
    client._on_message(None, json.dumps({
        "method": "Network.responseReceived",
        "params": {
            "requestId": "http_b64_1",
            "response": {
                "url": "https://sportsbook.com/compressed_payload"
            }
        }
    }))
    cmd_id = client.cmd_id

    # 2. Base64-encoded UTF-8 string
    original_text = '{"status": "ok", "data": "binary-like payload"}'
    b64_str = base64.b64encode(original_text.encode('utf-8')).decode('utf-8')

    client._on_message(None, json.dumps({
        "id": cmd_id,
        "result": {
            "body": b64_str,
            "base64Encoded": True
        }
    }))

    assert len(received_bodies) == 1
    assert received_bodies[0][0] == "https://sportsbook.com/compressed_payload"
    assert received_bodies[0][1] == original_text


def test_cdp_client_http_response_ignored_when_filtered():
    """Test that URLs failing url_filter do not trigger getResponseBody."""
    client = CDPClient(
        ws_url="ws://mock",
        url_filter=lambda u: "keep" in u,
        on_http_body=lambda u, b: None,
        on_ws_frame=lambda f: None
    )
    mock_ws = MagicMock()
    client.ws = mock_ws

    client._on_message(None, json.dumps({
        "method": "Network.responseReceived",
        "params": {
            "requestId": "ignore_me",
            "response": {
                "url": "https://sportsbook.com/static/analytics.js"
            }
        }
    }))

    assert not mock_ws.send.called
    assert len(client.pending_requests) == 0


def test_session_manager_threads_ws_filter():
    """Test SessionManager threading the relevant_ws_url callback."""
    class MockParser(BookParser):
        book_name = "Mock"
        def relevant_http_url(self, url: str) -> bool: return True
        def relevant_ws_url(self, url: str) -> bool: return "mock" in url
        def handle_http_body(self, url: str, body: str) -> list: return []
        def handle_ws_frame(self, payload: str) -> list: return []

    manager = SessionManager([MockParser()], lambda updates: None)
    
    # Mock find_tab to return immediately
    import arbfinder.cdp.session_manager as sm
    sm.find_tab = MagicMock(return_value={"webSocketDebuggerUrl": "ws://mock"})
    
    # We want to capture the CDPClient creation
    original_cdpclient = sm.CDPClient

    captured_kwargs = {}
    def mock_cdp_client(*args, **kwargs):
        captured_kwargs.update(kwargs)
        # return a mock that doesn't block on run()
        mock_instance = MagicMock()
        mock_instance.run = MagicMock()
        return mock_instance

    sm.CDPClient = mock_cdp_client

    try:
        manager.start()
        # Wait briefly for thread to spawn and hit the mocked client
        time.sleep(0.1)
        manager.stop()

        assert "ws_url_filter" in captured_kwargs
        filter_fn = captured_kwargs["ws_url_filter"]
        assert filter_fn("wss://mock") is True
        assert filter_fn("wss://other") is False
    finally:
        sm.CDPClient = original_cdpclient
