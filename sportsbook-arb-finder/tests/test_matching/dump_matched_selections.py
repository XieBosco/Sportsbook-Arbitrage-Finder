import json
import os
import dataclasses
from datetime import datetime

from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.matching.output import MatchOutputBuilder
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
        
    print("Generating MatchedSelections...")
    
    matched_selections = []
    for bucket in store._index.values():
        ms = MatchOutputBuilder.from_bucket(bucket)
        matched_selections.append(ms)

    out_path = os.path.join(os.path.dirname(__file__), "matched_selections_dump.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(matched_selections, f, cls=EnhancedJSONEncoder, indent=2)
        
    print(f"MatchedSelections dump written to {out_path}")

if __name__ == "__main__":
    main()
