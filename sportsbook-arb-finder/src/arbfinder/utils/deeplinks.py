"""Sportsbook deeplink generation utilities.

Constructs direct clickable links for selections in each sportsbook
according to the schemas documented in the /documentation folder:
- DraftKings: documentation/draftkings.md
- FanDuel: documentation/fanduel.md
- BetMGM: documentation/betmgm.md
- Caesars: documentation/caesars.md
- Betano: documentation/betano.md
"""

from __future__ import annotations

import re
import urllib.parse

__all__ = ["generate_deeplink"]


def _slugify(text: str) -> str:
    """Generate a clean URL slug from team or event names."""
    if not text:
        return ""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return slug.strip("-")


def generate_deeplink(
    book_id: str,
    selection_id: str = "",
    market_id: str = "",
    event_id: str = "",
    home_team: str = "",
    away_team: str = "",
) -> str:
    """Build a sportsbook deeplink URL.

    Parameters
    ----------
    book_id : str
        The canonical or case-insensitive name of the book (e.g. "DraftKings", "FanDuel").
    selection_id : str
        The book-specific outcome or selection ID (if available).
    market_id : str
        The book-specific market ID (if available).
    event_id : str
        The book-specific event/game/fixture ID (if available).
    home_team : str
        The home team name (used for SEO event slugs).
    away_team : str
        The away team name (used for SEO event slugs).

    Returns
    -------
    str
        The constructed deep-link URL.
    """
    book = str(book_id or "").strip().lower()
    sel_id = str(selection_id or "").strip()
    m_id = str(market_id or "").strip()
    ev_id = str(event_id or "").strip()

    home_slug = _slugify(home_team)
    away_slug = _slugify(away_team)
    match_slug = f"{away_slug}-vs-{home_slug}" if (away_slug and home_slug) else "match"

    # 1. DraftKings (documentation/draftkings.md)
    # Preferred: https://sportsbook.draftkings.com/?outcomes={selectionId}
    # Or: https://sportsbook.draftkings.com/event/{eventId}?outcomes={selectionId}
    if "draftkings" in book:
        if sel_id:
            encoded_sel = urllib.parse.quote(sel_id, safe="")
            if ev_id:
                return f"https://sportsbook.draftkings.com/event/{urllib.parse.quote(ev_id, safe='')}?outcomes={encoded_sel}"
            return f"https://sportsbook.draftkings.com/?outcomes={encoded_sel}"
        if ev_id:
            return f"https://sportsbook.draftkings.com/event/{match_slug}/{urllib.parse.quote(ev_id, safe='')}"
        return "https://sportsbook.draftkings.com/"

    # 2. FanDuel (documentation/fanduel.md)
    # Preferred: https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]={marketId}&selectionId[0]={selectionId}
    if "fanduel" in book:
        if m_id and sel_id:
            encoded_m = urllib.parse.quote(m_id, safe="")
            encoded_sel = urllib.parse.quote(sel_id, safe="")
            return f"https://on.sportsbook.fanduel.ca/addToBetslip?marketId[0]={encoded_m}&selectionId[0]={encoded_sel}"
        if sel_id:
            encoded_sel = urllib.parse.quote(sel_id, safe="")
            return f"https://on.sportsbook.fanduel.ca/addToBetslip?selectionId[0]={encoded_sel}"
        if ev_id:
            return f"https://on.sportsbook.fanduel.ca/sports/event/{urllib.parse.quote(ev_id, safe='')}"
        return "https://on.sportsbook.fanduel.ca/"

    # 3. BetMGM (documentation/betmgm.md)
    # Preferred: https://www.on.betmgm.ca/en/sports?options={fixtureId}-{optionMarketId}-{optionId}
    if "betmgm" in book:
        if ev_id and m_id and sel_id:
            composite = f"{ev_id}-{m_id}-{sel_id}"
            return f"https://www.on.betmgm.ca/en/sports?options={urllib.parse.quote(composite, safe='-:')}"
        if sel_id:
            return f"https://www.on.betmgm.ca/en/sports?options={urllib.parse.quote(sel_id, safe='-:')}"
        if ev_id:
            return f"https://www.on.betmgm.ca/en/sports/events/{match_slug}-{urllib.parse.quote(ev_id, safe=':')}"
        return "https://www.on.betmgm.ca/en/sports"

    # 4. Caesars (documentation/caesars.md)
    # Preferred: https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds={selectionId}
    if "caesars" in book or "czr" in book:
        if sel_id:
            return f"https://sportsbook.caesars.com/ca/on/bet/betslip?selectionIds={urllib.parse.quote(sel_id, safe='')}"
        if ev_id:
            return f"https://sportsbook.caesars.com/ca/on/bet/event/{urllib.parse.quote(ev_id, safe='')}"
        return "https://sportsbook.caesars.com/ca/on/bet"

    # 5. Betano (documentation/betano.md)
    # Preferred: https://www.betano.ca/live/{eventName}/{eventId}/
    if "betano" in book:
        if ev_id:
            return f"https://www.betano.ca/live/{match_slug}/{urllib.parse.quote(ev_id, safe='')}/"
        return "https://www.betano.ca/"

    return "#"
