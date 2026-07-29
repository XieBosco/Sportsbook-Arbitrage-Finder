import json
import time
import urllib.request
import urllib.error
import websocket
import base64
import msgpack
import re
from collections import defaultdict

# Global state to store reference data
reference_data = {
    "events": {},     # eventId -> event name
    "markets": {},    # marketId -> {eventId, name}
    "selections": {}  # selectionId -> marketId
}

def decode_draftkings_payload(b64_payload):
    # Clean the string
    cleaned = re.sub(r'[^a-zA-Z0-9+/=]', '', b64_payload)
    # Add padding if necessary
    cleaned += "=" * ((4 - len(cleaned) % 4) % 4)
    
    objects = []
    try:
        raw_bytes = base64.b64decode(cleaned)
        unpacker = msgpack.Unpacker(strict_map_key=False)
        unpacker.feed(raw_bytes)
        for obj in unpacker:
            objects.append(obj)
    except Exception as e:
        # It might not be a valid DraftKings msgpack payload, which is fine
        pass
    return objects

def find_outcomes(obj):
    outcomes = []
    if isinstance(obj, list):
        # Check if this array matches the known outcome signature
        # [selectionId, selectionName, odds_array, ..., tags_array, marketId]
        # Example len is usually >= 7
        if (len(obj) >= 7 and 
            isinstance(obj[0], str) and 
            isinstance(obj[1], str) and 
            isinstance(obj[2], list) and 
            (isinstance(obj[-1], str) or obj[-1] is None) and 
            isinstance(obj[-2], list)):
            outcomes.append(obj)
        
        # Traverse recursively
        for item in obj:
            outcomes.extend(find_outcomes(item))
            
    elif isinstance(obj, dict):
        for k, v in obj.items():
            outcomes.extend(find_outcomes(v))
            
    return outcomes

