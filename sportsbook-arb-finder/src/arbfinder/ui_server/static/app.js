/* ==========================================================
   Arbitrage Finder — Client-side WebSocket handler
   ========================================================== */

(function () {
    "use strict";

    // ---- Constants ----
    const MAX_DISPLAYED   = 100;
    const BACKOFF_INITIAL = 1000;  // ms
    const BACKOFF_MAX     = 15000; // ms

    // ---- State ----
    /** @type {Map<string, HTMLElement>} market-key → card DOM element */
    const cardMap  = new Map();
    /** @type {Map<string, number>}  market-key → last-updated timestamp (ms) */
    const updateTs = new Map();
    /** @type {Map<string, Object>} market-key → opportunity payload */
    const oppMap   = new Map();

    let ws              = null;
    let backoff         = BACKOFF_INITIAL;
    let reconnectTimer  = null;
    let sortBy          = "timecreated";

    // ---- DOM refs ----
    const statusBadge   = document.getElementById("connection-status");
    const statusText    = document.getElementById("status-text");
    const container     = document.getElementById("opportunities-container");
    const emptyState    = document.getElementById("empty-state");
    const oppCount      = document.getElementById("opp-count");

    // ==================================================================
    // WebSocket lifecycle
    // ==================================================================

    function connect() {
        const proto = location.protocol === "https:" ? "wss:" : "ws:";
        ws = new WebSocket(`${proto}//${location.host}/ws/opportunities`);

        ws.addEventListener("open", onOpen);
        ws.addEventListener("message", onMessage);
        ws.addEventListener("close", onClose);
        ws.addEventListener("error", onError);
    }

    function onOpen() {
        setStatus("connected", "Connected");
        backoff = BACKOFF_INITIAL;

        // Mark existing cards as stale until fresh data arrives
        for (const card of cardMap.values()) {
            card.classList.add("stale");
        }
    }

    function onMessage(event) {
        let msg;
        try {
            msg = JSON.parse(event.data);
        } catch (_) {
            return;
        }

        // Route by message type — extensible for future additions
        switch (msg.type) {
            case "opportunity":
                handleOpportunity(msg.data);
                break;
            case "opportunity_closed":
                handleOpportunityClosed(msg.data);
                break;
            default:
                // Unknown type — ignore silently
                break;
        }
    }

    function onClose() {
        setStatus("disconnected", "Disconnected");
        scheduleReconnect();
    }

    function onError() {
        // The browser will also fire "close" after "error", which
        // triggers reconnect — no action needed here beyond status.
        setStatus("disconnected", "Disconnected");
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        setStatus("reconnecting", `Reconnecting in ${(backoff / 1000).toFixed(0)}s…`);
        reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            backoff = Math.min(backoff * 2, BACKOFF_MAX);
            connect();
        }, backoff);
    }

    // ==================================================================
    // Status indicator
    // ==================================================================

    function setStatus(state, text) {
        statusBadge.className = "status-badge " + state;
        statusText.textContent = text;
    }

    // ==================================================================
    // Opportunity rendering
    // ==================================================================

    /**
     * Build a stable grouping key from an opportunity payload.
     * Uses canonical_game_id + market_type + line so that re-emissions
     * for the same still-open arb update in place.
     */
    function marketKey(opp) {
        return `${opp.canonical_game_id}|${opp.market_type}|${opp.line ?? "null"}`;
    }

    function handleOpportunity(opp) {
        const key  = marketKey(opp);
        const now  = Date.now();

        // Hide empty state on first card
        if (emptyState) {
            emptyState.style.display = "none";
        }

        // Update or create card
        let card = cardMap.get(key);
        if (card) {
            // Update existing card in place
            const newCard = buildCard(opp);
            card.replaceWith(newCard);
            cardMap.set(key, newCard);
        } else {
            card = buildCard(opp);
            container.appendChild(card);
            cardMap.set(key, card);
        }
        oppMap.set(key, opp);
        updateTs.set(key, now);

        sortContainer();

        // Enforce cap — evict oldest-updated entries
        if (cardMap.size > MAX_DISPLAYED) {
            evictOldest();
        }

        updateCounter();
    }

    function handleOpportunityClosed(oppData) {
        const key = marketKey(oppData);
        const card = cardMap.get(key);
        if (card) {
            card.remove();
            cardMap.delete(key);
            oppMap.delete(key);
            updateTs.delete(key);
            updateCounter();
        }
    }

    // ==================================================================
    // Team Logo Assets & Helpers
    // ==================================================================

    /**
     * Team logo lookup mapping loaded from external team_logos.js / team_logos.json.
     */
    let teamLogosMap = window.MLB_TEAM_LOGOS || {};

    // Fallback async fetch for team_logos.json if window.MLB_TEAM_LOGOS is not populated
    if (Object.keys(teamLogosMap).length === 0) {
        fetch("/static/team_logos.json")
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data) {
                    teamLogosMap = data;
                }
            })
            .catch(() => {});
    }

    /**
     * Resolve the logo image URL for a given team and league.
     * Returns null if no logo is available.
     */
    function getTeamLogoUrl(teamName, leagueKey) {
        if (!teamName) return null;
        const clean = String(teamName).toLowerCase().trim();
        const map = teamLogosMap || window.MLB_TEAM_LOGOS || {};

        // Direct key match
        if (map[clean]) {
            return `/static/mlb_team_logos/${map[clean]}`;
        }

        // Match if clean name ends with a known key (e.g. "ARI Diamondbacks" -> ends with "diamondbacks")
        for (const [key, filename] of Object.entries(map)) {
            if (clean.endsWith(` ${key}`) || clean.endsWith(key)) {
                return `/static/mlb_team_logos/${filename}`;
            }
        }

        return null;
    }

    /**
     * Render a team name with its optional team icon.
     * @param {string} teamName
     * @param {string} leagueKey
     * @param {"left"|"right"} [logoPosition="left"] - Place logo before or after the team name
     */
    function renderTeamBadge(teamName, leagueKey, logoPosition = "left") {
        const logoUrl = getTeamLogoUrl(teamName, leagueKey);
        const nameEsc = esc(teamName);
        if (!logoUrl) {
            return `<span class="team-badge"><span class="team-name">${nameEsc}</span></span>`;
        }

        const imgTag = `<img class="team-logo" src="${logoUrl}" alt="${nameEsc}" onerror="this.style.display='none'">`;
        const nameTag = `<span class="team-name">${nameEsc}</span>`;

        if (logoPosition === "right") {
            return `<span class="team-badge team-badge-right">${nameTag}${imgTag}</span>`;
        }
        return `<span class="team-badge team-badge-left">${imgTag}${nameTag}</span>`;
    }

    /**
     * Render the Selection column cell in the legs table.
     * Enriches "home" or "away" with team logos and labels.
     */
    function renderSelectionCell(selection, opp) {
        const sLower = String(selection).toLowerCase();
        let targetTeam = null;
        let suffix = "";

        if (sLower === "home") {
            targetTeam = opp.home_team;
            suffix = ` <span class="selection-team-sub">(${esc(opp.home_team)})</span>`;
        } else if (sLower === "away") {
            targetTeam = opp.away_team;
            suffix = ` <span class="selection-team-sub">(${esc(opp.away_team)})</span>`;
        } else {
            targetTeam = selection;
        }

        const logoUrl = getTeamLogoUrl(targetTeam, opp.league_key);
        if (logoUrl) {
            return `<div class="selection-info"><img class="selection-logo" src="${logoUrl}" alt="${esc(targetTeam)}" onerror="this.style.display='none'"><span>${esc(selection)}</span>${suffix}</div>`;
        }
        return `<span>${esc(selection)}</span>${suffix}`;
    }

    // ==================================================================
    // Deeplinks & Dual Bet Widget
    // ==================================================================

    /**
     * Resolve or build a direct clickable deeplink for a sportsbook leg
     * adhering to documentation schemas for DraftKings, FanDuel, BetMGM, Caesars, Betano.
     */
    function getLegDeeplink(leg, opp) {
        if (!leg) return "#";
        if (leg.deeplink && typeof leg.deeplink === "string" && leg.deeplink.startsWith("http")) {
            return leg.deeplink;
        }

        const book = String(leg.book_id || "").toLowerCase().trim();
        const home = (opp && opp.home_team) || "";
        const away = (opp && opp.away_team) || "";
        const homeSlug = home.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        const awaySlug = away.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        const matchSlug = (awaySlug && homeSlug) ? `${awaySlug}-vs-${homeSlug}` : "match";

        const selId = leg.selection_id || leg.raw_selection_id || "";
        const mId = leg.market_id || leg.raw_market_id || "";
        const evId = leg.event_id || leg.raw_event_id || (opp && opp.canonical_game_id) || "";

        // 1. DraftKings (documentation/draftkings.md)
        if (book.includes("draftkings")) {
            if (selId) {
                return evId
                    ? `https://sportsbook.draftkings.com/event/${encodeURIComponent(evId)}?outcomes=${encodeURIComponent(selId)}`
                    : `https://sportsbook.draftkings.com/?outcomes=${encodeURIComponent(selId)}`;
            }
            if (evId) return `https://sportsbook.draftkings.com/event/${encodeURIComponent(matchSlug)}/${encodeURIComponent(evId)}`;
            return "https://sportsbook.draftkings.com/";
        }

        // 2. FanDuel (documentation/fanduel.md)
        if (book.includes("fanduel")) {
            if (mId && selId) {
                return `https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]=${encodeURIComponent(mId)}&selectionId[0]=${encodeURIComponent(selId)}`;
            }
            if (selId) {
                return `https://on.sportsbook.fanduel.ca/addToBetslip?selectionId[0]=${encodeURIComponent(selId)}`;
            }
            if (evId) return `https://on.sportsbook.fanduel.ca/sports/event/${encodeURIComponent(evId)}`;
            return "https://on.sportsbook.fanduel.ca/";
        }

        // 3. BetMGM (documentation/betmgm.md)
        if (book.includes("betmgm")) {
            if (evId && mId && selId) {
                return `https://www.on.betmgm.ca/en/sports?options=${encodeURIComponent(evId)}-${encodeURIComponent(mId)}-${encodeURIComponent(selId)}`;
            }
            if (selId) {
                return `https://www.on.betmgm.ca/en/sports?options=${encodeURIComponent(selId)}`;
            }
            if (evId) return `https://www.on.betmgm.ca/en/sports/events/${encodeURIComponent(matchSlug)}-${encodeURIComponent(evId)}`;
            return "https://www.on.betmgm.ca/en/sports";
        }

        // 4. Caesars (documentation/caesars.md)
        if (book.includes("caesars") || book.includes("czr")) {
            if (selId) {
                return `https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds=${encodeURIComponent(selId)}`;
            }
            if (evId) return `https://sportsbook.caesars.com/ca/on/bet/event/${encodeURIComponent(evId)}`;
            return "https://sportsbook.caesars.com/ca/on/bet";
        }

        // 5. Betano (documentation/betano.md)
        if (book.includes("betano")) {
            if (evId) {
                return `https://www.betano.ca/live/${encodeURIComponent(matchSlug)}/${encodeURIComponent(evId)}/`;
            }
            return "https://www.betano.ca/";
        }

        return "#";
    }

    /**
     * Render the dual-bet action box with top/bottom sportsbook links
     * and center DUAL button opening both in one click.
     */
    function renderDualBetWidget(opp) {
        if (!opp.legs || opp.legs.length === 0) return "";
        const leg1 = opp.legs[0];
        const leg2 = opp.legs.length > 1 ? opp.legs[1] : null;
        const link1 = getLegDeeplink(leg1, opp);
        const link2 = leg2 ? getLegDeeplink(leg2, opp) : "#";

        return `
            <div class="dual-bet-box">
                <a class="bet-btn-side" href="${esc(link1)}" target="_blank" rel="noopener noreferrer" title="Open ${esc(leg1.book_id)} deeplink">${esc(leg1.book_id)}</a>
                <button type="button" class="dual-bet-btn" data-link1="${esc(link1)}" data-link2="${esc(link2)}" title="Open both sportsbooks">
                    <span>DUAL</span>
                    <svg class="dual-arrow-icon" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>
                </button>
                ${leg2 ? `<a class="bet-btn-side" href="${esc(link2)}" target="_blank" rel="noopener noreferrer" title="Open ${esc(leg2.book_id)} deeplink">${esc(leg2.book_id)}</a>` : ""}
            </div>
        `;
    }

    function buildCard(opp) {
        const card = document.createElement("div");
        card.className = "opportunity-card";
        card.id = "card-" + css_safe(marketKey(opp));

        // Format line display
        const linePart = opp.line !== null ? ` ${opp.line > 0 ? "+" : ""}${opp.line}` : "";
        const marketDisplay = opp.market_type.replace(/_/g, " ") + linePart;
        const gameTimeFormatted = formatGameStartTime(opp.start_time);

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <div class="card-game">
                        ${renderTeamBadge(opp.home_team, opp.league_key, "left")}
                        <span class="game-vs">vs</span>
                        ${renderTeamBadge(opp.away_team, opp.league_key, "right")}
                    </div>
                    <div class="card-meta">
                        <span class="tag tag-sport">${esc(opp.sport_key)} / ${esc(opp.league_key)}</span>
                        <span class="tag tag-market">${esc(marketDisplay)}</span>
                    </div>
                </div>
                <div class="card-header-right">
                    <div class="card-margin">
                        <div class="margin-value">${opp.margin_pct.toFixed(2)}%</div>
                        <div class="margin-label">margin</div>
                    </div>
                </div>
            </div>
            <table class="legs-table">
                <thead>
                    <tr>
                        <th>Book</th>
                        <th>Selection</th>
                        <th class="col-dual-th"></th>
                        <th>Odds</th>
                        <th>Stake</th>
                    </tr>
                </thead>
                <tbody>
                    ${opp.legs.map((leg, idx) => {
                        const legLink = getLegDeeplink(leg, opp);
                        const dualCell = idx === 0 && opp.legs.length > 0
                            ? `<td rowspan="${opp.legs.length}" class="col-dual-cell">${renderDualBetWidget(opp)}</td>`
                            : "";
                        return `
                        <tr>
                            <td>
                                <a class="book-row-link" href="${esc(legLink)}" target="_blank" rel="noopener noreferrer" title="Open ${esc(leg.book_id)} deeplink">
                                    <div class="book-info">
                                        <img class="book-logo" src="/assets/images/${leg.book_id.toLowerCase()}.png" alt="${esc(leg.book_id)}" onerror="this.style.display='none'">
                                        <span>${esc(leg.book_id)}</span>
                                    </div>
                                </a>
                            </td>
                            <td>${renderSelectionCell(leg.selection, opp)}</td>
                            ${dualCell}
                            <td class="col-odds">${esc(leg.odds_formatted)}</td>
                            <td class="col-stake">$${leg.stake.toFixed(2)}</td>
                        </tr>`;
                    }).join("")}
                </tbody>
            </table>
            <div class="card-footer">
                <div class="card-footer-left">
                    ${gameTimeFormatted ? `<span class="game-time">${esc(gameTimeFormatted)}</span>` : ""}
                </div>
                <div class="card-footer-right">
                    <span>Detected ${formatTime(opp.detected_at)}</span>
                </div>
            </div>
        `;
        return card;
    }

    // ==================================================================
    // Eviction
    // ==================================================================

    function evictOldest() {
        // Sort keys by update timestamp ascending
        const sorted = [...updateTs.entries()].sort((a, b) => a[1] - b[1]);
        while (cardMap.size > MAX_DISPLAYED && sorted.length) {
            const [key] = sorted.shift();
            const card = cardMap.get(key);
            if (card) card.remove();
            cardMap.delete(key);
            oppMap.delete(key);
            updateTs.delete(key);
        }
    }

    function evictExpired() {
        const now = Date.now();
        for (const [key, opp] of oppMap.entries()) {
            const ts = updateTs.get(key) || 0;
            // expires_hint_seconds defaults to 60.0, we add a small buffer (5s) for network latency
            const maxAgeMs = (opp.expires_hint_seconds + 5) * 1000;
            if (now - ts > maxAgeMs) {
                const card = cardMap.get(key);
                if (card) {
                    card.remove();
                    cardMap.delete(key);
                    oppMap.delete(key);
                    updateTs.delete(key);
                }
            }
        }
        updateCounter();
    }

    // ==================================================================
    // Helpers
    // ==================================================================

    function esc(str) {
        const el = document.createElement("span");
        el.textContent = str;
        return el.innerHTML;
    }

    function css_safe(str) {
        return str.replace(/[^a-zA-Z0-9_-]/g, "_");
    }

    function formatTime(isoStr) {
        try {
            const d = new Date(isoStr);
            return d.toLocaleTimeString();
        } catch (_) {
            return isoStr;
        }
    }

    /**
     * Format game start time to match the required format:
     * e.g. "Tue, Jan 23 : 10:00 PM"
     */
    function formatGameStartTime(isoStr) {
        if (!isoStr) return "";
        try {
            const d = new Date(isoStr);
            if (isNaN(d.getTime())) return "";

            const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
            const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

            const dayName = days[d.getDay()];
            const monthName = months[d.getMonth()];
            const dayNum = d.getDate();

            let hours = d.getHours();
            const minutes = String(d.getMinutes()).padStart(2, "0");
            const ampm = hours >= 12 ? "PM" : "AM";
            hours = hours % 12;
            hours = hours ? hours : 12;

            return `${dayName}, ${monthName} ${dayNum} : ${hours}:${minutes} ${ampm}`;
        } catch (_) {
            return "";
        }
    }

    function updateCounter() {
        oppCount.textContent = `${cardMap.size} opportunit${cardMap.size === 1 ? "y" : "ies"}`;
        if (emptyState) {
            emptyState.style.display = cardMap.size === 0 ? "flex" : "none";
        }
    }

    function sortContainer() {
        const entries = [...oppMap.entries()];
        entries.sort((a, b) => {
            const oppA = a[1];
            const oppB = b[1];
            
            if (sortBy === "margin") {
                return oppB.margin_pct - oppA.margin_pct;
            } else {
                const timeA = new Date(oppA.detected_at).getTime();
                const timeB = new Date(oppB.detected_at).getTime();
                return timeA - timeB;
            }
        });

        for (const [key] of entries) {
            const card = cardMap.get(key);
            if (card) {
                container.appendChild(card);
            }
        }
    }

    async function fetchConfig() {
        try {
            const res = await fetch("/api/settings");
            const data = await res.json();
            if (data.ui_sort_by) {
                sortBy = data.ui_sort_by;
            }
            return data;
        } catch (e) {
            console.error("Failed to fetch settings", e);
            return null;
        }
    }

    // ==================================================================
    // Settings Modal
    // ==================================================================
    const settingsBtn = document.getElementById("settings-btn");
    const settingsModal = document.getElementById("settings-modal");
    const settingsForm = document.getElementById("settings-form");
    const settingsCancel = document.getElementById("settings-cancel");

    // Custom Dropdown Logic
    function updateMultiSelectHeader(headerId, count, itemType) {
        const header = document.getElementById(headerId);
        if (count === 0) {
            header.textContent = `Select ${itemType}...`;
        } else {
            header.textContent = `${count} ${itemType} excluded`;
        }
    }

    document.querySelectorAll('.multi-select-header').forEach(header => {
        header.addEventListener('click', (e) => {
            const parent = header.closest('.multi-select');
            const wasOpen = parent.classList.contains('open');
            document.querySelectorAll('.multi-select').forEach(ms => ms.classList.remove('open'));
            if (!wasOpen) parent.classList.add('open');
            e.stopPropagation();
        });
    });

    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multi-select')) {
            document.querySelectorAll('.multi-select').forEach(ms => ms.classList.remove('open'));
        }
    });

    document.querySelectorAll('input[name="exclude_book"]').forEach(cb => {
        cb.addEventListener('change', () => {
            const count = document.querySelectorAll('input[name="exclude_book"]:checked').length;
            updateMultiSelectHeader("books-header", count, "books");
        });
    });

    document.querySelectorAll('input[name="exclude_market"]').forEach(cb => {
        cb.addEventListener('change', () => {
            const count = document.querySelectorAll('input[name="exclude_market"]:checked').length;
            updateMultiSelectHeader("markets-header", count, "markets");
        });
    });

    settingsBtn.addEventListener("click", async () => {
        const data = await fetchConfig();
        if (data) {
            // Populate form
            settingsForm.arb_total_bet_amount.value = data.arbitrage.total_bet_amount;
            settingsForm.arb_unit_size.value = data.arbitrage.unit_size;
            settingsForm.arb_stake_calculating_method.value = data.arbitrage.stake_calculating_method;
            settingsForm.arb_mainlines_only.checked = data.arbitrage.mainlines_only;
            settingsForm.arb_kelly_bankroll.value = data.arbitrage.kelly_bankroll;
            settingsForm.arb_kelly_multiplier.value = data.arbitrage.kelly_multiplier;

            settingsForm.scan_min_margin.value = data.scanner.min_margin;
            settingsForm.scan_max_odds_age_seconds.value = data.scanner.max_odds_age_seconds;
            settingsForm.scan_min_legs_required.value = data.scanner.min_legs_required;
            
            const excludedBooks = data.scanner.excluded_books || [];
            document.querySelectorAll('input[name="exclude_book"]').forEach(cb => {
                cb.checked = excludedBooks.includes(cb.value);
            });
            updateMultiSelectHeader("books-header", excludedBooks.length, "books");

            const excludedMarkets = data.scanner.excluded_markets || [];
            document.querySelectorAll('input[name="exclude_market"]').forEach(cb => {
                cb.checked = excludedMarkets.includes(cb.value);
            });
            updateMultiSelectHeader("markets-header", excludedMarkets.length, "markets");

            settingsForm.sinks_odds_format.value = data.sinks.odds_format;
            settingsForm.ui_sort_by.value = data.ui_sort_by;
        }
        settingsModal.showModal();
    });

    settingsCancel.addEventListener("click", () => {
        settingsModal.close();
    });

    settingsForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const payload = {
            arbitrage: {
                total_bet_amount: parseFloat(settingsForm.arb_total_bet_amount.value),
                unit_size: parseFloat(settingsForm.arb_unit_size.value),
                stake_calculating_method: parseInt(settingsForm.arb_stake_calculating_method.value, 10),
                mainlines_only: settingsForm.arb_mainlines_only.checked,
                kelly_bankroll: parseFloat(settingsForm.arb_kelly_bankroll.value),
                kelly_multiplier: parseFloat(settingsForm.arb_kelly_multiplier.value),
            },
            scanner: {
                min_margin: parseFloat(settingsForm.scan_min_margin.value),
                max_odds_age_seconds: parseFloat(settingsForm.scan_max_odds_age_seconds.value),
                min_legs_required: parseInt(settingsForm.scan_min_legs_required.value, 10),
                excluded_books: Array.from(document.querySelectorAll('input[name="exclude_book"]:checked')).map(cb => cb.value),
                excluded_markets: Array.from(document.querySelectorAll('input[name="exclude_market"]:checked')).map(cb => cb.value),
            },
            odds_format: settingsForm.sinks_odds_format.value,
            ui_sort_by: settingsForm.ui_sort_by.value,
        };

        try {
            await fetch("/api/settings", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });
            
            // Update local state and re-render
            sortBy = payload.ui_sort_by;
            sortContainer();
            
            settingsModal.close();
        } catch (err) {
            console.error("Failed to save settings", err);
            alert("Failed to save settings. Check console for details.");
        }
    });

    // ==================================================================
    // Feed Health Interactive Tab & Dropdown
    // ==================================================================
    const feedsTabWrapper = document.getElementById("feeds-tab-wrapper");
    const feedsTabBtn = document.getElementById("feeds-tab-btn");
    const feedsDropdown = document.getElementById("feeds-dropdown");
    const feedsSummaryDot = document.getElementById("feeds-summary-dot");
    const feedsSummaryBadge = document.getElementById("feeds-summary-badge");
    const feedsList = document.getElementById("feeds-list");
    const feedsRefreshTime = document.getElementById("feeds-refresh-time");

    if (feedsTabBtn && feedsDropdown) {
        feedsTabBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = feedsDropdown.classList.toggle("open");
            feedsTabBtn.setAttribute("aria-expanded", String(isOpen));
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (feedsDropdown.classList.contains("open") && feedsTabWrapper && !feedsTabWrapper.contains(e.target)) {
                feedsDropdown.classList.remove("open");
                feedsTabBtn.setAttribute("aria-expanded", "false");
            }
        });

        // Close dropdown on Escape
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && feedsDropdown.classList.contains("open")) {
                feedsDropdown.classList.remove("open");
                feedsTabBtn.setAttribute("aria-expanded", "false");
            }
        });
    }

    async function updateBookHealth() {
        if (!feedsList || !feedsSummaryBadge) return;
        try {
            const res = await fetch("/api/health");
            if (!res.ok) return;
            const data = await res.json();
            const sportsbooks = data.sportsbooks || {};
            const bookNames = Object.keys(sportsbooks).sort();
            
            if (bookNames.length === 0) {
                feedsSummaryBadge.textContent = "0 Feeds";
                feedsSummaryBadge.className = "feeds-badge";
                feedsList.innerHTML = `<div class="muted" style="padding: 8px; text-align: center;">No feeds active</div>`;
                return;
            }

            let liveCount = 0;
            let initCount = 0;
            let offlineCount = 0;

            feedsList.innerHTML = bookNames.map(book => {
                const info = sportsbooks[book];
                let statusClass = "offline";
                let statusBadgeText = "Offline";

                if (info.is_connected && info.is_initialized) {
                    statusClass = "live";
                    statusBadgeText = "Live";
                    liveCount++;
                } else if (info.is_connected) {
                    statusClass = "init";
                    statusBadgeText = "Init";
                    initCount++;
                } else {
                    offlineCount++;
                }

                let timeText = "";
                if (info.last_update_at) {
                    timeText = formatTime(info.last_update_at);
                } else {
                    timeText = "No data";
                }

                return `
                    <div class="feed-item">
                        <div class="feed-item-left">
                            <span class="status-dot" style="background: var(--${statusClass === "live" ? "green" : statusClass === "init" ? "yellow" : "red"}); width: 7px; height: 7px;"></span>
                            <span class="feed-name">${esc(book)}</span>
                        </div>
                        <div class="feed-item-right">
                            <span class="feed-time">${esc(timeText)}</span>
                            <span class="feed-status-badge ${statusClass}">${statusBadgeText}</span>
                        </div>
                    </div>
                `;
            }).join("");

            // Update summary badge & dot
            feedsSummaryBadge.textContent = `${liveCount}/${bookNames.length} Live`;
            if (liveCount === bookNames.length) {
                feedsSummaryBadge.className = "feeds-badge all-live";
                if (feedsSummaryDot) feedsSummaryDot.style.background = "var(--green)";
            } else if (liveCount > 0 || initCount > 0) {
                feedsSummaryBadge.className = "feeds-badge has-warning";
                if (feedsSummaryDot) feedsSummaryDot.style.background = "var(--yellow)";
            } else {
                feedsSummaryBadge.className = "feeds-badge has-offline";
                if (feedsSummaryDot) feedsSummaryDot.style.background = "var(--red)";
            }

            if (feedsRefreshTime) {
                const now = new Date();
                feedsRefreshTime.textContent = `Updated ${now.toLocaleTimeString()}`;
            }
        } catch (_) {
            // Silently ignore health polling errors
        }
    }

    // Open both legs when clicking DUAL button
    document.addEventListener("click", function (e) {
        const btn = e.target.closest(".dual-bet-btn");
        if (!btn) return;
        e.preventDefault();
        e.stopPropagation();

        const l1 = btn.getAttribute("data-link1");
        const l2 = btn.getAttribute("data-link2");
        if (l1 && l1 !== "#") {
            window.open(l1, "_blank", "noopener,noreferrer");
        }
        if (l2 && l2 !== "#") {
            window.open(l2, "_blank", "noopener,noreferrer");
        }
    });

    // ==================================================================
    // Init
    // ==================================================================
    fetchConfig().then(() => {
        connect();
        updateBookHealth();
        setInterval(evictExpired, 5000); // Check for expired arbs every 5 seconds
        setInterval(updateBookHealth, 10000); // Check feed health every 10 seconds
    });
})();
