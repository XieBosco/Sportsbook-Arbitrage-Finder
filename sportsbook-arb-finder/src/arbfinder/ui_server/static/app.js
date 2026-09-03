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

    function buildCard(opp) {
        const card = document.createElement("div");
        card.className = "opportunity-card";
        card.id = "card-" + css_safe(marketKey(opp));

        // Format line display
        const linePart = opp.line !== null ? ` ${opp.line > 0 ? "+" : ""}${opp.line}` : "";
        const marketDisplay = opp.market_type.replace(/_/g, " ") + linePart;

        card.innerHTML = `
            <div class="card-header">
                <div>
                    <div class="card-game">${esc(opp.home_team)} vs ${esc(opp.away_team)}</div>
                    <div class="card-meta">
                        <span class="tag tag-sport">${esc(opp.sport_key)} / ${esc(opp.league_key)}</span>
                        <span class="tag tag-market">${esc(marketDisplay)}</span>
                    </div>
                </div>
                <div class="card-margin">
                    <div class="margin-value">${opp.margin_pct.toFixed(2)}%</div>
                    <div class="margin-label">margin</div>
                </div>
            </div>
            <table class="legs-table">
                <thead>
                    <tr>
                        <th>Book</th>
                        <th>Selection</th>
                        <th>Odds</th>
                        <th>Stake</th>
                    </tr>
                </thead>
                <tbody>
                    ${opp.legs.map(leg => `
                    <tr>
                        <td>${esc(leg.book_id)}</td>
                        <td>${esc(leg.selection)}</td>
                        <td class="col-odds">${esc(leg.odds_formatted)}</td>
                        <td class="col-stake">$${leg.stake.toFixed(2)}</td>
                    </tr>`).join("")}
                </tbody>
            </table>
            <div class="card-footer">
                <span>Detected ${formatTime(opp.detected_at)}</span>
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

    function updateCounter() {
        oppCount.textContent = `${cardMap.size} opportunit${cardMap.size === 1 ? "y" : "ies"}`;
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

    settingsBtn.addEventListener("click", async () => {
        const data = await fetchConfig();
        if (data) {
            // Populate form
            settingsForm.arb_min_profit_percentage.value = data.arbitrage.min_profit_percentage;
            settingsForm.arb_total_bet_amount.value = data.arbitrage.total_bet_amount;
            settingsForm.arb_unit_size.value = data.arbitrage.unit_size;
            settingsForm.arb_stake_calculating_method.value = data.arbitrage.stake_calculating_method;
            settingsForm.arb_mainlines_only.checked = data.arbitrage.mainlines_only;
            settingsForm.arb_kelly_bankroll.value = data.arbitrage.kelly_bankroll;
            settingsForm.arb_kelly_multiplier.value = data.arbitrage.kelly_multiplier;

            settingsForm.scan_min_margin.value = data.scanner.min_margin;
            settingsForm.scan_max_odds_age_seconds.value = data.scanner.max_odds_age_seconds;
            settingsForm.scan_min_legs_required.value = data.scanner.min_legs_required;
            settingsForm.scan_excluded_books.value = data.scanner.excluded_books.join(", ");
            settingsForm.scan_excluded_markets.value = data.scanner.excluded_markets.join(", ");

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
                min_profit_percentage: parseFloat(settingsForm.arb_min_profit_percentage.value),
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
                excluded_books: settingsForm.scan_excluded_books.value.split(",").map(s => s.trim()).filter(Boolean),
                excluded_markets: settingsForm.scan_excluded_markets.value.split(",").map(s => s.trim()).filter(Boolean),
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
    // Init
    // ==================================================================
    fetchConfig().then(() => {
        connect();
        setInterval(evictExpired, 5000); // Check for expired arbs every 5 seconds
    });
})();