def on_message(ws, message):
    data = json.loads(message)
    
    # 1. Check if this is a response to our Network.getResponseBody request
    if "id" in data and "result" in data and "body" in data.get("result", {}):
        try:
            body_str = data["result"]["body"]
            
            # The body might be base64 encoded by CDP
            if data["result"].get("base64Encoded"):
                body_str = base64.b64decode(body_str).decode('utf-8', errors='ignore')
                
            payload = json.loads(body_str)
            
            # --- PARSE REFERENCE DICTIONARY ---
            if "events" in payload and "markets" in payload and "selections" in payload:
                print("\n[✔] Successfully captured DraftKings Reference Dictionary! Organizing game data...")
                
                # Parse Events (Games)
                for ev in payload.get("events", []):
                    reference_data["events"][str(ev.get("id"))] = ev.get("name", "Unknown Event")
                
                # Parse Markets
                for m in payload.get("markets", []):
                    m_id = str(m.get("id"))
                    reference_data["markets"][m_id] = {
                        "eventId": str(m.get("eventId")),
                        "name": m.get("name", "Unknown Market")
                    }
                    
                # Parse Selections
                for s in payload.get("selections", []):
                    s_id = str(s.get("id"))
                    reference_data["selections"][s_id] = str(s.get("marketId"))
                
                print(f"[*] Parsed {len(reference_data['events'])} events, {len(reference_data['markets'])} markets, {len(reference_data['selections'])} selections.")
                return
                
        except Exception as e:
            # We silently ignore parsing errors for non-JSON or unrelated bodies
            pass

    # 2. Listen for HTTP network responses natively via CDP (to get the Reference Dictionary)
    if data.get("method") == "Network.responseReceived":
        response = data.get("params", {}).get("response", {})
        url = response.get("url", "")
        
        # Intercept the static reference dictionary
        if "/v1/markets" in url and "api/sportscontent" in url:
            request_id = data.get("params", {}).get("requestId")
            print(f"\n[*] Intercepted Reference Dictionary loading... (Request ID: {request_id})")
            
            cmd_id = hash(request_id) % 100000 
            req = {
                "id": cmd_id, 
                "method": "Network.getResponseBody",
                "params": {"requestId": request_id}
            }
            ws.send(json.dumps(req))

    # 3. Listen for WebSocket frames (to get Live Odds)
    if data.get("method") == "Network.webSocketFrameReceived":
        frame = data.get("params", {}).get("response", {})
        payloadData = frame.get("payloadData")
        
        if payloadData:
            objects = decode_draftkings_payload(payloadData)
            outcomes = find_outcomes(objects)
            
            if outcomes:
                if not reference_data["events"]:
                    print("\n[!] Intercepted odds, but reference dictionary hasn't loaded yet. Please refresh the DraftKings page.")
                    return
                
                print("\n" + "="*80)
                print("                 --- LIVE ODDS UPDATE ---")
                print("="*80)
                
                # Grouping structure: games[event_name][market_type] = list of formatted strings
                games = defaultdict(lambda: defaultdict(list))
                
                for outcome in outcomes:
                    selection_id = str(outcome[0])
                    selection_name = str(outcome[1])
                    odds_array = outcome[2]
                    
                    # Get american odds if available
                    american_odds = odds_array[0] if len(odds_array) > 0 else "N/A"
                    
                    # Lookup metadata from the reference dictionary
                    market_id = reference_data["selections"].get(selection_id, "")
                    
                    # Some updates have the market_id as the last element of the outcome array!
                    if not market_id and len(outcome) > 0 and isinstance(outcome[-1], str):
                        market_id = str(outcome[-1])

                    # Extract market_type intelligently
                    market_meta = reference_data["markets"].get(market_id, {})
                    market_type = market_meta.get("name")
                    if not market_type:
                        if selection_id.startswith("0ML"):
                            market_type = "Moneyline"
                        elif selection_id.startswith("0HC"):
                            market_type = "Spread"
                        elif selection_id.startswith("0OU"):
                            market_type = "Total"
                        else:
                            tags = outcome[-2]
                            market_type = str(tags[0]) if len(tags) > 0 else "UNKNOWN_MARKET"
                    
                    event_id = market_meta.get("eventId", "")
                    event_name = reference_data["events"].get(event_id, "Unknown Game")
                    
                    # HEURISTIC FALLBACK: If DraftKings created a new market/handicap on the fly, 
                    # the ID won't be in our static dictionary. 
                    # DraftKings IDs look like: 0OU85458301O850_1 (Prefix + CoreID + Handicap)
                    # We can extract the CoreID and find a sibling selection in our dictionary to get the game!
                    if event_name == "Unknown Game":
                        core_id_match = re.search(r'^0[A-Z]{2}(\d+)', selection_id)
                        if core_id_match:
                            core_id = core_id_match.group(1)
                            # Find any known selection with this core ID
                            for known_sel_id, known_market_id in reference_data["selections"].items():
                                if core_id in known_sel_id:
                                    fallback_meta = reference_data["markets"].get(known_market_id, {})
                                    fallback_event_id = fallback_meta.get("eventId", "")
                                    if fallback_event_id in reference_data["events"]:
                                        event_name = reference_data["events"][fallback_event_id]
                                        break
                                        
                        # If STILL unknown, try the string-matching heuristic for Spreads/Moneylines
                        if event_name == "Unknown Game":
                            for known_game in reference_data["events"].values():
                                clean_selection = selection_name.replace("Over ", "").replace("Under ", "").strip()
                                if clean_selection and clean_selection in known_game:
                                    event_name = known_game
                                    break
                    
                    # Extract handicap if available (usually at index 4 for spreads/totals)
                    handicap_str = ""
                    if market_type in ["Spread", "Total", "Run Line", "Total Runs", "Point Spread", "Total Points"]:
                        if len(outcome) > 4 and isinstance(outcome[4], (int, float)):
                            h_val = float(outcome[4])
                            if market_type in ["Spread", "Run Line", "Point Spread"] and h_val > 0:
                                handicap_str = f" (+{h_val})"
                            elif market_type in ["Spread", "Run Line", "Point Spread"]:
                                handicap_str = f" ({h_val})"
                            else:
                                handicap_str = f" ({h_val})"
                    
                    betslip_link = f"https://sportsbook.draftkings.com/?outcomes={selection_id}"
                    bet_string = f"      {selection_name}{handicap_str} | Odds: {american_odds} | Link: {betslip_link}"
                    
                    games[event_name][market_type].append(bet_string)
                
                # Print the grouped output
                for game_name, game_markets in games.items():
                    # We removed the 'Unknown Game' filter for debugging

                    print(f"\n⚾ {game_name}")
                    
                    # Print markets
                    for m_type, bets in game_markets.items():
                        print(f"  [{m_type}]")
                        for bet in bets:
                            print(bet)
                                
                print("\n" + "="*80)


def on_error(ws, error):
    print("Websocket Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("Websocket Connection Closed.")

def on_open(ws):
    print("Websocket Connected successfully! Enabling Network tracking...")
    ws.send(json.dumps({
        "id": 1,
        "method": "Network.enable"
    }))

def main():
    port = 19222 
    print(f"Looking for Chrome with remote debugging on port {port}...")
    
    page_target = None
    
    # Loop until we successfully connect to Chrome
    while True:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
            with urllib.request.urlopen(req) as response:
                targets = json.loads(response.read().decode())
                
            # Find the primary page target
            for target in targets:
                if target.get("type") == "page" and not target.get("url", "").startswith("devtools://"):
                    page_target = target
                    break
                    
            if page_target:
                break
            else:
                print("Connected to Chrome, but no active web page found. Open a tab...")
                
        except urllib.error.URLError:
            print(f"Waiting for Chrome to be launched with --remote-debugging-port={port}...")
            
        time.sleep(3)
        
    ws_url = page_target["webSocketDebuggerUrl"]
    print(f"Connecting to CDP Websocket: {ws_url}")
    
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    print("Waiting for DraftKings network traffic...")
    print("IMPORTANT: After starting this script, please REFRESH the DraftKings MLB page in your browser to load the reference dictionary.")
    ws.run_forever()

if __name__ == "__main__":
    main()
