#!/usr/bin/env python3
"""
Visualize which cells changed for the cross pattern test.
"""

from pathlib import Path

def read_map_data(filepath, bytes_per_cell=20):
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
    file_orig = Path("gamedata/newgameoriginal.dbs")
    file_new = Path("gamedata/NEWGAME.DBS")

    cells_orig = read_map_data(file_orig)
    cells_new = read_map_data(file_new)

    # Find changed cells
    changed = set()
    for cell_idx in range(400):
        if cells_orig[cell_idx] != cells_new[cell_idx]:
            changed.add(cell_idx)

    print("Visual map of changed cells (Column-major: cell = col * 20 + row)")
    print("="*80)
    print()
    print("   Col: ", end="")
    for col in range(20):
        print(f"{col%10}", end="")
    print()
    print("  +" + "-"*20 + "+")

    for row in range(20):
        print(f"{row:2d}|", end="")
        for col in range(20):
            cell_idx = col * 20 + row
            if cell_idx in changed:
                print("X", end="")
            else:
                print(".", end="")
        print("|")

    print("  +" + "-"*20 + "+")
    print()
    print("X = changed cell")
    print()

    # List changed cells with details
    print("="*80)
    print("Changed cells:")
    print("="*80)
    for cell_idx in sorted(changed):
        col = cell_idx // 20
        row = cell_idx % 20

        old_cell = cells_orig[cell_idx]
        new_cell = cells_new[cell_idx]

        print(f"\nCell {cell_idx} (Column {col}, Row {row}):")

        changes = []
        for i in range(20):
            if old_cell[i] != new_cell[i]:
                changes.append((i, old_cell[i], new_cell[i]))

        for byte_idx, old, new in changes:
            byte_type = "ODD" if byte_idx % 2 == 1 else "EVEN"
            xor = old ^ new
            print(f"  Byte {byte_idx:2d} ({byte_type}): 0x{old:02X} -> 0x{new:02X}  XOR: 0x{xor:02X}")

if __name__ == "__main__":
    main()
