import json
import os
import sys
import dataclasses
from datetime import datetime

# Add test_matching to path so we can import fixture_loader
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_matching")))

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.matching.output import MatchOutputBuilder
from fixture_loader import get_all_normalized_updates
from arbfinder.scanner.market_grouper import MarketGrouper, MarketGroupKey

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, set):
            return list(o)
        return super().default(o)

def main():
    print("Loading normalized updates from fixtures...")
    updates = get_all_normalized_updates()
    
    print(f"Loaded {len(updates)} updates. Matching...")
    store = BucketStore()
    resolver = TimeResolver()
    matcher = Matcher(store, resolver)
    
    for u in updates:
        matcher.assign(u)
        
    print("Generating MatchedSelections and grouping them...")
    grouper = MarketGrouper()
    
    for bucket in store._index.values():
        ms = MatchOutputBuilder.from_bucket(bucket)
        grouper.add(ms)

    out_path = os.path.join(os.path.dirname(__file__), "market_grouper_dump.json")
    
    # We have to convert the MarketGrouper's _groups dict (whose keys are MarketGroupKey objects)
    # into a dict with string keys for JSON serialization.
    groups_dict = {}
    for key, group in grouper._groups.items():
        str_key = f"{key.sport_key}|{key.league_key}|{key.home_team}|{key.away_team}|{key.market_type}|{key.line}"
        groups_dict[str_key] = group

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(groups_dict, f, cls=EnhancedJSONEncoder, indent=2)
        
    print(f"MarketGrouper dump written to {out_path}")

if __name__ == "__main__":
    main()
