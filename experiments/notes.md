# Sportsbook API Notes

## FanDuel

**Deeplink Schema:**
```
https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]={marketId}&selectionId[0]={selectionId}
```

**Data Flow:**
FanDuel uses a reference dictionary that maps `marketId` and `selectionId` values to specific markets. At the beginning of loading a FanDuel page, the client requests the reference dictionary from the endpoint:
```
https://sbapi.on.sportsbook.fanduel.ca/api/content-managed-page?page=CUSTOM&customPageId=mlb&pbHorizontal=false&_ak=FhMFpcPWXMeyZxOx&timezone=America%2FToronto
```
This dictionary allows the frontend to map the corresponding IDs to plain English.

In short intervals, the client sends `POST` requests to the web servers using the URL:
```
getMarketPrices?priceHistory=0
```
The response contains `marketId`, `selectionId`, and odds data that are mapped to plain English using the reference dictionary.

**Variables:**
- `marketId`: An identifier for a unique market.
- `selectionId`: An identifier for a unique selection.

### Building the FanDuel Scraper

Unlike DraftKings and Betano, FanDuel does not stream live odds over a constant WebSocket. Instead, it relies on frequent `POST` requests to update the frontend. Extracting this data requires intercepting these HTTP responses.

#### 1. Passive CDP Interception
To extract live odds without triggering FanDuel's headless browser detection, attach to a standard Chrome session using the remote debugging protocol (CDP). Since the data is transmitted via HTTP rather than WebSockets, you must monitor the `Network.responseReceived` events.
- **Important Note:** CDP does not automatically attach response bodies to the `responseReceived` event. Once you detect the target URL, you must immediately dispatch a `Network.getResponseBody` command containing the `requestId` to pull the actual JSON payload.

#### 2. Intercepting the Reference Dictionary
The initial page load fetches a massive dictionary mapping arbitrary IDs to plain English names.
- Intercept the URL containing `content-managed-page`.
- Extract `events` (games), `markets` (types of bets), and `selections` (runners/teams) from the `attachments` JSON block. Store these in memory to translate incoming odds updates.

#### 3. Deeply Nested JSON & Recursive Searching (CRITICAL)
When intercepting odds updates, look for URLs containing `getMarketPrices`. The returned JSON structure is heavily nested and subject to change without warning.
- **The Fix:** Do not hardcode array indexes or dictionary keys to find the odds! Instead, implement a recursive JSON traversal function that scans the entire payload for any object that contains both the `"marketId"` and `"runnerDetails"` keys. This guarantees bug-free extraction even if FanDuel shifts the payload hierarchy.

#### 4. Extracting American Odds
Once you locate a `runnerDetails` object, extracting the odds requires defensive parsing, as the location can shift between formats:
- Attempt to extract from `runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")`.
- If it returns `None`, fallback to `runner.get("winRunnerOdds", {}).get("trueOdds", {}).get("americanOdds")`.

---

## DraftKings

**Deeplink Schema:**
```
https://sportsbook.draftkings.com/event/{seoIdentifier}/{eventId}?outcomes={selectionId}
```
*Note: The preferred short schema to use is:*
```
https://sportsbook.draftkings.com/?outcomes={selectionId}
or 
https://sportsbook.draftkings.com/event/{eventId}?outcomes={selectionId}
```

*Other Examples:*
- `https://sportsbook.draftkings.com/event/spain-vs-austria/34331119?outcomes=0QA346850632%232196171599_13L209533Q10Q21`
- `https://sportsbook.draftkings.com/event/stl-cardinals-%40-chi-cubs/34350317?outcomes=0HC85377741P150_3`

**Data Flow:**
DraftKings uses a websocket connection to send live odds data to the frontend. It first establishes a connection to:
```
wss://sportsbook-ws-ca-on.draftkings.com/websocket?format=msgpack&locale=en
```
and sends binary messages which are then decoded to live odds data.

