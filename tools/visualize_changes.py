#!/usr/bin/env python3
"""
Visualize which cells changed.
"""

import sys
from pathlib import Path

def read_file(filepath):
    """Read entire file."""
    with open(filepath, 'rb') as f:
        return f.read()

def main():
    file_new = Path("gamedata/newgame.dbs")
    file_old = Path("gamedata/newgameold.dbs")

    data_new = read_file(file_new)
    data_old = read_file(file_old)

    # Find changed cells
    changed_cells = set()
    for offset in range(min(len(data_new), len(data_old))):
        if data_new[offset] != data_old[offset]:
            cell_idx = offset // 8
            changed_cells.add(cell_idx)

    print("Visual map of changed cells:")
    print("="*70)
    print()
    print("   ", end="")
    for col in range(20):
        print(f"{col%10}", end="")
    print()
    print("  +" + "-"*20 + "+")

    for row in range(20):
        print(f"{row:2d}|", end="")
        for col in range(20):
            cell_idx = row * 20 + col
            if cell_idx in changed_cells:
                print("X", end="")
            else:
                print(".", end="")
        print("|")

    print("  +" + "-"*20 + "+")
    print()
    print("X = cell changed")
    print(". = cell unchanged")
    print()

    # List the changed cells
    print("\nChanged cells:")
    for cell_idx in sorted(changed_cells):
        row = cell_idx // 20
        col = cell_idx % 20
        print(f"  ({row:2d},{col:2d})", end="")
        if col == 19:
            print(" <-- Column 19 (rightmost)", end="")
        print()

if __name__ == "__main__":
    main()
