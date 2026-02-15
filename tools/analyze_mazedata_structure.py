"""Analyze the index structure of MAZEDATA.EGA."""

import struct
from pathlib import Path

def analyze_index():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    count = struct.unpack_from("<H", data, 0)[0]
    print(f"Entry count: {count}")
    
    # We suspect 5-byte entries: [b0 b1] [off_lo off_hi] [b4]
    # But let's check if the offset might be 3 bytes after all, 
    # or if the entry is 6 bytes.
    
    # Let's try to find where the first offset points.
    # Entries start at offset 2.
    for entry_size in [4, 5, 6, 7, 8]:
        print(f"\nTrying entry size {entry_size}:")
        for i in range(5):
            base = 2 + i * entry_size
            entry = data[base : base + entry_size]
            print(f"  Entry {i}: {entry.hex(' ')}")

if __name__ == "__main__":
    analyze_index()
