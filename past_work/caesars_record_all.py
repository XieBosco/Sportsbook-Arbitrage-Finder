import json
import time
import urllib.request
import urllib.error
import websocket
import os
import base64

ws_urls = {}
request_urls = {}

ws_counter = 1
json_counter = 1

LOG_DIR = "c:\\Users\\fiona\\Desktop\\arbitrage_tool\\experiments\\caesars_full_logs"

def on_message(ws, message):
    global ws_counter, json_counter
    data = json.loads(message)
    
    # --- WEBSOCKET TRACKING ---
    if data.get("method") == "Network.webSocketCreated":
        req_id = data.get("params", {}).get("requestId")
        url = data.get("params", {}).get("url", "")
        ws_urls[req_id] = url
        print(f"[*] New WebSocket Created: {url}")
        
    if data.get("method") == "Network.webSocketFrameReceived":
        req_id = data.get("params", {}).get("requestId")
        frame = data.get("params", {}).get("response", {})
        payloadData = frame.get("payloadData")
        url = ws_urls.get(req_id, "")
        
        # Filter for live odds diffusion WS
        if "brands/czr/diffusion" in url and "livescores" not in url and "cashout" not in url and "microbetting" not in url:
            if payloadData:
                filename = os.path.join(LOG_DIR, f"ws_{ws_counter}.txt")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(payloadData)
                print(f"[✔] Recorded WS message {ws_counter}")
                ws_counter += 1

    # --- HTTP JSON TRACKING ---
    if data.get("method") == "Network.responseReceived":
        response = data.get("params", {}).get("response", {})
        url = response.get("url", "")
        mime = response.get("mimeType", "")
        req_id = data.get("params", {}).get("requestId")
        
        if "api.americanwagering.com" in url and "application/json" in mime:
            request_urls[req_id] = url
            
    if data.get("method") == "Network.loadingFinished":
        req_id = data.get("params", {}).get("requestId")
        if req_id in request_urls:
            cmd_id = hash(req_id) % 100000 
            req = {
                "id": cmd_id, 
                "method": "Network.getResponseBody",
                "params": {"requestId": req_id}
            }
            # We encode the req_id in the cmd_id map so we can retrieve it later, but for simplicity:
            # We'll just request the body and catch it below
            ws.send(json.dumps(req))
            # Store it globally so getResponseBody knows which URL it belongs to
            global_cmd_to_url[cmd_id] = request_urls[req_id]

    if "id" in data and "result" in data and "body" in data.get("result", {}):
        cmd_id = data["id"]
        if cmd_id in global_cmd_to_url:
            url = global_cmd_to_url[cmd_id]
            try:
                body_str = data["result"]["body"]
                if data["result"].get("base64Encoded"):
                    body_str = base64.b64decode(body_str).decode('utf-8', errors='ignore')
                    
                payload = json.loads(body_str)
                
                # Save the JSON to a file
                filename = os.path.join(LOG_DIR, f"json_{json_counter}.json")
                with open(filename, "w", encoding="utf-8") as f:
                    # Write the URL as a comment or meta field at the top for debugging
                    out_data = {
                        "_DEBUG_URL": url,
                        "data": payload
                    }
                    json.dump(out_data, f, indent=2)
                    
                print(f"[✔] Recorded JSON {json_counter} from: {url.split('?')[0]}")
                json_counter += 1
            except Exception as e:
                print(f"[!] Error parsing JSON body for {url}: {e}")

global_cmd_to_url = {}

def on_error(ws, error):
    print("\n[!] Websocket Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("\n[!] Websocket Connection Closed.")

def on_open(ws):
    print("Websocket Connected successfully! Enabling Network tracking...")
    ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
    ws.send(json.dumps({"id": 2, "method": "Network.setCacheDisabled", "params": {"cacheDisabled": True}}))

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
        except urllib.error.URLError:
            pass
        time.sleep(1)
        
    ws_url = page_target["webSocketDebuggerUrl"]
    print(f"Connecting to CDP Websocket: {ws_url}")
    
    ws = websocket.WebSocketApp(ws_url,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    print(f"Waiting for Caesars traffic...")
    print(f"Make sure to REFRESH the Caesars Sportsbook page to capture the initial JSONs!")
    ws.run_forever()

if __name__ == "__main__":
    main()
