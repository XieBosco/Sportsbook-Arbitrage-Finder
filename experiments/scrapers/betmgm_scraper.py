import json
import time
import urllib.request
import urllib.error
import websocket

# Global state to store reference data
reference_data = {
    "fixtures": {}  # fixtureId -> fixture name
}

def parse_game_update(payload):
    game = payload.get("game", {})
    fixture_id = payload.get("fixtureId")
    market_id = game.get("id")
    market_name = game.get("name", {}).get("value", f"Market {market_id}")
    results = game.get("results", [])
    
    fixture_name = reference_data["fixtures"].get(str(fixture_id), f"Unknown Game (Fixture: {fixture_id})")
    
    bets = []
    for result in results:
        selection_id = result.get("id")
        selection_name = result.get("name", {}).get("value", "Unknown Selection")
        odds = result.get("americanOdds")
        
        if odds is None:
            continue
            
        attr = result.get("attr")
        handicap = ""
        if attr:
            handicap = f" ({attr})"
            
        betslip_link = f"https://www.on.betmgm.ca/en/sports?options={fixture_id}-{market_id}-{selection_id}"
        bets.append(f"      {selection_name}{handicap} | Odds: {odds} | Link: {betslip_link}")
        
    if bets:
        print(f"\n⚾ {fixture_name}")
        print(f"  [{market_name}]")
        for bet in bets:
            print(bet)
        print("="*80)

def parse_option_market_update(payload):
    option_market = payload.get("optionMarket", {})
    fixture_id = payload.get("fixtureId")
    market_id = option_market.get("id")
    market_name = option_market.get("name", {}).get("value", f"Market {market_id}")
    options = option_market.get("options", [])
    
    fixture_name = reference_data["fixtures"].get(str(fixture_id), f"Unknown Game (Fixture: {fixture_id})")
    
    bets = []
    for option in options:
        selection_id = option.get("id")
        selection_name = option.get("name", {}).get("value", "Unknown Selection")
        price = option.get("price", {})
        odds = price.get("americanOdds")
        
        if odds is None:
            continue
            
        betslip_link = f"https://www.on.betmgm.ca/en/sports?options={fixture_id}-{market_id}-{selection_id}"
        bets.append(f"      {selection_name} | Odds: {odds} | Link: {betslip_link}")
        
    if bets:
        print(f"\n⚾ {fixture_name}")
        print(f"  [{market_name}]")
        for bet in bets:
            print(bet)
        print("="*80)

def on_message(ws, message):
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
        
    # 1. Check if this is a response to our Network.getResponseBody request for the Reference Dictionary
    if "id" in data and "result" in data and "body" in data.get("result", {}):
        try:
            body_str = data["result"]["body"]
            payload = json.loads(body_str)
            
            if "fixture" in payload and "id" in payload["fixture"]:
                fixture = payload["fixture"]
                fixture_id = str(fixture["id"])
                fixture_name = fixture.get("name", {}).get("value", f"Unknown Game (Fixture: {fixture_id})")
                
                if fixture_id not in reference_data["fixtures"]:
                    reference_data["fixtures"][fixture_id] = fixture_name
                    print(f"\n[✔] Captured Reference Dictionary: Mapped {fixture_id} -> '{fixture_name}'")
        except Exception as e:
            # Not a JSON payload or parsing failed, ignore silently
            pass
            
    # 2. Check if this is an HTTP Response we need to intercept
    if data.get("method") == "Network.responseReceived":
        response = data.get("params", {}).get("response", {})
        url = response.get("url", "")
        
        # Intercept the static reference dictionary
        if "fixture-view" in url and "betmgm.ca" in url:
            request_id = data.get("params", {}).get("requestId")
            print(f"\n[*] Intercepted Reference Dictionary loading... (Request ID: {request_id})")
            
            cmd_id = hash(request_id) % 100000 
            req = {
                "id": cmd_id, 
                "method": "Network.getResponseBody",
                "params": {"requestId": request_id}
            }
            ws.send(json.dumps(req))
            
    # 3. Check if this is a WebSocket frame containing live odds
    if data.get("method") == "Network.webSocketFrameReceived":
        frame_payload = data.get("params", {}).get("response", {}).get("payloadData", "")
        
        # BetMGM uses SignalR, which delimits messages with the ASCII record separator (\x1e)
        signalr_frames = frame_payload.split('\x1e')
        for s_frame in signalr_frames:
            if not s_frame:
                continue
            
            try:
                frame_data = json.loads(s_frame)
            except json.JSONDecodeError:
                continue
                
            if not isinstance(frame_data, dict):
                continue
                
            # BetMGM SignalR/websocket payloads often look like {"type": 1, "target": "Receive", "arguments": [...]}
            args = frame_data.get("arguments", [])
            if not args:
                continue
                
            for arg in args:
                if not isinstance(arg, dict):
                    continue
                    
                message_type = arg.get("messageType")
                payload = arg.get("payload")
                
                if not message_type or not payload:
                    continue
                    
                if message_type == "GameUpdate":
                    parse_game_update(payload)
                elif message_type == "OptionMarketUpdate":
                    parse_option_market_update(payload)


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
    
    while True:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
            with urllib.request.urlopen(req) as response:
                targets = json.loads(response.read().decode())
                
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
    
    print("Waiting for BetMGM network traffic...")
    print("IMPORTANT: After starting this script, please REFRESH the BetMGM page in your browser to load the reference dictionary.")
    ws.run_forever()

if __name__ == "__main__":
    main()
