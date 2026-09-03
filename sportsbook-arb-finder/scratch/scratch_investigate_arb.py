import json
from datetime import datetime, timezone

with open('scripts/data2/timeline.jsonl', 'r') as f:
    events = [json.loads(line) for line in f]

count = 0
for e in events:
    dt = datetime.fromtimestamp(e['timestamp'], timezone.utc)
    # Check between 03:13:00 and 03:15:00
    if dt >= datetime(2026, 8, 30, 3, 13, 0, tzinfo=timezone.utc) and dt <= datetime(2026, 8, 30, 3, 15, 0, tzinfo=timezone.utc):
        print(f'{dt} | {e["sportsbook"]} | {e["file_name"]}')
        count += 1
        
print(f"Total events in this window: {count}")
