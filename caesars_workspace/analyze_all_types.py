"""Analyze all 551 ws files to understand what message types exist and what's not yet decoded."""
import base64, os

LOG_DIR = r"c:\Users\fiona\Desktop\arbitrage_tool\caesars_workspace\caesars_full_logs"

type_counts = {}
type_examples = {}
tiny_files = 0  # 4-byte files (likely pings/heartbeats)

for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r') as f:
        raw = f.read().strip()
    d = base64.b64decode(raw)
    
    if len(d) <= 3:
        tiny_files += 1
        type_byte = f"0x{d[0]:02x}" if len(d) > 0 else "empty"
        key = f"{type_byte} (len={len(d)})"
    else:
        type_byte = d[0]
        key = f"0x{type_byte:02x}"
    
    type_counts[key] = type_counts.get(key, 0) + 1
    if key not in type_examples:
        type_examples[key] = []
    if len(type_examples[key]) < 3:
        type_examples[key].append((n, len(d), d[:30].hex()))

print("=== Message type distribution ===")
for key in sorted(type_counts.keys()):
    print(f"  {key}: {type_counts[key]} messages")
    for n, length, hex_preview in type_examples[key]:
        print(f"    ws_{n}: len={length}, hex={hex_preview}")

print(f"\nTotal files: {sum(type_counts.values())}")
print(f"Tiny files (<=3 bytes): {tiny_files}")

# Check what the small files (4 bytes, type 0x13 or similar) contain
print("\n=== All distinct small message payloads ===")
small_payloads = set()
for n in range(1, 552):
    fpath = os.path.join(LOG_DIR, f"ws_{n}.txt")
    if not os.path.exists(fpath): continue
    with open(fpath, 'r') as f:
        raw = f.read().strip()
    d = base64.b64decode(raw)
    if len(d) <= 6:
        small_payloads.add(d.hex())

for p in sorted(small_payloads):
    print(f"  {p}")
