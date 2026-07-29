# Continuation Prompt: Build `caesars_scraper.py`

## Pre-reading

Read `caesars_workspace/decoder_handoff.md` first. It documents the completed
decoder (`analyze_caesar.py`) — what it does, its validated accuracy, and the
assumptions baked into the code that will need to change for live operation.

Also read `caesars_workspace/documentation/diffusion_protocol_analysis.md` for
the full Diffusion protocol spec (message types, binary delta format, CBOR
schemas, alias lifecycle).

## Task

> Write a Python script named caesars_scraper.py that acts as a live odds
> scraper for Caesars Sportsbook. To avoid anti-bot detection, the script must
> prompt the user to launch a Chrome browser with a remote debugging port,
> navigate to the Caesars MLB page, and use the Chrome DevTools Protocol (CDP)
> to passively intercept network traffic without making any direct API
> requests itself. The scraper must perform similar steps to analyze_caesar.py
> to extract data. Finally, the scraper will output updates to the terminal as
> soon as the websocket messages are sent and format the data to include the
> game name, team name, handicap, american odds, and other important
> information related to the game and selection.

## Critical constraint: passive CDP interception only

This script attaches to an **already-running, user-launched Chrome instance**
via its remote debugging port purely to eavesdrop on WebSocket frames the
browser is already sending and receiving as a normal user session.

**It must:**
- Connect to `http://localhost:{port}/json` to enumerate CDP targets, find the
  Caesars page, and attach to its debugger WebSocket.
- Enable `Network.enable` and subscribe to `Network.webSocketFrameReceived` and
  `Network.webSocketFrameSent` events.
- Also subscribe to `Network.responseReceived` to intercept the `/v4/home`
  JSON response (use `Network.getResponseBody` to retrieve it) — this is how
  the enrichment lookup gets populated, without making a separate HTTP request.

**It must never:**
- Issue its own API or WebSocket requests to Caesars.
- Automate page interaction beyond what the user does themselves.
- Spoof headers, fingerprints, or attempt to bypass bot-detection challenges.
- Fall back to an alternate data source if CDP attachment fails.

**If CDP can't attach** (e.g. Chrome wasn't launched with `--remote-debugging-port`),
the script must fail immediately with a clear message telling the user the
exact command to relaunch Chrome:
```
chrome.exe --remote-debugging-port=19222
```

## Reuse existing decoding logic

`analyze_caesar.py` contains **proven, validated** implementations of:
- `decode_cbor_item()` — from-scratch CBOR decoder (major types 0–5, 7,
  including float16/32/64)
- `apply_binary_delta()` — Diffusion Type 5 delta applicator
- `find_alias_and_cbor_type84()` / `find_alias_and_cbor_type04()` — alias
  boundary detection for compressed and uncompressed Type 4 messages
- `parse_type05()` — Type 5 frame parsing (alias + 0x00 separator + payload)
- `classify_object()` — heuristic event/market/selection classifier
- `build_enrichment_lookup()` — `/v4/home` JSON → selectionId lookup builder

**Import or copy these directly.** Do not re-derive the CBOR decoder, delta
format, or alias resolution logic — that work is done and validated at 100%
(551/551 messages, 131/131 deltas, 128/128 alias mappings, 0 failures).

## Suggested CDP connection approach

Use the **`websocket-client`** library (`pip install websocket-client`) to
connect to the CDP endpoint. This keeps the dependency footprint minimal — no
Selenium, Playwright, or puppeteer needed since the script only listens, never
controls the page.

```python
import websocket, json, requests

# 1. Enumerate targets
targets = requests.get("http://localhost:9222/json").json()
page = next(t for t in targets if "caesars" in t.get("url", "").lower())
ws_url = page["webSocketDebuggerUrl"]

# 2. Attach to the page's debugger WebSocket
ws = websocket.create_connection(ws_url)
ws.send(json.dumps({"id": 1, "method": "Network.enable"}))

# 3. Listen for events
while True:
    msg = json.loads(ws.recv())
    if msg.get("method") == "Network.webSocketFrameReceived":
        payload = msg["params"]["response"]["payloadData"]
        # payload is base64-encoded — same format as ws_*.txt files
        raw = base64.b64decode(payload)
        # ... decode using the existing pipeline ...
```

## What's new and needs design work

These are the parts that **don't exist** in `analyze_caesar.py` and need to be
built from scratch:

1. **CDP session management** — Enumerating targets, attaching to the right
   page, enabling network interception, handling the CDP JSON-RPC protocol.

2. **Real-time frame capture** — Instead of reading sorted `ws_*.txt` files,
   the scraper receives `Network.webSocketFrameReceived` events as they arrive.
   Frames must be decoded and acted on immediately.

3. **Identifying the right WebSocket** — Caesars opens 4 WebSocket connections
   (odds, livescores, cashout, microbetting). The scraper needs to identify
   which `requestId` corresponds to the primary odds Diffusion socket (the one
   at `wss://api.americanwagering.com/.../diffusion?ty=WB&...`). Track
   `Network.webSocketCreated` events to map requestIds to URLs.

4. **Live `/v4/home` interception** — Instead of loading a static `json_5.json`,
   intercept the `/v4/home` response via `Network.responseReceived` +
   `Network.getResponseBody`. This should happen automatically when the page
   loads. The enrichment lookup must be built (or rebuilt) from this response.

5. **Live alias/state management** — Same `alias_state` dict as
   `analyze_caesar.py`, but maintained indefinitely as the session runs. Must
   handle:
   - New aliases appearing at any time (new selections going live)
   - Chained deltas (each delta updates the state for subsequent deltas)
   - Potential alias resets on WebSocket reconnect (clear state on new `0x23`)

6. **Terminal output formatting** — Print each decoded update immediately.
   Suggested format for selection updates:
   ```
   [16:42:03] Toronto Blue Jays at Boston Red Sox
              |Run Line Live| (line: 1.5)
              |Toronto Blue Jays|  a: -200  d: 1.50  f: 1/2  [open]
   ```
   Market updates (line changes) and event updates (active/suspended) should
   also be printed with appropriate formatting.

7. **Graceful startup** — The user may have already been on the page for a
   while before starting the scraper. The script should handle mid-session
   attach: if it sees a Type 5 delta for an unknown alias, it should log a
   warning and skip rather than crash. Aliases will get populated as new
   Type 4 messages arrive.

## Additional Information

1. **Reconnect handling** — If the Diffusion WebSocket disconnects and
   reconnects (which happens periodically), the scraper should automatically
   detect the new connection and continue, and alert the user. The new connection
   will re-establish all aliases from scratch (new handshake, new subscriptions,
   new Type 4 bindings).

2. **Page navigation** — If the user navigates away from the MLB page (e.g. to
   NFL or to a different tab), the WebSocket may close. The script should wait
   for them to navigate back.

3. **`/v4/home` refresh** — The initial `/v4/home` response may go stale as
   markets open/close. The scraper should re-intercept `/v4/home` if the page
   refreshes.

5. **Output destination** — Terminal and log to a file /
   emit structured JSON lines for downstream consumption.
