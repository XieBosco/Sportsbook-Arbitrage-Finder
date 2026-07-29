import asyncio
import json
import websocket
import urllib.request
import re
import base64
import cbor2
import io
import time

request_urls = {}
cmd_to_url = {}
is_state_loaded = False
id_map = {}
alias_map = {}

def build_id_map(data, map_dict):
    if isinstance(data, dict):
        if 'id' in data:
            map_dict[data['id']] = data
        for k, v in data.items():
            build_id_map(v, map_dict)
    elif isinstance(data, list):
        for item in data:
            build_id_map(item, map_dict)

def get_event_and_market_for_selection(sel_id):
    # O(1) lookup since id_map is flattened and selections have eventId and marketId
    sel = id_map.get(sel_id)
    if sel:
        event_id = sel.get('eventId')
        market_id = sel.get('marketId')
        
        event = id_map.get(event_id, {}) if event_id else None
        market = id_map.get(market_id, {}) if market_id else None
        
        if event and market:
            return event.get('name', 'Unknown Event'), market.get('name', 'Unknown Market'), market.get('line')
            
    # Fallback to O(N) search through possible nested structures
    for obj_id, obj in id_map.items():
        # Check standard markets array
        if 'markets' in obj:
            for market in obj.get('markets', []):
                if isinstance(market, dict) and 'selections' in market:
                    for selection in market.get('selections', []):
                        if isinstance(selection, dict) and selection.get('id') == sel_id:
                            return obj.get('name', 'Unknown Event'), market.get('name', 'Unknown Market'), market.get('line')
        
        # Check v4/home keyMarketGroups structure
        if 'keyMarketGroups' in obj:
            for kmg in obj.get('keyMarketGroups', []):
                if isinstance(kmg, dict) and 'markets' in kmg:
                    for market in kmg.get('markets', []):
                        if isinstance(market, dict) and 'selections' in market:
                            for selection in market.get('selections', []):
                                if isinstance(selection, dict) and selection.get('id') == sel_id:
                                    return obj.get('name', 'Unknown Event'), market.get('name', 'Unknown Market'), market.get('line')

    return None, None, None

def extract_cbor_updates(decoded_bytes):
    if len(decoded_bytes) < 2:
        return None, None, None
        
    msg_type = decoded_bytes[0]
    
    if msg_type == 4:
        for offset in range(2, min(10, len(decoded_bytes))):
            fp = io.BytesIO(decoded_bytes[offset:])
            try:
                item = cbor2.load(fp)
                if isinstance(item, dict) and 'id' in item:
                    alias = bytes(decoded_bytes[2:offset])
                    
                    # Add newly discovered objects to the map if they aren't already there
                    if item['id'] not in id_map:
                        id_map[item['id']] = item
                        
                    return alias, item['id'], item.get('price')
            except Exception:
                pass
                
    elif msg_type == 5:
        matched_alias = None
        for alias in sorted(alias_map.keys(), key=len, reverse=True):
            if decoded_bytes[2:].startswith(alias):
                matched_alias = alias
                break
                
        if matched_alias:
            payload = decoded_bytes[2 + len(matched_alias):]
            fp = io.BytesIO(payload)
            items = []
            while fp.tell() < len(payload):
                try:
                    items.append(cbor2.load(fp))
                except Exception:
                    break
                    
            for item in items:
                if isinstance(item, bytes):
                    s = item.decode('ascii', errors='ignore')
                    m = re.search(r'([a-zA-Z]*)(\d+/\d+)', s)
                    if m:
                        frac = m.group(2)
                        try:
                            num, den = map(float, frac.split('/'))
                            dec = 1.0 + (num / den)
                            if dec >= 2.0:
                                am = int((dec - 1.0) * 100)
                            else:
                                am = int(-100 / (dec - 1.0))
                            
                            odds_dict = {
                                'f': frac,
                                'd': round(dec, 2),
                                'a': am
                            }
                            return matched_alias, None, odds_dict
                        except Exception:
                            pass
                            
    return None, None, None

