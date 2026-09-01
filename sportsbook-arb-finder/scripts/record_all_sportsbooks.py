import json
import time
import urllib.request
import urllib.error
import websocket
import os
import base64
import threading

file_lock = threading.RLock()

# Keep counters per sportsbook
counters = {
    "betano": {"ws": 1, "json": 1},
    "betmgm": {"ws": 1, "json": 1},
    "caesars": {"ws": 1, "json": 1},
    "draftkings": {"ws": 1, "json": 1},
    "fanduel": {"ws": 1, "json": 1}
}

# Base dir should be 'data' in the scripts folder
BASE_DIR = os.path.join(os.path.dirname(__file__), "data2")

def log_to_timeline(sb, file_type, file_name):
    with file_lock:
        timeline_path = os.path.join(BASE_DIR, "timeline.jsonl")
        entry = {
            "timestamp": time.time(),
            "sportsbook": sb,
            "file_type": file_type,
            "file_name": file_name
        }
        with open(timeline_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

def get_log_dir(sportsbook):
    msg_dir_name = "messages" if sportsbook == "caesars" else f"{sportsbook}_messages"
    d = os.path.join(BASE_DIR, sportsbook, msg_dir_name)
    if not os.path.exists(d):
        os.makedirs(d)
    return d

def save_ws(sb, payloadData):
    with file_lock:
        c = counters[sb]["ws"]
        filename = f"ws_{c}.txt"
        filepath = os.path.join(get_log_dir(sb), filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(payloadData)
        log_to_timeline(sb, "ws", filename)
        print(f"[✔] [{sb.upper()}] Recorded WS message {c}")
        counters[sb]["ws"] += 1

def save_json(sb, out_data, url, is_ws=False):
    with file_lock:
        if is_ws:
            c = counters[sb]["ws"]
            filename = f"ws_{c}.txt"
            filepath = os.path.join(get_log_dir(sb), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)
            log_to_timeline(sb, "ws", filename)
            print(f"[✔] [{sb.upper()}] Recorded live odds update {c} to ws_{c}.txt")
            counters[sb]["ws"] += 1
        else:
            c = counters[sb]["json"]
            filename = f"json_{c}.json"
            filepath = os.path.join(get_log_dir(sb), filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(out_data, f, indent=2)
            log_to_timeline(sb, "json", filename)
            print(f"[✔] [{sb.upper()}] Recorded JSON {c} from {url.split('?')[0]}")
            counters[sb]["json"] += 1

def on_message(ws, message):
    if not hasattr(ws, 'ws_urls'):
        ws.ws_urls = {}
    if not hasattr(ws, 'request_urls'):
        ws.request_urls = {}
    if not hasattr(ws, 'global_cmd_to_url'):
        ws.global_cmd_to_url = {}

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return
    
    # --- WEBSOCKET TRACKING ---
    if data.get("method") == "Network.webSocketCreated":
        req_id = data.get("params", {}).get("requestId")
        url = data.get("params", {}).get("url", "")
        ws.ws_urls[req_id] = url
        
    if data.get("method") == "Network.webSocketFrameReceived":
        req_id = data.get("params", {}).get("requestId")
        frame = data.get("params", {}).get("response", {})
        payloadData = frame.get("payloadData")
        url = ws.ws_urls.get(req_id, "")
        
        if payloadData:
            if "betano.ca/contenthub" in url:
                save_ws("betano", payloadData)
            elif "cds-push" in url and "betmgm.ca" in url:
                save_ws("betmgm", payloadData)
            elif "brands/czr/diffusion" in url and "livescores" not in url and "cashout" not in url and "microbetting" not in url:
                save_ws("caesars", payloadData)
            elif "sportsbook-ws" in url and "draftkings.com" in url:
                save_ws("draftkings", payloadData)

    # --- HTTP JSON TRACKING ---
    if data.get("method") == "Network.responseReceived":
        response = data.get("params", {}).get("response", {})
        url = response.get("url", "")
        mime = response.get("mimeType", "")
        req_id = data.get("params", {}).get("requestId")
        
        if ("api/live/overview" in url and "betano.ca" in url and "application/json" in mime) or \
           ("fixture-view" in url and "betmgm.ca" in url and "application/json" in mime) or \
           ("api.americanwagering.com" in url and "application/json" in mime) or \
           ("api/sportscontent" in url and "draftkings.com" in url and "application/json" in mime) or \
           ("content-managed-page" in url or "getMarketPrices" in url):
            
            ws.request_urls[req_id] = url
            
    if data.get("method") == "Network.loadingFinished":
        req_id = data.get("params", {}).get("requestId")
        if req_id in ws.request_urls:
            cmd_id = hash(req_id) % 100000 
            req = {
                "id": cmd_id, 
                "method": "Network.getResponseBody",
                "params": {"requestId": req_id}
            }
            ws.send(json.dumps(req))
            ws.global_cmd_to_url[cmd_id] = ws.request_urls[req_id]

    if "id" in data and "result" in data and "body" in data.get("result", {}):
        cmd_id = data["id"]
        if cmd_id in ws.global_cmd_to_url:
            url = ws.global_cmd_to_url[cmd_id]
            try:
                body_str = data["result"]["body"]
                if data["result"].get("base64Encoded"):
                    body_str = base64.b64decode(body_str).decode('utf-8', errors='ignore')
                    
                payload = json.loads(body_str)
                out_data = {
                    "_DEBUG_URL": url,
                    "data": payload
                }
                
                # Determine which sportsbook it is
                if "api/live/overview" in url and "betano.ca" in url:
                    save_json("betano", out_data, url)
                elif "fixture-view" in url and "betmgm.ca" in url:
                    save_json("betmgm", out_data, url)
                elif "api.americanwagering.com" in url:
                    save_json("caesars", out_data, url)
                elif "api/sportscontent" in url and "draftkings.com" in url:
                    save_json("draftkings", out_data, url)
                elif "content-managed-page" in url or "getMarketPrices" in url:
                    # Fanduel special logic
                    if "getMarketPrices" in url:
                        save_json("fanduel", out_data, url, is_ws=True)
                    else:
                        save_json("fanduel", out_data, url)

            except Exception as e:
                print(f"[!] Error parsing JSON body for {url}: {e}")

active_ws_urls = set()

def on_error(ws, error):
    print("\n[!] Websocket Error:", error)

def on_close(ws, close_status_code, close_msg, ws_url):
    print(f"\n[!] Websocket Connection Closed for {ws_url}.")
    if ws_url in active_ws_urls:
        active_ws_urls.remove(ws_url)

def on_open(ws):
    print("Websocket Connected successfully! Enabling Network tracking...")
    ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
    ws.send(json.dumps({"id": 2, "method": "Network.setCacheDisabled", "params": {"cacheDisabled": True}}))
    ws.send(json.dumps({"id": 3, "method": "Emulation.setFocusEmulationEnabled", "params": {"enabled": True}}))

def start_ws_client(ws_url):
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=lambda ws, code, msg: on_close(ws, code, msg, ws_url)
    )
    ws.run_forever()

def main():
    port = 19222 
    print(f"Looking for Chrome with remote debugging on port {port}...")
    print(f"Waiting for ALL sportsbook traffic...")
    print(f"Make sure to REFRESH all sportsbook pages to capture the initial JSONs!")
    
    while True:
        try:
            req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
            with urllib.request.urlopen(req) as response:
                targets = json.loads(response.read().decode())
                
            for target in targets:
                if target.get("type") == "page" and not target.get("url", "").startswith("devtools://"):
                    ws_url = target.get("webSocketDebuggerUrl")
                    if ws_url and ws_url not in active_ws_urls:
                        print(f"[*] Attaching to new tab: {target.get('url')}")
                        active_ws_urls.add(ws_url)
                        t = threading.Thread(target=start_ws_client, args=(ws_url,), daemon=True)
                        t.start()
        except urllib.error.URLError:
            pass
        time.sleep(2)

if __name__ == "__main__":
    main()
