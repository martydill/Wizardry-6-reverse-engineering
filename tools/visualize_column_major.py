#!/usr/bin/env python3
"""
Visualize the map using column-major, 20 bytes per cell.
"""

import sys
from pathlib import Path

def read_map_data(filepath, bytes_per_cell=20, grid_height=20):
    """Read map data in column-major format."""
    with open(filepath, 'rb') as f:
        data = f.read()

    grid_width = 20  # Assuming 20x20
    cells = []

    for i in range(grid_width * grid_height):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells, grid_width, grid_height

def main():
    file_new = Path("gamedata/newgame.dbs")
    file_old = Path("gamedata/newgameold.dbs")

    cells_new, width, height = read_map_data(file_new)
    cells_old, _, _ = read_map_data(file_old)

    print("Map visualization (COLUMN-MAJOR, 20 bytes/cell)")
    print("="*80)
    print()

    # Find changed cells
    changed = set()
    for cell_idx in range(len(cells_new)):
        if cells_new[cell_idx] != cells_old[cell_idx]:
            changed.add(cell_idx)

    print(f"Total cells changed: {len(changed)}")
    print()

    # Visualize as grid (column-major)
    print("Grid (column-major: cell_idx = col * 20 + row):")
    print("   ", end="")
    for col in range(width):
        print(f"{col%10}", end="")
    print()
    print("  +" + "-"*width + "+")

    for row in range(height):
        print(f"{row:2d}|", end="")
        for col in range(width):
            cell_idx = col * height + row  # Column-major
            if cell_idx in changed:
                print("X", end="")
            else:
                print(".", end="")
        print("|")

    print("  +" + "-"*width + "+")
    print()
    print("X = changed cell")
    print()

    # List changed cells
    print("Changed cells (column-major coordinates):")
    for cell_idx in sorted(changed):
        col = cell_idx // height
        row = cell_idx % height
        print(f"  Cell {cell_idx:3d} = Column {col:2d}, Row {row:2d}")
        if col == 1:
            print(f"                Column 1 = possible rightmost if stored reversed?")
        if col == 19:
            print(f"                Column 19 = rightmost in normal order")

    # Show what bytes changed in each cell
    print()
    print("="*80)
    print("Byte changes within each cell:")
    print("="*80)

    for cell_idx in sorted(changed):
        col = cell_idx // height
        row = cell_idx % height
        old_cell = cells_old[cell_idx]
        new_cell = cells_new[cell_idx]

        print(f"\nCell {cell_idx} (Column {col}, Row {row}):")

        changed_bytes = []
        for byte_idx in range(20):
            if old_cell[byte_idx] != new_cell[byte_idx]:
                changed_bytes.append((byte_idx, old_cell[byte_idx], new_cell[byte_idx]))

        if changed_bytes:
            print(f"  Changed bytes: {len(changed_bytes)}")
            for byte_idx, old, new in changed_bytes:
                print(f"    Byte {byte_idx:2d}: 0x{old:02X} -> 0x{new:02X}")

if __name__ == "__main__":
    main()
