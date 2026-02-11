"""Analyze bit patterns in MAZEDATA.EGA."""

import collections
from pathlib import Path

def analyze_bits():
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
        
    total = len(nibbles)
    
    # Check for grays if we assume 3 bits are tied
    # Bits: 3 2 1 0
    # Case A: Bits 0, 1, 2 are same
    tied_012 = sum(1 for n in nibbles if (n & 1 == (n >> 1) & 1 == (n >> 2) & 1))
    
    # Case B: Bits 1, 2, 3 are same
    tied_123 = sum(1 for n in nibbles if ((n >> 1) & 1 == (n >> 2) & 1 == (n >> 3) & 1))
    
    # Case C: Any 3 bits same?
    
    print(f"Percentage of pixels where bits 0,1,2 are identical: {tied_012/total*100:.1f}%")
    print(f"Percentage of pixels where bits 1,2,3 are identical: {tied_123/total*100:.1f}%")

if __name__ == "__main__":
    analyze_bits()
