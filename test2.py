import base64
import json
import io  # Import the io module
import diffusion.datatypes

def parse_diffusion_payload(base64_string: str) -> dict:
    """
    Decodes a standalone Base64 Diffusion JSON payload into a Python dictionary.
    """
    try:
        # 1. Convert the Base64 string back into raw binary bytes
        raw_bytes = base64.b64decode(base64_string)
        
        # 2. Wrap the bytes in a stream so the SDK can call .read() on it
        byte_stream = io.BytesIO(raw_bytes)
        
        # 3. Pass the stream to the SDK parser
        diffusion_value = diffusion.datatypes.JSON.read_value(byte_stream)
        
        # 4. Extract the standard Python dictionary
        parsed_data = diffusion_value.get() 
        
        return parsed_data

    except base64.binascii.Error as e:
        print(f"Base64 Decoding Error: {e}")
        return None
    except Exception as e:
        print(f"Diffusion Parsing Error: {e}")
        return None

if __name__ == "__main__":
    target_payload = "hACpqZt4AZWT0W7aMBSGga7lFXY15WK3TEkotHDHELCqsGyFaVpvJic+STwcO/U52eBp9ih5qfQ6MxSqFWkXu7M/H/36P8suE/gJim745i0bhLzXhauOG4Vu5zL2vE7oh3brxl7kXrvgdb0YI20Af5ecgGW0ZMqZGqYiYbkzE0wRZruTZaoNjTWHcDnlplDYisEYbbDBU0F4nuRghOY2CPaJjfgJNOsT0DoFZ6fg1RG0DhnnR3AMvTgF7brmRksQd8F88n30dfStfhIyt0whQ2csaOvc6S2Tpzq3473O2UGnuddp/79O81D23zrH9s86R7+LF+0/BItJXQskZmglMiDf9fsd96rjeyu/O7x0h657ryRD+pJzRrCb2bx5HvJXrjfsDoZ+712/N+j7/rXv34tcIy0YRWmVxsJACITlmgvMJduuYEM/xvNgOXFmo8VEHnBgOJjXn0UkNcKMZfCYhZpIZ0H8UShKqySU+ldQULUOGQLONePAK2nTDLtRSqgEqxRlkUwBqapjsWdlrIosBNPmKZNxtNJ5rNV7G1A+2GZIu2UQRUUubJhBiLTif7PHB0qFeYGq2k4VikoImZTYSJCMWIN9mrogbNYqKoyxf+KTsBcAZm0vgpylbZlmdf0HIwBGJA=="
    
    print("Decoding payload...")
    result = parse_diffusion_payload(target_payload)
    
    if result:
        print("\n--- Decoded JSON ---")
        print(json.dumps(result, indent=4))
    else:
        print("\nFailed to decode the payload.")