import json
import os
import dataclasses
from datetime import datetime

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from fixture_loader import get_all_normalized_updates

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

def set_nested(d, keys, value):
    """Set a value in a nested dictionary using a list of keys."""
    for key in keys[:-1]:
        key_str = str(key)
        if key_str not in d:
            d[key_str] = {}
        d = d[key_str]
    d[str(keys[-1])] = value

def main():
    print("Loading normalized updates from fixtures...")
    updates = get_all_normalized_updates()
    
    print(f"Loaded {len(updates)} updates. Matching...")
    store = BucketStore()
    resolver = TimeResolver()
    matcher = Matcher(store, resolver)
    
    for u in updates:
        matcher.assign(u)
        
    print("Building nested dictionary from flat BucketKey...")
    nested_dict = {}
    
    for key, bucket in store._index.items():
        keys_list = [
            key.sport_key,
            key.league_key,
            key.time_window,
            f"{key.home_team} vs {key.away_team}",
            key.market_type,
            key.selection,
            key.line
        ]
        set_nested(nested_dict, keys_list, bucket)

    out_path = os.path.join(os.path.dirname(__file__), "nested_buckets_dump.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(nested_dict, f, cls=EnhancedJSONEncoder, indent=2)
        
    print(f"Nested buckets dump written to {out_path}")

if __name__ == "__main__":
    main()
