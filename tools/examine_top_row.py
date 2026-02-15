#!/usr/bin/env python3
"""
Examine row 0 (top row), columns 15-19 to see the bottom wall encoding.
"""

import sys
from pathlib import Path

def read_map_data(filepath, bytes_per_cell=20):
    """Read map data in column-major format."""
    with open(filepath, 'rb') as f:
        data = f.read()

    cells = []
    for i in range(400):  # 20x20 grid
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def main():
    filepath = Path("gamedata/newgame.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    cells = read_map_data(filepath)

    print("Examining TOP ROW (row 0), LAST 5 COLUMNS (15-19)")
    print("Looking for BOTTOM WALLS (south walls)")
    print("Column-major: cell_index = column * 20 + row")
    print("="*80)
    print()

    # Row 0, columns 15-19 in column-major
    for col in range(15, 20):
        row = 0
        cell_idx = col * 20 + row

        cell_data = cells[cell_idx]

        print(f"Column {col}, Row {row} (Cell {cell_idx}):")
        print(f"  Full cell data:")
        print(f"    ", end="")
        for i in range(20):
            print(f"{cell_data[i]:02X} ", end="")
            if (i + 1) % 10 == 0:
                print()
                print(f"    ", end="")
        print()

        # Show odd bytes (suspected horizontal wall bytes)
        print(f"  ODD bytes (horizontal walls?):")
        print(f"    ", end="")
        for i in range(1, 20, 2):
            if cell_data[i] != 0:
                print(f"[{i:2d}:{cell_data[i]:02X}]", end=" ")
            else:
                print(f" {i:2d}:-- ", end=" ")
        print()

        # Show even bytes (suspected vertical wall bytes?)
        print(f"  EVEN bytes (vertical walls?):")
        print(f"    ", end="")
        for i in range(0, 20, 2):
            if cell_data[i] != 0:
                print(f"[{i:2d}:{cell_data[i]:02X}]", end=" ")
            else:
                print(f" {i:2d}:-- ", end=" ")
        print()
        print()

    # Also show row 1 in these columns (to see if walls stored in adjacent cells)
    print("="*80)
    print("Also checking ROW 1 (cells below) to see if walls stored there:")
    print("="*80)
    print()

    for col in range(15, 20):
        row = 1
        cell_idx = col * 20 + row

        cell_data = cells[cell_idx]

        print(f"Column {col}, Row {row} (Cell {cell_idx}):")
        print(f"  ODD bytes: ", end="")
        for i in range(1, 20, 2):
            if cell_data[i] != 0:
                print(f"[{i}:{cell_data[i]:02X}]", end=" ")
        print()
        print(f"  EVEN bytes: ", end="")
        for i in range(0, 20, 2):
            if cell_data[i] != 0:
                print(f"[{i}:{cell_data[i]:02X}]", end=" ")
        print()
        print()

if __name__ == "__main__":
    main()
