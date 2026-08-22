import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))
from unittest.mock import patch, MagicMock
import requests
from arbfinder.cdp.discovery import list_tabs, find_tab

def test_list_tabs_success():
    """Test list_tabs returns json list when requests succeeds."""
    mock_tabs = [
        {"id": "tab1", "type": "page", "title": "DraftKings", "url": "https://sportsbook.draftkings.com"},
        {"id": "tab2", "type": "page", "title": "Caesars", "url": "https://caesars.com/sportsbook"}
    ]
    with patch("arbfinder.cdp.discovery.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_tabs
        mock_get.return_value = mock_resp
        
        result = list_tabs(port=19222)
        assert result == mock_tabs
        mock_get.assert_called_once_with("http://127.0.0.1:19222/json", timeout=5)


def test_list_tabs_network_failure():
    """Test list_tabs returns empty list when network request fails."""
    with patch("arbfinder.cdp.discovery.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Connection refused")
        
        result = list_tabs(port=19222)
        assert result == []


def test_find_tab_by_url():
    """Test find_tab matching by URL pattern (case-insensitive)."""
    mock_tabs = [
        {"id": "tab1", "type": "page", "title": "Home Page", "url": "https://sportsbook.draftkings.com/leagues/basketball"},
        {"id": "tab2", "type": "page", "title": "Other", "url": "https://example.com"}
    ]
    with patch("arbfinder.cdp.discovery.list_tabs", return_value=mock_tabs):
        tab = find_tab("draftkings")
        assert tab is not None
        assert tab["id"] == "tab1"


def test_find_tab_by_title():
    """Test find_tab matching by title when URL does not contain pattern."""
    mock_tabs = [
        {"id": "tab1", "type": "page", "title": "Caesars Sportsbook - Live Odds", "url": "https://williamhill.us/app"},
    ]
    with patch("arbfinder.cdp.discovery.list_tabs", return_value=mock_tabs):
        tab = find_tab("caesars")
        assert tab is not None
        assert tab["id"] == "tab1"


def test_find_tab_ignores_devtools_and_non_page():
    """Test find_tab ignores devtools URLs and non-page types."""
    mock_tabs = [
        {"id": "tab1", "type": "background_page", "title": "DraftKings Extension", "url": "https://draftkings.com/ext"},
        {"id": "tab2", "type": "page", "title": "DevTools DraftKings", "url": "devtools://devtools/bundled/inspector.html?ws=127.0.0.1"},
        {"id": "tab3", "type": "page", "title": "DraftKings Real Page", "url": "https://sportsbook.draftkings.com"}
    ]
    with patch("arbfinder.cdp.discovery.list_tabs", return_value=mock_tabs):
        tab = find_tab("draftkings")
        assert tab is not None
        assert tab["id"] == "tab3"


def test_find_tab_not_found():
    """Test find_tab returns None when no matching tab exists."""
    mock_tabs = [
        {"id": "tab1", "type": "page", "title": "Google", "url": "https://google.com"}
    ]
    with patch("arbfinder.cdp.discovery.list_tabs", return_value=mock_tabs):
        tab = find_tab("fanduel")
        assert tab is None