**Example Binary Message:**
```text
ldkkNmU2ZmIzZDUtZGFkYy00ZjdkLTg4YzUtNWE0OWI4NWMwNzRjpnVwZGF0ZZOTlZCQkJCQk5CQkJOQkJGSGJixMEhDODUzOTkwMTVQMjUwXzGtV0FTIE5hdGlvbmFsc5WkKzEwNqQyLjA2pTUzLzUwwKM0OSXLQAB64UeuFHvLQAQAAAAAAADR9j2TrU1haW5Qb2ludExpbmWjU0dQo09TQrEwSEM4NTM5OTAxNVAzNTBfMcCDq2NyZWF0ZWRUaW1luDIwMjYtMDctMDZUMjM6MjY6NTkuNjUzWqxyZWNlaXZlZFRpbWW4MjAyNi0wNy0wNlQyMzoyNjo1OS42NjBarXB1Ymxpc2hlZFRpbWW4MjAyNi0wNy0wNlQyMzoyNjo1OS44MzJawJLX
```
The binary message can be read as a base64 encoded string. The encoded json follows the MessagePack protocol, requiring extra work.
Here is the complete code to natively decode the payloads
```
import base64
import msgpack
import json
import re
from datetime import datetime, timezone

# Your exact Washington Nationals string
b64_payload = "ldkkZWNhMWFmMzItODc4Yy00MTA5LWFmNWYtMWQ2ZTBmYTM0YzFlpnVwZGF0ZZOTlZCQkJCQk5CQkJOQkJGSGJixMEhDODU0NTc1NjdQMTUwXzGqTEEgRG9kZ2Vyc5Wm4oiSMjQ4pDEuNDClMjUvNjLAozcxJcs/9nOc6C2mVss/+AAAAAAAANH6JZOtTWFpblBvaW50TGluZaNTR1CjT1NCwMCDq2NyZWF0ZWRUaW1luDIwMjYtMDctMTJUMDI6Mzg6MDIuNzk5WqxyZWNlaXZlZFRpbWW4MjAyNi0wNy0xMlQwMjozODowMi44MDdarXB1Ymxpc2hlZFRpbWW4MjAyNi0wNy0xMlQwMjozODowMy4wNzlawJLX/yr/PrBqUv4LAA=="

# 1. Clean and pad exactly like the first successful script
b64_payload = re.sub(r'[^a-zA-Z0-9+/]', '', b64_payload)
if len(b64_payload) % 4 == 1:
    b64_payload = b64_payload[:-1]
b64_payload += "=" * ((4 - len(b64_payload) % 4) % 4)

# 2. Custom encoder to translate Timestamps and raw bytes into valid JSON strings
def safe_json_encoder(obj):
    if type(obj).__name__ == 'Timestamp':
        return datetime.fromtimestamp(obj.seconds, tz=timezone.utc).isoformat()
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return str(obj)

try:
    raw_bytes = base64.b64decode(b64_payload)
    
    # 3. Revert to unpackb (which successfully extracted the Nationals data earlier)
    # We leave raw=True (the default) so it doesn't crash on binary hashes, 
    # letting our safe_json_encoder handle the text conversion.
    data = msgpack.unpackb(raw_bytes, strict_map_key=False)
    
    # 4. Format into clean JSON
    valid_json_output = json.dumps(data, indent=2, default=safe_json_encoder)
    
    print(valid_json_output)
    
    # Save it to a file you can copy-paste from
    with open("draftkings_odds.json", "w") as f:
        f.write(valid_json_output)
        print("\nSuccessfully saved to draftkings_odds.json!")
        
except Exception as e:
    print(f"Extraction failed: {e}")
```
Example decoded string:
```
['6e6fb3d5-dadc-4f7d-88c5-5a49b85c074c',
 'update',
 [[[[], [], [], [], []],
   [[], [], []],
   [[],
    [],
    [[24,
      ['0HC85399015P250_1',
       'WAS Nationals',
       ['+106', '2.06', '53/50', None, '49%'],
       2.06,
       2.5,
       -2499,
       ['MainPointLine', 'SGP', 'OSB'],
       '0HC85399015P350_1']]]]],
  None,
  {'createdTime': '2026-07-06T23:26:59.653Z',
   'publishedTime': '2026-07-06T23:26:59.832Z',
   'receivedTime': '2026-07-06T23:26:59.660Z'}],
 None,
 [Timestamp(seconds=1783380419, nanoseconds=865206800), 0]]

```
Index-to-variable mappings:

| Array Index | Frontend Variable | Data Type | Value from Payload |
| :--- | :--- | :--- | :--- |
| **0** | `selectionId` (or `outcomeId`) | String | `"0HC85399015P250_1"` |
| **1** | `selectionName` | String | `"WAS Nationals"` |
| **2** | `odds` | Array | `["+106", "2.06", "53/50", 49]` |
| **3** | `binaryOddsData` (or `status`) | Binary/Float Block | `[Raw Float/Binary Data]` |
| **4** | `marketType` | String | `"MainPointLine"` |
| **5** | `tags` | Array of Strings | `["SGP", "OSB"]` |
| **6** | `marketId` | String | `"0HC85399015P350_1"` |

