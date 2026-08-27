import collections
import json
import os
from datetime import datetime

# Parse data
events_by_book = collections.defaultdict(dict)
rows = []

with open(r"C:\Users\fiona\Desktop\arbitrage_tool\sportsbook-arb-finder\tests\test_parsers\parsed_messages_output.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for line in lines[2:]:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 12:
            r = {
                "book": parts[0],
                "sport": parts[1],
                "league": parts[2],
                "start_time": parts[3],
                "event_id": parts[4],
                "home": parts[5],
                "away": parts[6],
                "market": parts[7],
                "selection": parts[8],
                "line": parts[9],
                "odds": parts[10]
            }
            rows.append(r)
            if r["home"] and r["away"]:
                try:
                    dt = datetime.fromisoformat(r["start_time"].replace("Z", "+00:00"))
                except:
                    dt = None
                events_by_book[r["book"]][r["event_id"]] = {
                    "book": r["book"],
                    "sport": r["sport"],
                    "league": r["league"],
                    "start_time": dt,
                    "home": r["home"],
                    "away": r["away"]
                }

def words_overlap(t1, t2):
    w1 = set(t1.lower().split())
    w2 = set(t2.lower().split())
    # Exclude common generic words that might cause false positives
    w1.discard("city")
    w2.discard("city")
    w1.discard("fc")
    w2.discard("fc")
    w1.discard("sox")
    w2.discard("sox") # wait, White Sox and Red Sox overlap in "Sox"!
    # Let's remove "sox" from check
    w1.discard("sox")
    w2.discard("sox")
    # Actually just intersection is fine except for "New York", "Chicago", "Los Angeles"
    return len(w1.intersection(w2)) > 0

standard_events = []

for b, book_evs in events_by_book.items():
    for ev_id, ev in book_evs.items():
        matched = False
        for se in standard_events:
            se_ev = list(se.values())[0]
            if ev["start_time"] and se_ev["start_time"]:
                dt1 = ev["start_time"].replace(tzinfo=None)
                dt2 = se_ev["start_time"].replace(tzinfo=None)
                if abs((dt1 - dt2).total_seconds()) <= 3600:
                    if words_overlap(ev["home"], se_ev["home"]) and words_overlap(ev["away"], se_ev["away"]):
                        se[b] = ev
                        matched = True
                        break
        if not matched:
            standard_events.append({b: ev})

sport_map = collections.defaultdict(dict)
league_map = collections.defaultdict(dict)
team_aliases = collections.defaultdict(lambda: collections.defaultdict(list))
market_map = collections.defaultdict(dict)
selection_map = collections.defaultdict(dict)

# Build standard event mappings
team_to_std = {}
for se in standard_events:
    homes = [e["home"] for e in se.values()]
    aways = [e["away"] for e in se.values()]
    std_home = max(homes, key=len)
    std_away = max(aways, key=len)
    
    sports = [e["sport"] for e in se.values()]
    alpha_sports = [s for s in sports if s.isalpha()]
    std_sport = alpha_sports[0] if alpha_sports else sports[0]
    
    leagues = [e["league"] for e in se.values()]
    alpha_leagues = [l for l in leagues if l.isalpha()]
    std_league = alpha_leagues[0] if alpha_leagues else leagues[0]
    
    for b, e in se.items():
        sport_map[std_sport][b] = e["sport"]
        league_map[std_league][b] = e["league"]
        
        home = e["home"]
        away = e["away"]
        if home not in team_aliases[std_home][b]: team_aliases[std_home][b].append(home)
        if away not in team_aliases[std_away][b]: team_aliases[std_away][b].append(away)
        team_to_std[home] = std_home
        team_to_std[away] = std_away

# Parse rows again for markets and selections
for r in rows:
    b = r["book"]
    m = r["market"]
    s = r["selection"]
    
    std_m = None
    if "Moneyline" in m or "MONEY_LINE" in m or "Winner" in m or "Money Line" in m:
        std_m = "moneyline"
    elif "Run Line" in m or "HANDICAP" in m or "Spread" in m:
        std_m = "run_line"
    elif "Total" in m or "TOTAL" in m or "Over/Under" in m:
        std_m = "total"
    else:
        std_m = m
        
    market_map[std_m][b] = m
    
    std_s = None
    s_lower = s.lower()
    if s_lower.startswith("over") or s_lower == "o":
        std_s = "over"
    elif s_lower.startswith("under") or s_lower == "u":
        std_s = "under"
    else:
        team_part = __import__('re').sub(r'[+-]?\d+\.?\d*$', '', s).strip()
        if team_part in team_to_std:
            std_s = team_to_std[team_part]
        elif s in team_to_std:
            std_s = team_to_std[s]
        else:
            std_s = s
            
    selection_map[std_s][b] = s

OUT_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\sportsbook-arb-finder\src\arbfinder\normalization\maps"

with open(os.path.join(OUT_DIR, "sport_map.json"), "w", encoding="utf-8") as f: json.dump(sport_map, f, indent=4)
with open(os.path.join(OUT_DIR, "league_map.json"), "w", encoding="utf-8") as f: json.dump(league_map, f, indent=4)
with open(os.path.join(OUT_DIR, "team_aliases.json"), "w", encoding="utf-8") as f: json.dump(team_aliases, f, indent=4)
with open(os.path.join(OUT_DIR, "market_type_map.json"), "w", encoding="utf-8") as f: json.dump(market_map, f, indent=4)
with open(os.path.join(OUT_DIR, "selection_map.json"), "w", encoding="utf-8") as f: json.dump(selection_map, f, indent=4)

print("Maps successfully built entirely from parsed_messages_output.txt!")
