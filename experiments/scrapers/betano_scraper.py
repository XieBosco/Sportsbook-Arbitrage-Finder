import json
import time
import urllib.request
import urllib.error
import websocket
import base64
import lz4.frame
import re
from collections import defaultdict

# Global state to store reference data
reference_data = {
    "events": {},     # eventId -> Event Object
    "markets": {},    # marketId -> Market Object
    "selections": {}  # selectionId -> Selection Object
}

def decode_betano_payload(b64_payload):
    try:
        # Step 1: Base64 decode the string into raw bytes
        compressed_bytes = base64.b64decode(b64_payload)
        
        # Step 2: Decompress the LZ4 frame
        decompressed_bytes = lz4.frame.decompress(compressed_bytes)
        
        # Step 3: Decode the bytes into a UTF-8 string and parse JSON
        json_string = decompressed_bytes.decode('utf-8')
        data = json.loads(json_string)
        return data
    except Exception as e:
        print(f"Failed to decode Betano payload: {e}")
        return None

def process_live_odds(data):
    if not reference_data["events"]:
        print("[!] Intercepted odds, but reference dictionary hasn't loaded yet. Please refresh the Betano page.")
        return

    updates_found = False
    
    # We group output by event -> market_type -> bets
    games = defaultdict(lambda: defaultdict(list))
    
    # Data is a list of events
    for item in data:
        event_id = item.get("eventId")
        if not event_id:
            continue
            
        payload = item.get("payload", {})
        
        event_meta = reference_data["events"].get(str(event_id)) or reference_data["events"].get(int(event_id), {})
        
        # If the event isn't in our dictionary, skip it
        if not event_meta:
            continue
            
        event_participants = event_meta.get("participants", [])
        if len(event_participants) == 2:
            # Betano often lists Home first, but let's check isHome flag
            team1 = event_participants[0]
            team2 = event_participants[1]
            if team1.get("isHome"):
                home_team = team1.get("name")
                away_team = team2.get("name")
            else:
                home_team = team2.get("name")
                away_team = team1.get("name")
            event_name = f"{away_team} @ {home_team}"
        else:
            event_name = f"Event {event_id}"
            
        event_url = "https://www.betano.ca" + event_meta.get("url", "")
        
        # SCENARIO 1: Static Handicap changes (just odds updates)
        selection_changes = payload.get("selectionChanges", {})
        for market_id_str, changes in selection_changes.items():
            market_id = str(market_id_str)
            market_meta = reference_data["markets"].get(market_id) or reference_data["markets"].get(int(market_id), {})
            market_type = market_meta.get("name", f"Unknown Market {market_id}")
            
            for change in changes:
                selection_id = str(change.get("id"))
                price = change.get("price")
                
                # Fetch selection details
                sel_meta = reference_data["selections"].get(selection_id) or reference_data["selections"].get(int(selection_id), {})
                selection_name = sel_meta.get("fullName", sel_meta.get("name", f"Unknown Selection {selection_id}"))
                
                # Handicap formatting
                handicap_str = ""
                if "handicap" in change:
                    h_val = float(change["handicap"])
                    if h_val > 0 and market_type in ["Spread", "Run Line", "Point Spread"]:
                        handicap_str = f" (+{h_val})"
                    else:
                        handicap_str = f" ({h_val})"
                elif "shortName" in sel_meta and sel_meta["shortName"]:
                    # Sometimes the handicap is stored in the shortName like "+1.5"
                    handicap_str = f" ({sel_meta['shortName']})"
                
                bet_string = f"      {selection_name}{handicap_str} | Odds: {price} | Link: {event_url}"
                games[event_name][market_type].append(bet_string)
                updates_found = True
                
        # SCENARIO 2: Dynamic Handicap changes (brand new market blocks)
        new_market = payload.get("market", {})
        if new_market:
            market_id = str(new_market.get("id"))
            market_type = new_market.get("name", f"Unknown Market {market_id}")
            
            # Save the new market to our reference dictionary
            reference_data["markets"][market_id] = new_market
            
            selections = new_market.get("selections", [])
            for sel in selections:
                selection_id = str(sel.get("id"))
                price = sel.get("price")
                selection_name = sel.get("fullName", sel.get("name", f"Unknown Selection {selection_id}"))
                
                # Save the new selection
                reference_data["selections"][selection_id] = sel
                
                # Handicap formatting
                handicap_str = ""
                if "handicap" in sel:
                    h_val = float(sel["handicap"])
                    if h_val > 0 and market_type in ["Spread", "Run Line", "Point Spread"]:
                        handicap_str = f" (+{h_val})"
                    else:
                        handicap_str = f" ({h_val})"
                elif "shortName" in sel and sel["shortName"]:
                    handicap_str = f" ({sel['shortName']})"
                    
                bet_string = f"      {selection_name}{handicap_str} | Odds: {price} | Link: {event_url}"
                games[event_name][market_type].append(bet_string)
                updates_found = True

    if updates_found:
        print("\n" + "="*80)
        print("                 --- LIVE ODDS UPDATE ---")
        print("="*80)
        for game_name, game_markets in games.items():
            print(f"\n🏟 {game_name}")
            for m_type, bets in game_markets.items():
                print(f"  [{m_type}]")
                for bet in bets:
                    print(bet)
        print("\n" + "="*80)