| Odds Sub-Array Index | Frontend Variable | Data Type | Value from Payload |
| :--- | :--- | :--- | :--- |
| **0** | `american` | String | `"+106"` |
| **1** | `decimal` | String | `"2.06"` |
| **2** | `fractional` | String | `"53/50"` |
| **3** | `impliedProbability` | Integer | `49` |

Afterwards, Draftkings sends a GET request to fetch a reference dictionary:
```
https://sportsbook-nash.draftkings.com/sites/CA-ON-SB/api/sportscontent/controldata/league/leagueSubcategory/v1/markets?isBatchable=false&templateVars=84240&eventsQuery=%24filter%3DleagueId%20eq%20%2784240%27%20AND%20clientMetadata%2FSubcategories%2Fany%28s%3A%20s%2FId%20eq%20%274519%27%29&marketsQuery=%24filter%3DclientMetadata%2FsubCategoryId%20eq%20%274519%27%20AND%20tags%2Fall%28t%3A%20t%20ne%20%27SportcastBetBuilder%27%29&include=Events&entity=events
```
in order to obtain extraneous data for markets.


**Extracting Live Odds via CDP (Chrome DevTools Protocol):**
DraftKings actively flags and blocks heavily automated headless browsers. To securely extract the WebSocket data without triggering detection, a passive CDP listening approach is highly recommended:

1. **Connect via CDP:** Launch a standard (non-headless) Chrome instance with a remote debugging port (e.g., `--remote-debugging-port=19222`). Use a script to fetch `http://127.0.0.1:19222/json` and attach to the active tab's CDP websocket.
2. **Enable Network Tracking:** Send the `Network.enable` CDP command to begin intercepting all network traffic on the tab.
3. **Capture the Reference Dictionary:** When the DraftKings page is loaded or refreshed, intercept the HTTP response to `https://sportsbook.draftkings.com/api/sportscontent/...`. This JSON acts as the "Reference Dictionary," providing a static mapping of `eventId`, `marketId`, and `selectionId` to human-readable names.
4. **Intercept WebSocket Frames:** Listen for `Network.webSocketFrameReceived` events originating from `wss://sportsbook-ws...draftkings.com`. 
5. **Base64 & MessagePack Decoding:** The `response.payloadData` from the WebSocket frame contains a Base64 encoded string. Decode this string into bytes, and unpack it using the `msgpack` library (ensure `strict_map_key=False`).
6. **Resolving Dynamic Markets (Important Bug-Fix):** When a handicap changes (e.g., Over 8.5 to Over 8.0), DraftKings dynamically generates a brand new market and selection ID in the live odds payload. This new ID will **not** exist in your initial Reference Dictionary!
   - Fortunately, DraftKings selection IDs follow a strict format: `PREFIX` + `CORE_ID` + `HANDICAP` (e.g., `0OU85458301O850_1`).
   - The `CORE_ID` (e.g., `85458301`) remains constant across all handicap changes for a specific market grouping.
   - To resolve a new, unknown market: Extract the core ID using a regex like `^0[A-Z]{2}(\d+)`. Search your original Reference Dictionary for any old selection ID that shares this exact core ID. Since they share the core ID, they point to the exact same game/event!
7. **Handling Static Handicaps (Moneyline):** To save bandwidth, if a market's odds change but its handicap does not (which is always true for Moneyline), DraftKings sends `null` for the `marketId` at the end of the odds array instead of repeating the string. Ensure your array-parsing logic explicitly tolerates `null` (or `None` in Python) in the final index of the array, otherwise you will silently drop all Moneyline updates!


**Variables:**
- `eventId`: An identifier for a unique event. (Needed to fetch the necessary `seoIdentifier`).
- `seoIdentifier`: An identifier used for SEO that also attaches itself to URLs to add bets to a betslip.
- `selectionId`: An identifier for a unique selection.

---

## BetMGM

**Deeplink Schema:**
```
Examples
https://www.on.betmgm.ca/en/sports/events/argentina-egypt-2:7828823?options=2:7828823-201196265-762963230&type=Single
or
https://www.on.betmgm.ca/en/sports/events/colorado-rockies-at-los-angeles-dodgers-19768288?options=19768288-1541910451-2250808212&type=Single
or
https://www.on.betmgm.ca/en/sports?options=2:7716083-190814890-698929676

Recommended Schema
https://www.on.betmgm.ca/en/sports?options={fixtureId}-{optionMarketId}-{optionId}
```

