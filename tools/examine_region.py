#!/usr/bin/env python3
"""
Examine the top-right region of the map to understand the wall encoding.
"""

import sys
from pathlib import Path

def examine_region(filepath):
    """Examine cells in the top-right region."""
    with open(filepath, 'rb') as f:
        data = f.read()

    print("Examining top-right region of map (rows 0-5, columns 14-19)")
    print("Assuming 8 bytes per cell, 20x20 map")
    print("="*70)
    print()

    # Show cells in the region
    for row in range(0, 6):
        print(f"\nRow {row}:")
        print("-" * 70)

        for col in range(14, 20):
            cell = row * 20 + col
            cell_start = cell * 8
            cell_end = cell_start + 8

            if cell_end <= len(data):
                bytes_data = data[cell_start:cell_end]

                print(f"  Cell ({row},{col:2d}) = {cell:3d}: ", end="")
                for i, b in enumerate(bytes_data):
                    if b != 0:
                        print(f"[{i}:{b:02X}]", end=" ")
                    else:
                        print(f" {i}:--", end=" ")
                print()

    print()
    print("="*70)
    print("Focusing on changed cells and neighbors:")
    print()

    # Cell (3,15) and its neighbors
    changed_cells = [(3, 15), (4, 19)]

    for row, col in changed_cells:
        print(f"\nCell ({row},{col}) and its neighbors:")
        print("-" * 70)

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                r, c = row + dr, col + dc
                if 0 <= r < 20 and 0 <= c < 20:
                    cell = r * 20 + c
                    cell_start = cell * 8
                    cell_end = cell_start + 8

                    bytes_data = data[cell_start:cell_end]

                    marker = " <-- CHANGED" if (r, c) in changed_cells else ""
                    print(f"  ({r},{c:2d}): ", end="")

                    # Show all 8 bytes
                    for i, b in enumerate(bytes_data):
                        print(f"{b:02X} ", end="")

                    print(marker)
        print()

    print("="*70)
    print("Byte interpretation hypothesis:")
    print()
    print("Looking at byte patterns across cells:")
    print()

    # Collect statistics on which bytes are non-zero
    byte_usage = [0] * 8
    for cell in range(400):  # 20x20 = 400 cells
        cell_start = cell * 8
        cell_end = cell_start + 8

        if cell_end <= len(data):
            bytes_data = data[cell_start:cell_end]
            for i, b in enumerate(bytes_data):
                if b != 0:
                    byte_usage[i] += 1

    print("Byte usage across all 400 cells:")
    for i, count in enumerate(byte_usage):
        percentage = (count / 400) * 100
        print(f"  Byte {i}: {count:3d} cells have non-zero values ({percentage:5.1f}%)")

    print()
    print("="*70)
    print("Analyzing bit patterns in bytes 3 and 5:")
    print()

    # Look at bit patterns in bytes 3 and 5 specifically
    bit_patterns_3 = {}
    bit_patterns_5 = {}

    for cell in range(400):
        cell_start = cell * 8
        cell_end = cell_start + 8

        if cell_end <= len(data):
            bytes_data = data[cell_start:cell_end]

            b3 = bytes_data[3]
            b5 = bytes_data[5]

            if b3 not in bit_patterns_3:
                bit_patterns_3[b3] = []
            bit_patterns_3[b3].append(cell)

            if b5 not in bit_patterns_5:
                bit_patterns_5[b5] = []
            bit_patterns_5[b5].append(cell)

    print("Byte 3 patterns (top 10):")
    for pattern, cells in sorted(bit_patterns_3.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {pattern:02X} = {pattern:08b}: {len(cells):3d} cells")

    print()
    print("Byte 5 patterns (top 10):")
    for pattern, cells in sorted(bit_patterns_5.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"  {pattern:02X} = {pattern:08b}: {len(cells):3d} cells")

def main():
    file_path = Path("gamedata/newgameold.dbs")

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        sys.exit(1)

    examine_region(file_path)

if __name__ == "__main__":
    main()
