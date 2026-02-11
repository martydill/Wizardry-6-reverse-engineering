"""Analyze correlation between planes in MAZEDATA.EGA."""

import sys
from pathlib import Path

def analyze_correlations():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    atlas_data = data[:32000]
    
    # Each plane is 8000 bytes
    planes = [
        atlas_data[0:8000],
        atlas_data[8000:16000],
        atlas_data[16000:24000],
        atlas_data[24000:32000]
    ]
    
    print("Plane similarities (matching bytes out of 8000):")
    for i in range(4):
        for j in range(i + 1, 4):
            matches = sum(1 for b1, b2 in zip(planes[i], planes[j]) if b1 == b2)
            percentage = matches / 8000 * 100
            print(f"  Plane {i} vs Plane {j}: {matches} matches ({percentage:.1f}%)")

if __name__ == "__main__":
    analyze_correlations()