def on_message(ws, message):
    global is_state_loaded, id_map, alias_map
    
    data = json.loads(message)
    
    if data.get("method") == "Network.requestWillBeSent":
        req = data.get("params", {}).get("request", {})
        req_id = data.get("params", {}).get("requestId")
        url = req.get("url", "")
        if "api.americanwagering.com" in url:
            request_urls[req_id] = url
            
    elif data.get("method") == "Network.responseReceived":
        resp = data.get("params", {}).get("response", {})
        req_id = data.get("params", {}).get("requestId")
        url = resp.get("url", "")
        mime_type = resp.get("mimeType", "")
        if "api.americanwagering.com" in url and "application/json" in mime_type:
            cmd_id = abs(hash(req_id)) % 100000
            cmd_to_url[cmd_id] = url
            ws.send(json.dumps({
                "id": cmd_id,
                "method": "Network.getResponseBody",
                "params": {"requestId": req_id}
            }))
            
    elif "id" in data and data["id"] in cmd_to_url:
        url = cmd_to_url[data["id"]]
        if "/v4/home" in url:
            body_str = data.get("result", {}).get("body", "")
            is_base64 = data.get("result", {}).get("base64Encoded", False)
            if is_base64:
                body_str = base64.b64decode(body_str).decode('utf-8', errors='ignore')
            try:
                payload = json.loads(body_str)
                old_size = len(id_map)
                build_id_map(payload, id_map)
                new_size = len(id_map)
                if new_size > old_size:
                    print(f"\n[OK] Extracted {new_size - old_size} new objects into index")
                    is_state_loaded = True
            except Exception as e:
                print(f"[DEBUG] Error extracting json: {e}")
                pass
                
    elif data.get("method") == "Network.webSocketFrameReceived":
        params = data.get("params", {})
        response = params.get("response", {})
        payloadData = response.get("payloadData", "")
        
        if payloadData:
            try:
                cleaned = re.sub(r'[^a-zA-Z0-9+/=]', '', payloadData)
                cleaned += "=" * ((4 - len(cleaned) % 4) % 4)
                decoded_bytes = base64.b64decode(cleaned)
                
                if len(decoded_bytes) > 0 and decoded_bytes[0] in [4, 5]:
                    pass # print(f"Received msg type {decoded_bytes[0]}, length {len(decoded_bytes)}")
                
                alias, obj_id, odds_dict = extract_cbor_updates(decoded_bytes)
                
                if alias is not None:
                    print(f"DEBUG: Found alias {alias} (obj_id={obj_id}, odds={odds_dict})")
                    if obj_id is not None:
                        alias_map[alias] = obj_id
                        if obj_id in id_map and odds_dict:
                            id_map[obj_id].setdefault('price', {})
                            id_map[obj_id]['price'].update(odds_dict)
                            
                    elif odds_dict is not None:
                        if alias not in alias_map:
                            print(f"DEBUG: Alias {alias} not in alias_map!")
                        else:
                            obj_id = alias_map[alias]
                            if obj_id not in id_map:
                                print(f"DEBUG: obj_id {obj_id} not in id_map!")
                            else:
                                old_price = id_map[obj_id].get('price', {}).copy()
                                
                                id_map[obj_id].setdefault('price', {})
                                id_map[obj_id]['price'].update(odds_dict)
                                
                                event_name, market_name, line = get_event_and_market_for_selection(obj_id)
                                
                                if not event_name or not market_name:
                                    print(f"DEBUG: get_event_and_market failed for {obj_id}")
                                else:
                                    new_price = id_map[obj_id]['price']
                                    
                                    if old_price.get('a') != new_price.get('a'):
                                        print("\n                 --- LIVE ODDS UPDATE ---")
                                        print("================================================================================")
                                        print(f"Match: {event_name.strip('|')} ")
                                        
                                        market_display = market_name
                                        if line is not None:
                                            market_display += f" (Line: {line})"
                                            
                                        print(f"  [{market_display}]")
                                        
                                        sel_name = id_map[obj_id].get('name', 'Unknown Selection').strip('|')
                                        odds = new_price.get('a', 'N/A')
                                        if odds != 'N/A' and int(odds) > 0:
                                            odds = f"+{odds}"
                                        state = id_map[obj_id].get('state', 'Unknown')
                                        link = f"https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds={obj_id}"
                                        
                                        print(f"      [PRICE] {sel_name} | Odds: {odds} | State: {state} | Link: {link}")
                                        print("================================================================================")
                                    else:
                                        print(f"DEBUG: Price didn't change for {obj_id}")
                                
            except Exception as e:
                pass

def on_error(ws, error):
    import traceback
    print("\nWebsocket Error Type:", type(error))
    print("Websocket Error Output:", repr(error))
    if not isinstance(error, KeyboardInterrupt):
        traceback.print_exc()

def on_close(ws, close_status_code, close_msg):
    print(f"\nWebsocket Connection Closed. Code: {close_status_code}, Msg: {close_msg}")

def on_open(ws):
    print("Websocket Connected successfully! Enabling Network tracking...")
    ws.send(json.dumps({
        "id": 1,
        "method": "Network.enable"
    }))
    ws.send(json.dumps({
        "id": 2,
        "method": "Network.setCacheDisabled",
        "params": {"cacheDisabled": True}
    }))
    ws.send(json.dumps({
        "id": 21,
        "method": "Network.clearBrowserCache"
    }))
    ws.send(json.dumps({
        "id": 22,
        "method": "Network.clearBrowserCookies"
    }))
    ws.send(json.dumps({
        "id": 3,
        "method": "Page.enable"
    }))
    ws.send(json.dumps({
        "id": 4,
        "method": "Runtime.evaluate",
        "params": {"expression": "console.log('Bot tracking enabled. Please manually refresh the page.')"}
    }))
    
    print("\n**************************************************************")
    print("*** PLEASE REFRESH THE BROWSER PAGE NOW TO LOAD THE ODDS ***")
    print("**************************************************************\n")

    import threading
    def debug_loop():
        while True:
            time.sleep(10)
            print(f"[DEBUG] alias_map size: {len(alias_map)}, id_map size: {len(id_map)}, is_state_loaded: {is_state_loaded}")
    
    threading.Thread(target=debug_loop, daemon=True).start()

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
                print("Could not find a valid page target. Make sure Chrome is open and not on a devtools page. Retrying in 2s...")
                time.sleep(2)
        except Exception as e:
            print(f"Failed to connect to CDP: {e}. Retrying in 2s...")
            time.sleep(2)
            
    print(f"Attached to page: {page_target.get('title', 'Unknown')} ({page_target.get('url', 'Unknown')})")
    
    ws_url = page_target['webSocketDebuggerUrl']
    
    wsapp = websocket.WebSocketApp(ws_url,
                                 on_open=on_open,
                                 on_message=on_message,
                                 on_error=on_error,
                                 on_close=on_close)
    
    print("Waiting for Caesars network traffic...")
    wsapp.run_forever()

if __name__ == "__main__":
    main()
