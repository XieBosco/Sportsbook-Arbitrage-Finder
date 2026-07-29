# BetMGM Sportsbook Odds Scraper

## Overview
BetMGM utilizes a SignalR WebSocket connection to stream live odds data directly to the frontend. The payload is sent as plain JSON strings, containing both primary market updates and secondary prop market updates. 

## Deeplink Schema
To construct a URL that automatically adds a bet to the user's betslip:
**Preferred Schema:**
```
https://www.on.betmgm.ca/en/sports?options={fixtureId}-{optionMarketId}-{optionId}
```
*Alternative Schemas:*
```
https://www.on.betmgm.ca/en/sports/events/argentina-egypt-2:7828823?options=2:7828823-201196265-762963230&type=Single
https://www.on.betmgm.ca/en/sports?options=2:7716083-190814890-698929676
```

### Variables
- `fixtureId`: A unique identifier for a game/event (e.g., `19766272` or `2:7831170`).
- `optionMarketId`: A unique identifier for a market.
- `optionId`: A unique identifier for a selection within a market.

## Data Architecture & Flow

### 1. The Reference Dictionary (State Initialization)
In frequent intervals, BetMGM sends an HTTP `GET` request to retrieve a JSON reference dictionary mapping `fixtureId`s to metadata (e.g., the actual names of the teams). 
**Endpoint:**
```
https://www.betmgm.ca/cds-api/bettingoffer/fixture-view?x-bwin-accessid=...&fixtureIds=...
```
This is essential because the live WebSocket stream only provides the `fixtureId` and does **not** include the human-readable team names for the event.

### 2. Live Odds Updates (WebSocket)
BetMGM connects to a SignalR endpoint:
```
wss://cds-push.on.betmgm.ca/ws-1-0?lang=en-us&country=CA...
```
Updates are sent as plain JSON payloads.

---

## Implementation Guide (Building the Scraper)

Building a BetMGM scraper requires a dual-interception strategy: catching standard HTTP requests and WebSocket frames simultaneously via CDP.

### 1. Passive CDP Interception
To avoid headless browser detection, attach to a regular Chrome session using CDP (`Network.enable`). You must monitor both `Network.responseReceived` (for the reference dictionary) and `Network.webSocketFrameReceived` (for the live odds).

### 2. Intercepting the Reference Dictionary
BetMGM does not include human-readable game names (like "Indiana Fever at Las Vegas Aces") within the live odds WebSocket payload. 
- To map this ID, intercept HTTP responses (`Network.responseReceived`) where the URL contains `fixture-view`.
- Use the `Network.getResponseBody` CDP command with the corresponding `requestId` to retrieve the JSON payload.
- Extract the `fixtureId` and the human-readable game name, and store this mapping in memory.

### 3. SignalR and the `\x1e` Terminator (CRITICAL)
BetMGM's WebSocket data runs on SignalR. This introduces a major parsing trap:
- SignalR frames are delimited and appended with the ASCII Record Separator character `\x1e` (e.g., `{"type":1,...}\x1e`).
- Running a raw `json.loads()` on the `payloadData` string will throw a `JSONDecodeError` because of the trailing hidden character.
- **The Fix:** You must split the payload string (`payloadData.split('\x1e')`) and iterate over the fragments before parsing them into JSON. *Note: Ensure you split the inner `payloadData` string, NOT the outer CDP JSON wrapper.*

### 4. The Live Odds Data Model
BetMGM sends odds updates via plain JSON. Look for objects inside the `arguments[0]['payload']` array. You must handle two distinct command types:
- **`GameUpdateCommand`**: Updates primary markets. Extract data from `payload['game']` (`id`, `name`) and iterate through `payload['game']['results']` to find `id`, `name`, and `americanOdds`.
- **`OptionMarketUpdateCommand`**: Updates secondary prop markets. Extract data from `payload['optionMarket']` (`id`, `name`) and iterate through `payload['optionMarket']['options']` to find `id`, `name`, and `price.americanOdds`.
