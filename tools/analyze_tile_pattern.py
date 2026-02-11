"""Analyze the pattern in tile_320x200_5_0.png."""

from pathlib import Path
from PIL import Image
import numpy as np

def analyze_pattern():
    path = Path("output/mazedata_extracted_v5/atlas_0_32x32/tile_320x200_5_0.png")
    if not path.exists():
        print("File not found")
        return

    img = Image.open(path).convert("L") # Grayscale for pattern analysis
    data = np.array(img)
    
    print(f"Analyzing {path.name} pattern:")
    
    # Check for horizontal repetition
    # (Typical of brick walls where patterns repeat or are offset)
    diffs = []
    for shift in range(1, 16):
        diff = np.mean(np.abs(data[:, :-shift] - data[:, shift:]))
        diffs.append((shift, diff))
    
    diffs.sort(key=lambda x: x[1])
    print("\nPotential horizontal repetition (shift, mean_diff):")
    for shift, diff in diffs[:5]:
        print(f"  Shift {shift:2d}: {diff:.2f}")

    # Check for vertical repetition
    v_diffs = []
    for shift in range(1, 16):
        diff = np.mean(np.abs(data[:-shift, :] - data[shift:, :]))
        v_diffs.append((shift, diff))
        
    v_diffs.sort(key=lambda x: x[1])
    print("\nPotential vertical repetition (shift, mean_diff):")
    for shift, diff in v_diffs[:5]:
        print(f"  Shift {shift:2d}: {diff:.2f}")

    # Description based on pixel values
    # Let's look at the average brightness of rows
    row_means = np.mean(data, axis=1)
    print("\nRow brightness (first 10):")
    for i, m in enumerate(row_means[:10]):
        print(f"  Row {i:2d}: {m:.1f}")

if __name__ == "__main__":
    analyze_pattern()