**Data Flow:**
BetMGM uses a websocket connection to send live odds data to the frontend. It first establishes a connection to:
```
wss://cds-push.on.betmgm.ca/ws-1-0?lang=en-us&country=CA&x-bwin-accessId=MzViOTU5Y2EtNzgyMy00ZTBmLThkNDctYjRlYjgwNjMwZDQy&appUpdates=false
```
and sends a raw json string that either contains frontend changes or live odds updates.

**Example Message:**
```
Find example in the betmgm_data folder
```

In frequent intervals, BetMgm sends a GET request to retrieve a json reference dictionary mapping fixtureIds to metadata on that fixture. It uses the url:
```
https://www.betmgm.ca/cds-api/bettingoffer/fixture-view?x-bwin-accessid=ZjNmOGM4OTAtZmVhOS00ZTZiLWE5MDQtNGVjNWM5MDkxNjQ1&lang=en-us&country=CA&userCountry=CA&subdivision=CA-Ontario&offerMapping=Filtered&scoreboardMode=Full&fixtureIds=19766272&state=Latest&includePrecreatedBetBuilder=true&supportVirtual=true&isBettingInsightsEnabled=true&useRegionalisedConfiguration=true&includeRelatedFixtures=false&statisticsModes=Rank,Pitchers&firstMarketGroupOnly=true
```

**Variables:**
- `fixtureId`: an unique identifier for a game
- `optionMarketId`: an unique identifier for a market
- `optionId`: an unique identfier for a selection within a market

### Building the BetMGM Scraper

Building a BetMGM scraper requires intercepting both standard HTTP requests and WebSocket frames via CDP (Chrome DevTools Protocol).

#### 1. Passive CDP Interception
To avoid headless browser detection, attach to a regular Chrome session using CDP (`Network.enable`). We need to monitor both `Network.responseReceived` and `Network.webSocketFrameReceived`.

#### 2. The Reference Dictionary
BetMGM does not include human-readable game names (like "Indiana Fever at Las Vegas Aces") within the live odds WebSocket payload. It only provides the `fixtureId`.
- To map this ID, you must intercept HTTP responses (`Network.responseReceived`) where the URL contains `fixture-view`.
- Use `Network.getResponseBody` to retrieve the JSON payload and extract the `fixtureId` and the human-readable game name. Store this mapping locally.

#### 3. SignalR and the `\x1e` Terminator
BetMGM's WebSocket data runs on SignalR. 
- SignalR frames are appended with the ASCII Record Separator character `\x1e` (e.g. `{"type":1,...}\x1e`).
- Running a raw `json.loads()` on this string will fail. You must `split('\x1e')` and iterate over the fragments before parsing them into JSON.

#### 4. The Live Odds Data Model
BetMGM sends odds updates via plain JSON. Look for objects inside the `arguments[0]['payload']` array. You must handle two distinct command types:
- **GameUpdateCommand**: Updates primary markets. Extract data from `payload['game']` (`id`, `name`) and iterate through `payload['game']['results']` to find `id`, `name`, and `americanOdds`.
- **OptionMarketUpdateCommand**: Updates secondary prop markets. Extract data from `payload['optionMarket']` (`id`, `name`) and iterate through `payload['optionMarket']['options']` to find `id`, `name`, and `price.americanOdds`.

---

## Betano

**Deeplink Schema:**
```
Betano does not have a deeplink schema; however, the preferred url to redirect an user to the appropriate market is
https://www.betano.ca/live/mexico-england/88363620/
or its parameterized version
https://www.betano.ca/live/{eventName}/{eventId}/
```

**Data Flow:**
Betano uses a websocket connection to send live odds data to the frontend. It first establishes a connection to:
```
wss://www.betano.ca/contenthub?platformType=1
```
and sends a Base64-encoded string that contains a LZ4 block compressed JSON payload.

> [!WARNING]
> **Anti-Bot Port Scanning:** Betano's frontend JavaScript actively attempts to open WebSocket connections to `ws://127.0.0.1` on common debugging and automation ports (like `9222`). If your scraper exposes its CDP port locally and Betano scans it successfully, your session will be instantly flagged as a bot. To defeat this, you must block these local requests. The easiest method is to install the **AdGuard AdBlocker MV3** extension and add `||127.0.0.1^` and `||localhost^` to your **User rules** list. This intercepts and blocks the port scan before it reaches your local machine.