def on_message(ws, message):
    try:
        msg = json.loads(message)
        method = msg.get("method")
        
        if method == "Network.responseReceived":
            url = msg.get("params", {}).get("response", {}).get("url", "")
            # Intercept Reference Dictionary
            # url: https://www.betano.ca/danae-webapi/api/live/overview/261930000153980?isInit=false&includeVirtuals=true
            if re.match(r"^https://www\.betano\.ca/danae-webapi/api/live/overview/\d+\?isInit=false&includeVirtuals=true$", url):
                request_id = msg.get("params", {}).get("requestId")
                print(f"\n[*] Intercepted Reference Dictionary loading... (Request ID: {request_id})")
                
                # Request the actual response body
                body_payload = {
                    "id": 2,
                    "method": "Network.getResponseBody",
                    "params": {"requestId": request_id}
                }
                ws.send(json.dumps(body_payload))

        elif method == "Network.webSocketFrameReceived":
            response = msg.get("params", {}).get("response", {})
            payload_data = response.get("payloadData", "")
            
            # Identify a NewLiveOverviewDiffs JSON frame
            if "NewLiveOverviewDiffs" in payload_data:
                try:
                    # SignalR messages are delimited by the Record Separator character \x1e
                    for raw_frame in payload_data.split('\x1e'):
                        if not raw_frame.strip():
                            continue
                        
                        frame = json.loads(raw_frame)
                        args = frame.get("arguments", [])
                        if args:
                            b64_payload = args[0]
                            data = decode_betano_payload(b64_payload)
                            if data:
                                process_live_odds(data)
                except Exception as e:
                    print(f"Error processing frame: {e}")
                    import traceback
                    traceback.print_exc()
                    
        # Catch the response body of the Reference Dictionary
        elif msg.get("id") == 2:
            body = msg.get("result", {}).get("body")
            if body:
                data = json.loads(body)
                
                # Check if it has events, markets, selections
                if "events" in data and "markets" in data and "selections" in data:
                    print("\n[✔] Successfully captured Betano Reference Dictionary! Organizing data...")
                    
                    # Convert arrays to dicts if necessary, Betano provides them as dicts with string keys
                    reference_data["events"].update(data.get("events", {}))
                    reference_data["markets"].update(data.get("markets", {}))
                    reference_data["selections"].update(data.get("selections", {}))
                    
                    print(f"[*] Parsed {len(reference_data['events'])} events, {len(reference_data['markets'])} markets, {len(reference_data['selections'])} selections.")
            
    except Exception as e:
        print(f"Exception in on_message: {e}")
        import traceback
        traceback.print_exc()

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
                pages = json.loads(response.read().decode('utf-8'))
                
            # Find a normal page (not an extension or background page)
            for page in pages:
                if page.get('type') == 'page':
                    page_target = page
                    break
                    
            if page_target:
                break
            else:
                print("Found Chrome, but no active pages. Please open a tab.")
                
        except urllib.error.URLError:
            pass
            
        time.sleep(2)
        
    ws_url = page_target.get('webSocketDebuggerUrl')
    if not ws_url:
        print("Could not find WebSocket URL for the page.")
        return

    print(f"Connecting to CDP Websocket: {ws_url}")
    print("Waiting for Betano network traffic...")
    print("IMPORTANT: After starting this script, please REFRESH the Betano page in your browser to load the reference dictionary.")
    
    # Run WebSocket App
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    ws.run_forever()

if __name__ == "__main__":
    main()
