#!/usr/bin/env python3
"""
Compare top row cells (columns 15-19, row 0) between old and new files.
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
    file_new = Path("gamedata/NEWGAME.DBS")
    file_old = Path("gamedata/NEWGAMEold.dbs")

    if not file_new.exists() or not file_old.exists():
        print("Error: Files not found")
        sys.exit(1)

    cells_new = read_map_data(file_new)
    cells_old = read_map_data(file_old)

    print("Comparing TOP ROW (row 0), LAST 5 COLUMNS (15-19)")
    print("Bottom walls (south walls) added in NEW file")
    print("="*80)
    print()

    # Row 0, columns 15-19 in column-major
    for col in range(15, 20):
        row = 0
        cell_idx = col * 20 + row

        cell_old = cells_old[cell_idx]
        cell_new = cells_new[cell_idx]

        print(f"Column {col}, Row {row} (Cell {cell_idx}):")

        # Find differences
        changes = []
        for i in range(20):
            if cell_old[i] != cell_new[i]:
                changes.append((i, cell_old[i], cell_new[i]))

        if not changes:
            print("  NO CHANGES")
            print()
            continue

        print(f"  {len(changes)} byte(s) changed:")
        for byte_idx, old, new in changes:
            byte_type = "ODD" if byte_idx % 2 == 1 else "EVEN"
            xor = old ^ new
            print(f"    Byte {byte_idx:2d} ({byte_type}): 0x{old:02X} -> 0x{new:02X}  (XOR: 0x{xor:02X}, bin: {xor:08b})")

        print()

        # Show full before/after for changed bytes
        print("  Changed bytes in context:")
        print("    OLD: ", end="")
        for i in range(20):
            if cell_old[i] != cell_new[i]:
                print(f"[{i}:{cell_old[i]:02X}]", end=" ")
            elif cell_old[i] != 0:
                print(f"{i}:{cell_old[i]:02X}", end=" ")
        print()
        print("    NEW: ", end="")
        for i in range(20):
            if cell_old[i] != cell_new[i]:
                print(f"[{i}:{cell_new[i]:02X}]*", end=" ")
            elif cell_new[i] != 0:
                print(f"{i}:{cell_new[i]:02X}", end=" ")
        print()
        print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()

    all_changed_bytes = set()
    for col in range(15, 20):
        row = 0
        cell_idx = col * 20 + row
        cell_old = cells_old[cell_idx]
        cell_new = cells_new[cell_idx]

        for i in range(20):
            if cell_old[i] != cell_new[i]:
                all_changed_bytes.add(i)

    print(f"Byte positions that changed across all 5 cells: {sorted(all_changed_bytes)}")

    odd_bytes = [b for b in all_changed_bytes if b % 2 == 1]
    even_bytes = [b for b in all_changed_bytes if b % 2 == 0]

    print(f"  ODD bytes:  {odd_bytes}")
    print(f"  EVEN bytes: {even_bytes}")

if __name__ == "__main__":
    main()