**Example Base64-Encoded String:**
```text
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
```
Here is the complete code to natively decode the payloads
```
import base64
import lz4.frame
import json

def decode_danae_message(b64_payload):
    # Step 1: Base64 decode the string into raw bytes
    compressed_bytes = base64.b64decode(b64_payload)
    
    # Step 2: Decompress the LZ4 frame
    decompressed_bytes = lz4.frame.decompress(compressed_bytes)
    
    # Step 3: Decode the bytes into a UTF-8 string
    json_string = decompressed_bytes.decode('utf-8')
    
    # Step 4: Parse the JSON
    data = json.loads(json_string)
    
    return data

# Test it with your original payload
payload = "BCJNGEBAwLEJAADxGVt7InZlcnNpb24iOjE1MSwiZXZlbnRJZCI6ODgwNzU3NDQsInNwb3ITAPEuNiwidHlwZSI6MzAwLCJwYXlsb2FkIjp7ImxpdmVEYXRhIjp7InNjb3JlIjp7ImhvbWUiOiIwIiwiYXdheQsAgX0sImNsb2NrKQDyOmVjb25kc1NpbmNlU3RhcnQiOjU0NX0sInJlc3VsdHMiOnsicGVyaW9kIjoiMSIsImJhbGxzIjowLCJzdHJpa2VzIjoxLCJvdXQVAKJiYXNlYmFsbEFjPAADgAB2YmF0dGluZ4YAqnBpdGNoaW5nIn3bAPMCc29ydGluZ0luZGV4IjoxfSx+AIFEZXNjcmlwdCQBgSIxc3QgSW5uQAA5fX0sPwEfMj8BFBsxPwHxAHNlbGVjdGlvbkNoYW5nZfoA+xwyODM4ODQ1MTc2IjpbeyJpZCI6OTkyNDU2MDQ0MCwicHJpY2UiOjEuNX0sHgAVMR4A+hQyLjM3fV19LCJ0b3RhbE1hcmtldHNBdmFpbGFibGUiOjQ5NMMASDI0NjPEAHo3OTAyNDYxKAEPAwIfFjV9AR8yAwINTzE1MTcEAgQWOAQCHzEEAgEfMgQCBgXzAQWLAgQWAg8EAgofOAQCBF84dGggaQQCAik3NAMCZzQwNjc3OT8BLzIxQAEhDEMDByED8RNzZXJ2ZXJIb21lIjp0cnVlLCJjdXJyZW50U2V0TnVtYmVyGAEEFQALnAMWMZkBETAPAxJlIwBBTGlzdHcCA0QDFzEpAEM5In1dUgJPU2V0c1MADgQ9BB8yUgMFbEdhbWUgMk4DKTU1SgFYMzUyNTSJAgVJATkxMDOMBDJvbGTqAvECSWQiOjI4NDA2MTU1MjcsIm0AAwJ6BANwAxFz5QAFTAPyATYsImhhbmRpY2FwIjo2LjXvBPIISWQiOjM5LCJyZW5kZXJpbmdMYXlvdXRYAVNvbHVtbjME8QAwLCJkaXNwbGF5T3JkZXKkAAK4A8EzMjA0NTY4MiwibmEVBfYBT3ZlciA2LjUiLCJmdWxsThYANSJ9LJIAPzIuMZIABi80MJIAEBwxkgAbMpIAFTOSAD9VbmSTAAEBFwAC8gEB+gVmIkhDVEciGQEtMTOiAAJoAfEAQ2xvc2VUaW1lTWlsbGlzHgEPQgEBCjIBIjU1oQABuAFVNjY5NjahAFFPdmVyL48A3yBUb3RhbCBHb2FscyLeBAcaN9wELzU2UQIWCt0GBS4CCp4FcTY2NTcwNDBCAgLmAYUxNTYzMDcwOYAFcTQuN31dLCLNAFc3Mjk1NS0AdjMyMDY5NTQtACI5MCwAAlkAJzM3LAADWQAVNVkARjEuMTT4BQMfABc0HwAvODL4BQkLGgE4Mzg5GwF4NzY5MTkwN7YEAvABD7kGFmcyODQ4NzLuAIk4OTk5NTg2NqMAFTjCAAQfAAjhAC84NcIACToxMzTeAT8zOTDEABYPMAQKAr0AFTDIAg8wBAkoODX9AikxNzMEPzQ1MfICAw80BBMDFAEpMjgBAxEgZQAPNgQAdCwic2hvcnRJBAMoAAdMBE8xLjg4rgAKHzKuABAPUAQGBK4AFTmuAAKqAw+vAAABGQALsAAUVbAAFF1qAmIiRlRQTyIOAH9JZCI6MTU3vgAAD2sEKVQtOTgzMG4EA/YBFTe/AF9Qb2ludF4ECQ+CAgAfMYICFg9hBBGGMTc4NDAxNjEIBIY4Mzg3NDI4NeEJNjEuMgAKBB8AFTIIBC8zLv8JCg3DACoxM8IKWDQ2NjEzvwgSM5EBDwkEFmc5OTU2NDPDAHE5MjkzMTkwswcDwgrDNCwib3JpZ2luYWxQEwAxMS41fQuhY2VudGFnZU9mZscIHzESBAkaNRAEOTI0NosJD8oKCQg/CApGABkzDgtZODM0NTmFCB82EAEdZjgzNDkyOdMBiDkyODY1NjE40wElOTHTAQQfAAbTAUQxLjgzKAZYNDQyNzddAXYxNDc4NzI1VAY/Mi4xCQYKDEYFKDE3wwJ3ODM5Njc3OMQJB3UJD8MCEXkzOTI5MzU38ABBNjQ3N20EA3YJ6TJ9XSwiMjgzNzkyMzA0KwBoMDkwMDE3/AAYMRsBAh8AFTRKADk1LjRMAAhCBwItACU2Ny0ALTIuSwAlNjgeAD8xLjZsAgkqMzAnAik4OTgBdzc5MzQyNDY4AQUoAg85DyQfNzYNDU8yMjAzNg0EFjI2DQg6DxQyOg8PNg0HBCQNBTUNBUcNDzYNCh8yNg0EPzJuZDYNBDkxMDC+B3c4NDQwNjkzQQEPeQQeaDIwODk1NGkDaDYwOTYwMhwDFjA8BQMfABgzWg8fNj0FChs2AwIcMcIAODE2N7AMD8IAHzozMTP9D2g2MjEzMzAlCSczMysEAh8AFTbFAkMyLjk1XQNZOTI3MDJ/Cn8yNjM2MDI5EQMFAh4ACREDA6kDA5gLFzBbAQLeDAfdCTYyLjeYAAMeAAm3ABI5mAB4NDA2NTgyMqkDdjMyMDA4NTSYAAEKCgTjBgQfAAiZAB844hAJGzEXBjg4MTGqAw+nAQgPqgMkOjMwIogDD6EPBnFUZW5uaXNH+g1xMTYsInNldEwPDHwPFjekDwLRCQSUDwYYABEyOQnBY29tcGxldGVkU2V0WAAPnA8OBBYQL2V0LwANArcRBVoQlSI6IlNldCAyIkQAAsgAAswPJzQiMwYfMw4EBAEqACwxNvcPKzgxgwgPSANTB7ACD0gDABI4rwIPRwMTCkwAAWYDCK8CA5MDD/sCEyk3MkgDDPsCHzkSCQoM/AIqMTXOCA/fFQcP3gcUAaAUGDWBCHgyNDU2MDM38AAYOKMEAh8ABoQFPzEuOGUFCg2hFCkxNdYJD6MWCA/EABN3Mjg4Mjc0M3cIejg4MzU0NDKSCQaCBAQfAAiWCA+rDgsNxAAqODGIAQ+EBP9/KjIyoQFnMDc1NzE41AQPzwktHzHPCQ06NTY3RgYCihgDshUDCBkPBBcCHzEIGQYFvQkFzwkE4AkPzgkKD7YVBQ8IGQcqODNqE1g0NDM0Mg4LDwsJHAIrBRc4TxICBwgpNjdUCA/pDAoqMjmvCSk0OWcGaDYzODgxMXEKD+oMG4c3ODA2NzkzNHEKhjY4Njc2MjU1oAwWM0YEAx0AJTIzrQk1MzAw6wUDHgAWM98AHTMdABYyHQA2Mi45JwYDPAAXNFEOBioUAx0AFjE8AC0xNVoAFjO+BQ+yAAAGmQkuMjWzABYx7gAnMTKbGgN5ABY1XwsdNQ0BFjM8AAfVEAM6ABY0lQA8Ni45KgEWMY4FHzU3FAlQOjN9fV0AAAAA"

parsed_json = decode_danae_message(payload)
print(json.dumps(parsed_json, indent=2))
```


