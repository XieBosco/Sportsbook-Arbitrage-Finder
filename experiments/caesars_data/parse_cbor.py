import json
import base64
import cbor2
import glob

def find_cbor(decoded):
    for offset in range(len(decoded)):
        from io import BytesIO
        fp = BytesIO(decoded[offset:])
        items = []
        valid = True
        while fp.tell() < len(decoded) - offset:
            try:
                items.append(cbor2.load(fp))
            except Exception:
                valid = False
                break
        if items and valid and fp.tell() == len(decoded) - offset:
            return offset, items
    return -1, []

for file in sorted(glob.glob("messages/*.json")):
    with open(file, 'r') as f:
        decoded = base64.b64decode(f.read().strip())
    offset, items = find_cbor(decoded)
    print(f"{file}: Offset {offset}")
    for item in items:
        print(f"  {str(item)[:200]}")
