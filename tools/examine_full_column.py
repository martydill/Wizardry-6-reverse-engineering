#!/usr/bin/env python3
"""
Examine ALL cells in column 1 to understand the wall pattern.
"""

import sys
from pathlib import Path

def read_map_data(filepath, bytes_per_cell=20, grid_height=20):
    """Read map data in column-major format."""
    with open(filepath, 'rb') as f:
        data = f.read()

    grid_width = 20
    cells = []

    for i in range(grid_width * grid_height):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def main():
    file_new = Path("gamedata/newgame.dbs")  # With horizontal walls
    file_old = Path("gamedata/newgameold.dbs")  # Before horizontal walls

    cells_new = read_map_data(file_new)
    cells_old = read_map_data(file_old)

    print("Examining COLUMN 1 (rightmost in map editor)")
    print("All 20 rows, showing ODD bytes (suspected horizontal wall bytes)")
    print("="*80)
    print()

    # Column 1 in column-major = cells 20-39
    column_1_start = 20
    column_1_end = 40

    for row in range(20):
        cell_idx = column_1_start + row
        cell_old = cells_old[cell_idx]
        cell_new = cells_new[cell_idx]

        # Show odd bytes only (1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
        odd_bytes_old = [cell_old[i] for i in range(1, 20, 2)]
        odd_bytes_new = [cell_new[i] for i in range(1, 20, 2)]

        print(f"Row {row:2d} (cell {cell_idx}):")

        # Show old (before horizontal walls)
        print(f"  OLD: ", end="")
        for i, (idx, val) in enumerate([(i, cell_old[i]) for i in range(1, 20, 2)]):
            if val != 0:
                print(f"[{idx}:{val:02X}]", end=" ")
            else:
                print(f" {idx}:--", end=" ")
        print()

        # Show new (with horizontal walls)
        print(f"  NEW: ", end="")
        for i, (idx, val) in enumerate([(i, cell_new[i]) for i in range(1, 20, 2)]):
            marker = ""
            if cell_old[idx] != cell_new[idx]:
                marker = "*"
            if val != 0:
                print(f"[{idx}:{val:02X}]{marker}", end=" ")
            else:
                print(f" {idx}:-- {marker}", end=" ")
        print()

        # Show changes
        changes = []
        for idx in range(1, 20, 2):
            if cell_old[idx] != cell_new[idx]:
                changes.append(f"byte {idx}: {cell_old[idx]:02X}->{cell_new[idx]:02X}")

        if changes:
            print(f"  CHANGES: {', '.join(changes)}")

        print()

    print("="*80)
    print("Pattern analysis:")
    print("="*80)
    print()
    print("Looking for which ODD byte represents horizontal walls between rows...")
    print()
    print("If byte positions represent walls to neighboring rows:")
    print("  - We need to find which byte changed when adding walls")
    print("  - All changed bytes have bit 7 (0x80) affected")
    print("  - This should reveal the encoding scheme")

if __name__ == "__main__":
    main()
