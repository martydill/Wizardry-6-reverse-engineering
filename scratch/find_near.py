import struct
from pathlib import Path

def find_near(filename, b1, b2, window=20):
    data = Path(filename).read_bytes()
    for i in range(len(data)):
        if data[i] == b1:
            for j in range(max(0, i - window), min(len(data), i + window)):
                if data[j] == b2 and i != j:
                    print(f"Found {b1:02x} and {b2:02x} near each other at {i:04x} and {j:04x}")
                    # Show context
                    start = min(i, j) - 5
                    end = max(i, j) + 5
                    print(f"  Context: {data[start:end].hex()}")

if __name__ == "__main__":
    find_near("gamedata/WINIT.OVR", 0x09, 0x0a)
