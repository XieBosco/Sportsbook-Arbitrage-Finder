import json, os
LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"
for i in range(1, 14):
    fpath = os.path.join(LOG_DIR, f"json_{i}.json")
    data = json.load(open(fpath))
    url = data.get('_DEBUG_URL', '?')
    size = os.path.getsize(fpath)
    print(f"json_{i}.json ({size:>10} bytes): {url[:150]}")
