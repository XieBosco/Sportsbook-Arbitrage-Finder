import json
import time
import urllib.request
import urllib.error
import websocket
from collections import defaultdict

# Global state to store reference data
reference_data = {
    "events": {},   # eventId -> event name
    "markets": {},  # marketId -> market metadata
    "selections": {} # marketId_selectionId -> runner metadata
}

def on_message(ws, message):
    data = json.loads(message)
    
    # Check if this is a response to our Network.getResponseBody request
    if "id" in data and "result" in data and "body" in data.get("result", {}):
        try:
            body_str = data["result"]["body"]
            payload = json.loads(body_str)
            
            # --- PARSE REFERENCE DICTIONARY ---
            if "attachments" in payload and "markets" in payload["attachments"]:
                print("\n[✔] Successfully captured Reference Dictionary! Organizing game data...")
                
                # Parse Events (Games)
                events = payload["attachments"].get("events", {})
                for ev_id, ev_data in events.items():
                    reference_data["events"][str(ev_id)] = ev_data.get("name", "Unknown Event")
                
                # Parse Markets & Runners
                markets = payload["attachments"].get("markets", {})
                for m_id, m_data in markets.items():
                    reference_data["markets"][str(m_id)] = {
                        "eventId": str(m_data.get("eventId")),
                        "marketName": m_data.get("marketName", ""),
                        "marketType": m_data.get("marketType", "")
                    }
                    
                    for runner in m_data.get("runners", []):
                        s_id = str(runner.get("selectionId"))
                        r_name = runner.get("runnerName", "Unknown")
                        handicap = runner.get("handicap", 0)
                        
                        reference_data["selections"][f"{m_id}_{s_id}"] = {
                            "name": r_name,
                            "handicap": handicap
                        }
                return

            # --- PARSE LIVE ODDS UPDATE ---
            def find_markets(obj):
                markets = []
                if isinstance(obj, dict):
                    if "marketId" in obj and "runnerDetails" in obj:
                        markets.append(obj)
                    for k, v in obj.items():
                        markets.extend(find_markets(v))
                elif isinstance(obj, list):
                    for item in obj:
                        markets.extend(find_markets(item))
                return markets

            markets = find_markets(payload)
            if markets:
                if not reference_data["events"]:
                    print("\n[!] Intercepted odds, but reference dictionary hasn't loaded yet. Please refresh the FanDuel page.")
                    return
                
                print("\n" + "="*80)
                print("                 --- LIVE ODDS UPDATE ---")
                print("="*80)
                
                # Grouping structure: games[event_name][market_type] = list of formatted strings
                games = defaultdict(lambda: defaultdict(list))
                
                for market in markets:
                    m_id = str(market.get("marketId"))
                    
                    # Lookup metadata from the reference dictionary
                    market_meta = reference_data["markets"].get(m_id, {})
                    event_id = market_meta.get("eventId", "")
                    event_name = reference_data["events"].get(event_id, f"Unknown Game (Event: {event_id})")
                    market_type = market_meta.get("marketType", "UNKNOWN_MARKET")
                    
                    for runner in market.get("runnerDetails", []):
                        s_id = str(runner.get("selectionId"))
                        odds = None
                        
                        # Dig for american odds
                        win_odds = runner.get("winRunnerOdds", {})
                        if isinstance(win_odds, dict):
                            american = win_odds.get("americanDisplayOdds", {})
                            if isinstance(american, dict):
                                odds = american.get("americanOdds")
                            if odds is None:
                                true_odds = win_odds.get("trueOdds", {})
                                if isinstance(true_odds, dict):
                                    odds = true_odds.get("americanOdds")
                        
                        # Lookup Selection metadata
                        sel_meta = reference_data["selections"].get(f"{m_id}_{s_id}", {})
                        runner_name = sel_meta.get("name", f"Selection {s_id}")
                        handicap = sel_meta.get("handicap", 0)
                        
                        # Format handicap properly (e.g. +1.5 or -1.5)
                        h_str = ""
                        if handicap != 0:
                            h_str = f" ({handicap:g})" if handicap < 0 else f" (+{handicap:g})"
                            
                        betslip_link = f"https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]={m_id}&selectionId[0]={s_id}"
                        
                        bet_string = f"      {runner_name}{h_str} | Odds: {odds} | Link: {betslip_link}"
                        games[event_name][market_type].append(bet_string)
                
                # Print the grouped output
                if not games:
                    print("No recognized markets in this update.")
                
                for game_name, game_markets in games.items():
                    # Only print games that we successfully resolved names for
                    if "Unknown Game" in game_name:
                        continue
                        
                    print(f"\n⚾ {game_name}")
                    
                    # Display the core markets first in a specific order
                    core_markets = ["MONEY_LINE", "MATCH_HANDICAP_(2-WAY)", "TOTAL_POINTS_(OVER/UNDER)"]
                    for m_type in core_markets:
                        if m_type in game_markets:
                            friendly_name = m_type.replace('_', ' ').replace('(2-WAY)', '').strip()
                            print(f"  [{friendly_name}]")
                            for bet in game_markets[m_type]:
                                print(bet)
                    
                    # Print any other markets that updated
                    for m_type, bets in game_markets.items():
                        if m_type not in core_markets:
                            friendly_name = m_type.replace('_', ' ')
                            print(f"  [{friendly_name}]")
                            for bet in bets:
                                print(bet)
                                
                print("\n" + "="*80)
                
        except Exception as e:
            print("Error parsing response body:", e)

    # Listen for network responses natively via CDP
    if data.get("method") == "Network.responseReceived":
        response = data.get("params", {}).get("response", {})
        url = response.get("url", "")
        
        # Intercept both the static reference dictionary AND the live odds updates
        if "content-managed-page" in url or "getMarketPrices" in url:
            request_id = data.get("params", {}).get("requestId")
            
            if "content-managed-page" in url:
                print(f"\n[*] Intercepted Reference Dictionary loading... (Request ID: {request_id})")
            
            # Generate a numeric ID for the CDP command
            cmd_id = hash(request_id) % 100000 
            
            # Send command to get the response body for this specific request
            req = {
                "id": cmd_id, 
                "method": "Network.getResponseBody",
                "params": {"requestId": request_id}
            }
            ws.send(json.dumps(req))

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
    
    # Connect to the websocket
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    # Run forever, listening to the websocket traffic
    print("Waiting for Fanduel network traffic...")
    print("IMPORTANT: After starting this script, please REFRESH the FanDuel MLB page in your browser to load the reference dictionary.")
    ws.run_forever()

if __name__ == "__main__":
    main()
