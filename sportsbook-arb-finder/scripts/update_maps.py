import json
import os
import re

MAPS_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\sportsbook-arb-finder\src\arbfinder\normalization\maps"

map_files = ["sport_map.json", "league_map.json", "market_type_map.json", "selection_map.json", "team_aliases.json"]

# Load original maps
original_maps = {}
for m_name in map_files:
    path = os.path.join(MAPS_DIR, m_name)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        original_maps[m_name] = json.loads(content) if content else {}

# Build raw to std reverse mapping from original maps
raw_to_std = {m: {} for m in map_files}
for m_name in map_files:
    for std, book_dict in original_maps[m_name].items():
        for book, raw in book_dict.items():
            if isinstance(raw, list):
                for r in raw:
                    raw_to_std[m_name][(book, r)] = std
            else:
                raw_to_std[m_name][(book, raw)] = std

# 1. Load parsed_messages_output.txt
verified = {m: set() for m in map_files}

with open(r"C:\Users\fiona\Desktop\arbitrage_tool\sportsbook-arb-finder\tests\test_parsers\parsed_messages_output.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for line in lines[2:]:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 12: continue
        book = parts[0]
        verified["sport_map.json"].add((book, parts[1]))
        verified["league_map.json"].add((book, parts[2]))
        verified["team_aliases.json"].add((book, parts[5]))
        verified["team_aliases.json"].add((book, parts[6]))
        verified["market_type_map.json"].add((book, parts[7]))
        verified["selection_map.json"].add((book, parts[8]))

# 2. Extract references from parsed_reference_dicts.json
refs = json.load(open(r"C:\Users\fiona\Desktop\arbitrage_tool\sportsbook-arb-finder\tests\test_parsers\parsed_reference_dicts.json", "r", encoding="utf-8"))

ref_values = {m: set() for m in map_files}

for book, data in refs.items():
    if "events" in data:
        for ev in data["events"].values():
            if "sport_code" in ev: ref_values["sport_map.json"].add((book, str(ev["sport_code"])))
            if "league_name" in ev: ref_values["league_map.json"].add((book, str(ev["league_name"])))
            name = ev.get("name") or ""
            # basic split
            if " @ " in name:
                teams = name.split(" @ ")
                home = re.sub(r'\s*\([^)]*\)', '', teams[1]).strip()
                away = re.sub(r'\s*\([^)]*\)', '', teams[0]).strip()
                ref_values["team_aliases.json"].add((book, home))
                ref_values["team_aliases.json"].add((book, away))
            elif " vs " in name:
                teams = name.split(" vs ")
                home = re.sub(r'\s*\([^)]*\)', '', teams[0]).strip()
                away = re.sub(r'\s*\([^)]*\)', '', teams[1]).strip()
                ref_values["team_aliases.json"].add((book, home))
                ref_values["team_aliases.json"].add((book, away))

    if "markets" in data:
        for m in data["markets"].values():
            if isinstance(m, dict):
                m_name = m.get("name") or m.get("marketName")
                if m_name:
                    ref_values["market_type_map.json"].add((book, str(m_name)))
            elif isinstance(m, str):
                ref_values["market_type_map.json"].add((book, m))

    if "selections" in data:
        for s in data["selections"].values():
            if isinstance(s, dict):
                s_name = s.get("name") or s.get("selectionName")
                if s_name:
                    ref_values["selection_map.json"].add((book, str(s_name)))
            elif isinstance(s, str):
                # not enough info to get string name
                pass

# Helper to normalize selections
def get_standard_selection(raw_sel, raw_to_std_selections, raw_to_std_teams, book):
    if (book, raw_sel) in raw_to_std_selections:
        return raw_to_std_selections[(book, raw_sel)]
    # try over under
    lower_sel = raw_sel.lower()
    if lower_sel.startswith("over") or lower_sel == "o":
        return "over"
    if lower_sel.startswith("under") or lower_sel == "u":
        return "under"
    # check if it matches a team alias
    # some selections might have spread attached e.g. "HOU Astros -1.5"
    team_part = re.sub(r'[+-]?\d+\.?\d*$', '', raw_sel).strip()
    if (book, team_part) in raw_to_std_teams:
        return raw_to_std_teams[(book, team_part)]
    if (book, raw_sel) in raw_to_std_teams:
        return raw_to_std_teams[(book, raw_sel)]
    return raw_sel

# 3. Process maps
for m_name in map_files:
    path = os.path.join(MAPS_DIR, m_name)
    m_dict = original_maps[m_name]
    
    # First pass: clean up - keep only verified
    cleaned_dict = {}
    
    for std, book_dict in m_dict.items():
        new_book_dict = {}
        for book, raw in book_dict.items():
            if isinstance(raw, list):
                verified_raw = [r for r in raw if (book, r) in verified[m_name]]
                # Also deduplicate
                verified_raw = list(dict.fromkeys(verified_raw))
                if verified_raw:
                    new_book_dict[book] = verified_raw
            else:
                if (book, raw) in verified[m_name]:
                    new_book_dict[book] = raw
        if new_book_dict:
            cleaned_dict[std] = new_book_dict
            
    # Second pass: add from reference dicts + parsed messages output (some verified might be new)
    all_raws_to_add = verified[m_name].union(ref_values[m_name])
    
    for book, raw in all_raws_to_add:
        # Ignore empty values
        if not raw:
            continue
            
        std = raw_to_std[m_name].get((book, raw))
        
        if not std:
            if m_name == "selection_map.json":
                std = get_standard_selection(raw, raw_to_std["selection_map.json"], raw_to_std["team_aliases.json"], book)
            else:
                std = raw
        
        if std not in cleaned_dict:
            cleaned_dict[std] = {}
            
        if m_name == "team_aliases.json":
            if book not in cleaned_dict[std]:
                cleaned_dict[std][book] = []
            if raw not in cleaned_dict[std][book]:
                cleaned_dict[std][book].append(raw)
        else:
            cleaned_dict[std][book] = raw

    # Write back
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cleaned_dict, f, indent=4)

print("Maps updated successfully.")
