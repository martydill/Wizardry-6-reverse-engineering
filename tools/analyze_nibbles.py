"""Analyze nibble distribution in MAZEDATA.EGA."""

import collections
from pathlib import Path

def analyze_nibbles():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    # Skip index
    image_data = data[767:]
    
    nibbles = []
    for b in image_data:
        nibbles.append(b >> 4)
        nibbles.append(b & 0x0F)
        
    counts = collections.Counter(nibbles)
    total = len(nibbles)
    
    print("Nibble distribution (value: count %):")
    for val in range(16):
        count = counts[val]
        print(f"  {val:2d}: {count:6d} ({count/total*100:4.1f}%)")
        
    # Grays in default EGA palette: 0, 7, 8, 15
    grays = {0, 7, 8, 15}
    gray_total = sum(counts[v] for v in grays)
    print(f"\nTotal grays (0,7,8,15): {gray_total/total*100:.1f}%")

if __name__ == "__main__":
    analyze_nibbles()
