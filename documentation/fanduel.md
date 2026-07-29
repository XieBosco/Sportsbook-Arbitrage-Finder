# FanDuel Sportsbook Odds Scraper

## Overview
FanDuel does not stream live odds over a persistent WebSocket connection like most other sportsbooks. Instead, it relies long-polling. It continuously sends HTTP GET requests to endpoints like https://ips.sportsbook.fanduel.ca/inplayservice/v1.0/livedata?channel=WEB&dataEntries=FULL_DETAILS%… and https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1 every few seconds to fetch the latest data. The data is returned as a HTTP `POST` requests payload to update the frontend. Extracting live data requires intercepting these HTTP responses.

## Deeplink Schema
To construct a URL that automatically adds a bet to the user's betslip:
```
https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]={marketId}&selectionId[0]={selectionId}
```

### Variables
- `marketId`: A unique identifier for a specific betting market.
- `selectionId`: A unique identifier for a specific selection/runner within that market.

## Data Architecture & Flow

### 1. The Reference Dictionary (State Initialization)
When the FanDuel page first loads, the client requests a massive reference dictionary. This dictionary maps arbitrary IDs to plain English names for events, markets, and selections.
**Endpoint:**
```
https://sbapi.on.sportsbook.fanduel.ca/api/content-managed-page?page=CUSTOM&...
```
This allows the frontend to translate incoming odds updates.

### 2. Live Odds Updates
In short intervals, the client sends `POST` requests to the web servers to fetch the latest prices.
**Endpoint:**
```
https://smp.on.sportsbook.fanduel.ca/api/sports/fixedodds/readonly/v1/getMarketPrices?priceHistory=1
```
The response contains the `marketId`, `selectionId`, and the new odds data, which must be cross-referenced with the reference dictionary to resolve plain English names.

## Implementation Guide (Building the Scraper)

Developing a bug-free scraper for FanDuel requires strict adherence to the following steps:

### 1. Passive CDP Interception
To extract live odds without triggering FanDuel's headless browser detection, attach to a standard Chrome session using the Chrome DevTools Protocol (CDP). Since the data is transmitted via HTTP rather than WebSockets, you must monitor the `Network.responseReceived` events.

> **CRITICAL GOTCHA:** CDP does not automatically attach response bodies to the `responseReceived` event. Once you detect the target URL (e.g., `content-managed-page` or `getMarketPrices`), you must immediately dispatch a `Network.getResponseBody` command containing the `requestId` to pull the actual JSON payload.

### 2. Intercepting and Storing the Reference Dictionary
1. Intercept the URL containing `content-managed-page`.
2. Extract the `events` (games), `markets` (types of bets), and `selections` (runners/teams) from the `attachments` JSON block.
3. Store these in memory (e.g., Python dictionaries) to translate incoming odds updates.

### 3. Deeply Nested JSON & Recursive Searching (CRITICAL)
When intercepting odds updates, look for URLs containing `getMarketPrices`. The returned JSON structure is heavily nested and subject to change without warning.

> **IMPORTANT:** Do NOT hardcode array indexes or dictionary keys to find the odds.
Instead, implement a recursive JSON traversal function that scans the entire payload for any object containing both the `"marketId"` and `"runnerDetails"` keys. This guarantees bug-free extraction even if FanDuel shifts their payload hierarchy in the future.

### 4. Extracting American Odds
Once you locate a `runnerDetails` object, extracting the odds requires defensive parsing, as the location can shift between formats depending on the market type:
- First, attempt to extract from: `runner.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")`
- If it returns `None`, fallback to: `runner.get("winRunnerOdds", {}).get("trueOdds", {}).get("americanOdds")`
