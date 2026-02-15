#!/usr/bin/env python3
"""
Visualize the map wall differences assuming 8 bytes per cell structure.
"""

import sys
from pathlib import Path

def visualize_map(filepath_new, filepath_old):
    """Visualize which cells changed between the two files."""
    with open(filepath_new, 'rb') as f:
        data_new = f.read()

    with open(filepath_old, 'rb') as f:
        data_old = f.read()

    print("Assuming 8 bytes per cell, 20x20 map:")
    print("="*70)
    print()

    # Find all differences
    differences = []
    for i in range(min(len(data_new), len(data_old))):
        if data_new[i] != data_old[i]:
            cell = i // 8
            byte_in_cell = i % 8
            row = cell // 20
            col = cell % 20
            differences.append((i, cell, row, col, byte_in_cell, data_new[i], data_old[i]))

    print("Changed bytes:")
    print(f"{'Offset':<10} {'Cell':<6} {'Row,Col':<10} {'Byte':<6} {'Old':<6} {'New':<6} {'XOR':<10}")
    print("-" * 70)

    for offset, cell, row, col, byte_num, old, new in differences:
        xor = old ^ new
        print(f"0x{offset:08X}  {cell:4d}   ({row:2d},{col:2d})   byte {byte_num}  0x{old:02X}   0x{new:02X}   {xor:08b}")

    print()
    print("="*70)
    print("Map visualization (20x20 grid):")
    print("'X' marks cells that changed")
    print()

    # Create a grid
    grid = [[' ' for _ in range(20)] for _ in range(20)]

    for offset, cell, row, col, byte_num, old, new in differences:
        if row < 20 and col < 20:
            grid[row][col] = 'X'

    # Print grid with coordinates
    print("    ", end="")
    for col in range(20):
        print(f"{col:2d}", end=" ")
    print()
    print("    " + "-" * 60)

    for row in range(20):
        print(f"{row:2d} |", end=" ")
        for col in range(20):
            print(f" {grid[row][col]}", end=" ")
        print()

    print()
    print("="*70)
    print("Examining the 8 bytes for each changed cell:")
    print()

    # Group changes by cell
    cells_changed = {}
    for offset, cell, row, col, byte_num, old, new in differences:
        if cell not in cells_changed:
            cells_changed[cell] = []
        cells_changed[cell].append((byte_num, old, new))

    for cell in sorted(cells_changed.keys()):
        row = cell // 20
        col = cell % 20
        print(f"Cell {cell} at ({row},{col}) - {len(cells_changed[cell])} bytes changed:")

        # Get all 8 bytes for this cell from both files
        cell_start = cell * 8
        cell_end = cell_start + 8

        bytes_new = data_new[cell_start:cell_end]
        bytes_old = data_old[cell_start:cell_end]

        print("  Byte:  0    1    2    3    4    5    6    7")
        print(f"  Old:  ", end="")
        for b in bytes_old:
            print(f"{b:02X}   ", end="")
        print()

        print(f"  New:  ", end="")
        for b in bytes_new:
            print(f"{b:02X}   ", end="")
        print()

        print("  Diff: ", end="")
        for i in range(8):
            if bytes_old[i] != bytes_new[i]:
                print(f"^^   ", end="")
            else:
                print(f"     ", end="")
        print()

        # Show which bytes changed
        print("  Changed bytes:")
        for byte_num, old, new in cells_changed[cell]:
            xor = old ^ new
            print(f"    Byte {byte_num}: {old:02X} -> {new:02X} (XOR: {xor:02X} = {xor:08b})")

        print()

def main():
    if len(sys.argv) == 3:
        file_new = Path(sys.argv[1])
        file_old = Path(sys.argv[2])
    else:
        file_new = Path("gamedata/newgame.dbs")
        file_old = Path("gamedata/newgameold.dbs")

    if not file_new.exists() or not file_old.exists():
        print("Error: Files not found")
        sys.exit(1)

    visualize_map(file_new, file_old)

if __name__ == "__main__":
    main()