In short intervals, Betano sends a `GET` request to this generic endpoint:
```
{DictionaryId}?isInit=false&includeVirtuals=true
```
where decoded IDs are mapped to human-readable strings for the frontend.

**Example Reference Dictionary Endpoint:**
```
full url: https://www.betano.ca/danae-webapi/api/live/overview/261930000153980?isInit=false&includeVirtuals=true
261850000136228?isInit=false&includeVirtuals=true
```

To fetch the url needed to redirect a user to the appropriate market, get the eventId of an outcome
which maps to an object containing a pre-built url as one of its attributes within the reference dictionary.

**Variables:**
- `DictionaryId`: An integer identifier for every unique request to fetch a new reference dictionary.
- `eventId`: An identifier for a unique event.

### Building the Betano Scraper

Developing a robust live-odds scraper for Betano involves dealing with a compressed data pipeline wrapped inside a SignalR WebSocket connection. Here is the step-by-step breakdown of how to build it bug-free:

#### 1. Passive CDP Interception
To avoid Betano's active bot detection, you must intercept data through Chrome's remote debugging protocol (CDP). Target the `Network.webSocketFrameReceived` events to passively intercept WebSocket traffic without executing any JavaScript injections. 

#### 2. SignalR and the `\x1e` Terminator (CRITICAL)
Betano's WebSocket data runs on SignalR. This introduces a critical parsing gotcha:
- SignalR frames are appended with the ASCII Record Separator character `\x1e` (e.g. `{"type":1,...}\x1e`).
- Running a raw `json.loads()` on this string will throw an `Extra data` JSONDecodeError. 
- **The Fix:** You must split the payload string by `\x1e` and iterate over the fragments before parsing them into JSON.
- **Filtering:** SignalR will also send random keep-alive handshake packets (like `{"type":3,"invocationId":"29","result":null}`). Safely ignore these by ensuring the string contains `"NewLiveOverviewDiffs"` before attempting to parse it.

