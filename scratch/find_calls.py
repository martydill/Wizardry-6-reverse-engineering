import struct
from pathlib import Path

def find_calls(filename, target_offset):
    data = Path(filename).read_bytes()
    
    for i in range(len(data) - 2):
        if data[i] == 0xE8: # call rel16
            rel16 = struct.unpack("<h", data[i+1:i+3])[0]
            dest = (i + 3 + rel16) & 0xFFFF
            if dest == target_offset:
                print(f"Call to {target_offset:04x} found at {i:04x}")
                # Show preceding pushes
                start = max(0, i - 15)
                print(f"  Context: {data[start:i].hex()}")

if __name__ == "__main__":
    find_calls("gamedata/WINIT.OVR", 0x97c)
