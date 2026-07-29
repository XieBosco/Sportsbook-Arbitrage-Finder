import base64
import msgpack
import json
import re
from datetime import datetime, timezone
import sys

# Your exact Washington Nationals string
b64_payload = "BQCqEIkAGQJlTjc6MDYuMjA0NTkwMzI0GQJzGPxBAhkDcBgf"
raw_bytes = base64.b64decode(b64_payload)
print(raw_bytes)
sys.exit()

# 1. Clean and pad exactly like the first successful script
b64_payload = re.sub(r'[^a-zA-Z0-9+/]', '', b64_payload)
if len(b64_payload) % 4 == 1:
    b64_payload = b64_payload[:-1]
b64_payload += "=" * ((4 - len(b64_payload) % 4) % 4)

# 2. Custom encoder to translate Timestamps and raw bytes into valid JSON strings
def safe_json_encoder(obj):
    if type(obj).__name__ == 'Timestamp':
        return datetime.fromtimestamp(obj.seconds, tz=timezone.utc).isoformat()
    if isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return str(obj)

try:
    raw_bytes = base64.b64decode(b64_payload)
    
    # 3. Revert to unpackb (which successfully extracted the Nationals data earlier)
    # We leave raw=True (the default) so it doesn't crash on binary hashes, 
    # letting our safe_json_encoder handle the text conversion.
    data = msgpack.unpackb(raw_bytes, strict_map_key=False)
    
    # 4. Format into clean JSON
    valid_json_output = json.dumps(data, indent=2, default=safe_json_encoder)
    
    print(valid_json_output)
    
    # Save it to a file you can copy-paste from
    with open("draftkings_odds.json", "w") as f:
        f.write(valid_json_output)
        print("\nSuccessfully saved to draftkings_odds.json!")
        
except Exception as e:
    print(f"Extraction failed: {e}")