#### 3. Decoding the Compressed Payload
Once you isolate a `NewLiveOverviewDiffs` message and parse it into a JSON object, the actual odds payload is buried inside the `arguments` array.
- Extract the string from `arguments[0]`.
- Decode it from **Base64** into raw bytes.
- Decompress the bytes using the **LZ4** frame compression algorithm.
- Decode the resulting bytes back into a UTF-8 string and parse it as JSON. 

#### 4. The Live Odds Data Model
The uncompressed Betano payload gracefully handles both standard price changes and handicap line movements without requiring heuristic matching:
- **Static Handicaps (`selectionChanges`):** When only the odds change, the payload provides a `selectionChanges` map (`marketId -> [selection objects]`). Use your Reference Dictionary to resolve these IDs to human-readable names.
- **Dynamic Handicaps (`market`):** Unlike DraftKings, when a handicap line moves, Betano creates a brand new market and sends the *entire* market block (including all names, shortnames, new selection IDs, and prices) directly in the `payload['market']` field. You simply parse this block and immediately inject the new market and its selections into your local Reference Dictionary state so future price changes can be resolved.

---

## Caesars

**Deeplink Schema:**
```
https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds={selectionIds}
for example:
https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds=9dc72c90-b2e2-3194-8265-8a9f65905e09
```

**Data Flow:**
Caesars establishes a websocket connection using DiffusionData's servers to send delta messages containing live odds data to the frontend. It first establishes a connection to 4 separate:
```
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/livescores/diffusion?ty=WB&v=25&ca=10&r=0
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/cashout/diffusion?ty=WB&v=25&ca=10&r=0
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/microbetting/diffusion?ty=WB&v=25&ca=10&r=0
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/diffusion?ty=WB&v=25&ca=10&r=0
```
which each one handles live data of different topics (e.g. live odds data, live score updates and etc).

The primary websocket that sends live odds changes to markets is:
```
wss://api.americanwagering.com/regions/ca/locations/on/brands/czr/diffusion?ty=WB&v=25&ca=10&r=0
```
We are not concerned with the other 3 websockets, unless the data from them becomes useful for future development.


**Example Base64-Encoded String:**
```
BQClXf0AGLZBNBi3GHpGMTAuNTI4GQE3ElRyckFsZXNzYW5kcmEgTWF6em9sYRkBWRgo
```

Additionally, Caesar's makes a GET request to fetch a json file containing the initial state of each market and important information for each market:
```
https://api.americanwagering.com/regions/ca/locations/on/brands/czr/sb/v4/home
```


