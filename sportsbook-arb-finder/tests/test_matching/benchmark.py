import time
import timeit
from arbfinder.matching.bucket_store import BucketStore
from arbfinder.matching.matcher import Matcher
from arbfinder.matching.time_resolver import TimeResolver
from arbfinder.matching.output import MatchOutputBuilder
from fixture_loader import get_all_normalized_updates

def benchmark():
    print("Loading normalized updates...")
    updates = get_all_normalized_updates()
    
    if len(updates) < 50:
        print("Not enough updates to benchmark.")
        return
        
    updates_50 = updates[:50]
    print("Benchmarking 50 NormalizedOddsUpdate objects...")
    
    def run_benchmark():
        store = BucketStore()
        resolver = TimeResolver()
        matcher = Matcher(store, resolver)
        
        for u in updates_50:
            matcher.assign(u)
            
        matched_selections = []
        for bucket in store._index.values():
            ms = MatchOutputBuilder.from_bucket(bucket)
            matched_selections.append(ms)
            
        return len(matched_selections)
            
    # Run once to ensure it works and get the count
    num_selections = run_benchmark()
    
    # Time it
    iterations = 1000
    total_time = timeit.timeit(run_benchmark, number=iterations)
    avg_time = total_time / iterations
    
    print(f"Generated {num_selections} MatchedSelection objects from 50 updates.")
    print(f"Total time for {iterations} iterations: {total_time:.6f} seconds")
    print(f"Average time per iteration (50 updates): {avg_time:.6f} seconds ({avg_time * 1000:.3f} ms)")

if __name__ == "__main__":
    benchmark()
