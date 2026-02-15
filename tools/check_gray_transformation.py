"""Test bit inversions to find the most grayscale mapping."""

import collections
from pathlib import Path

def analyze_inversions():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    image_data = data[767:32767] # Sample first 32KB
    
    nibbles = []
    for b in image_data:
        nibbles.append(b >> 4)
        nibbles.append(b & 0x0F)
        
    total = len(nibbles)
    
    grays = {0, 7, 8, 15}
    
    best_mask = 0
    max_gray_pct = 0
    
    for mask in range(16):
        # Invert bits specified by mask
        gray_count = sum(1 for n in nibbles if (n ^ mask) in grays)
        pct = gray_count / total * 100
        if pct > max_gray_pct:
            max_gray_pct = pct
            best_mask = mask
            
    print(f"Best inversion mask: {best_mask:04b} ({max_gray_pct:.1f}% grays)")

if __name__ == "__main__":
    analyze_inversions()