**Variables:**
- `selectionId`: An integer identifier for every unique selection

# Caesars Sportsbook Odds Scraper: Findings & Implementation Plan

## 1. Core Architecture
The scraper connects to the live Caesars Sportsbook website via Chrome DevTools Protocol (CDP) using `websocket-client`. Instead of constantly refreshing or polling API endpoints (which flags bot protection), the scraper passively listens to the incoming WebSocket traffic between the browser and Caesars' backend servers.

### State Initialization (`/v4/home` & `/v4/events`)
- When the page first loads, Caesars sends a massive JSON blob containing the current state of all live matches, markets, and selections.
- The scraper intercepts this `responseReceived` event, issues a `getResponseBody` command via CDP, and flattens the nested JSON hierarchy into an O(1) `id_map`.
- This `id_map` links every Selection ID to its parent Market and Event, which is required because live odds updates only contain the Selection ID.

## 2. Diffusion Protocol & Binary Payloads
Caesars uses a proprietary, binary-compressed WebSocket protocol called **Diffusion**. The payload data is base64 encoded by CDP, and once decoded, the first byte dictates the message type.

### Type 4 (Topic Initialization)
- **Purpose:** Binds a short binary "Topic Alias" to a full string `obj_id` (Selection ID).
- **Structure:** `[MsgType=4] [Topic Alias (VarInt)] [CBOR Payload]`
- **Extraction:** The payload contains a CBOR map with an `id` field. We read this to populate our `alias_map`, associating the short binary alias with the full selection ID.

### Type 5 (Delta Updates)
- **Purpose:** Broadcasts live price/odds updates for previously initialized topics.
- **Structure:** `[MsgType=5] [Topic Alias (VarInt)] [Opcode] [Delta Payload]`
- **Extraction:** The payload uses CBOR Object Deltas (a dict) or JSON Patch-style operations (a list). We look up the alias in our `alias_map` to figure out which selection is updating, then parse the CBOR to extract the new price (`a` for American odds, `d` for decimal).

## 3. Key Findings & Critical Fixes

During the development and debugging of the scraper, we encountered seemingly incorrect odds (e.g., +800 for run lines, +1650 for money lines when the UI showed different numbers). We discovered two massive pitfalls in the data structure:

### A. Alias Map Contamination Across Refreshes
**The Problem:** Diffusion dynamically assigns integer IDs (aliases) to topics sequentially (e.g. topic 1 -> alias 1). When the page is refreshed to avoid bot timeouts, a new WebSocket session begins and the backend starts recycling aliases (e.g., alias 13783 might now point to a Golf market instead of a Baseball run line). Because `alias_map` wasn't cleared, the script applied Golf odds to Baseball markets.
**The Fix:** We must explicitly call `alias_map.clear()` whenever a new base state is loaded from `/v4/home`.

### B. Misinterpreting `cashoutPrice` as `price`
**The Problem:** Using raw regex (like `re.search(r'\d+/\d+', bytes)`) on the binary delta payloads is extremely dangerous. Caesars continuously sends updates for `cashoutPrice` for active tickets, which notoriously have terrible odds (like +800 or +1650). The regex was blindly capturing the fractional odds inside a `cashoutPrice` update or even scores/metadata, assuming it was the main market odds.
**The Fix:** Deltas must be fully parsed using `cbor2.load()`. We must actively traverse the returned list/dict to check if the path being modified is specifically `"/price"`, explicitly filtering out updates to `"/cashoutPrice"` or `"/previousPrice"`.

## 4. Implementation Plan for Production

To finalize this scraper into a production-ready arbitrage service, follow these implementation steps:

1. **Robust VLQ VarInt Parsing:**
   Replace raw byte string-matching with a standard VLQ integer reader to perfectly slice out the Topic Alias from Type 4 and Type 5 messages, ensuring no CBOR tags are accidentally swallowed.
2. **State Management Hooks:**
   Ensure `is_state_loaded` flips to `False` and dictionaries are wiped on page reloads to prevent cross-session contamination.
3. **Structured CBOR traversal:**
   Fully ditch byte-level Regex. Parse Type 5 messages properly and iterate through JSON Patch ops (`if op['path'] == '/price'`) or CBOR deltas to extract the exact price nodes safely.
4. **Market Line Handicaps:**
   Since markets like "Run Line" or "Total Runs" share the exact same string name (e.g., `|Run Line Live|`) as their alternate counterparts, the `market.get('line')` attribute must always be paired with the odds to accurately identify which handicap the odds belong to.