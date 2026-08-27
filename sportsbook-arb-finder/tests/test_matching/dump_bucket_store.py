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

def main():
    print("Loading normalized updates from fixtures...")
    updates = get_all_normalized_updates()
    
    print(f"Loaded {len(updates)} updates. Matching...")
    store = BucketStore()
    resolver = TimeResolver()
    matcher = Matcher(store, resolver)
    
    for u in updates:
        matcher.assign(u)
        
    print("Dumping BucketStore to JSON...")
    
    out_dict = {}
    for key, bucket in store._index.items():
        key_str = f"{key.sport_key}_{key.league_key}_{key.time_window}_{key.home_team}_{key.away_team}_{key.market_type}_{key.selection}_{key.line}"
        out_dict[key_str] = bucket

    out_path = os.path.join(os.path.dirname(__file__), "bucket_store_dump.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_dict, f, cls=EnhancedJSONEncoder, indent=2)
        
    print(f"BucketStore dump written to {out_path}")

if __name__ == "__main__":
    main()
