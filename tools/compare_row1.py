#!/usr/bin/env python3
"""
Compare row 1 cells (columns 15-19, row 1) between old and new files.
This checks if "bottom walls" of row 0 are stored as "top walls" in row 1.
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
    file_new = Path("gamedata/newgame.dbs")
    file_old = Path("gamedata/newgameold.dbs")

    if not file_new.exists() or not file_old.exists():
        print("Error: Files not found")
        sys.exit(1)

    cells_new = read_map_data(file_new)
    cells_old = read_map_data(file_old)

    print("Comparing ROW 1 (cells below top row), COLUMNS 15-19")
    print("Checking if bottom walls of row 0 are stored as top walls in row 1")
    print("="*80)
    print()

    # Row 1, columns 15-19 in column-major
    for col in range(15, 20):
        row = 1
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
            # Check if bit 7 changed
            bit7_changed = "(bit 7 changed)" if (xor & 0x80) else ""
            print(f"    Byte {byte_idx:2d} ({byte_type}): 0x{old:02X} -> 0x{new:02X}  (XOR: 0x{xor:02X}, bin: {xor:08b}) {bit7_changed}")

        print()

    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()

    all_changed_bytes = {}
    for col in range(15, 20):
        row = 1
        cell_idx = col * 20 + row
        cell_old = cells_old[cell_idx]
        cell_new = cells_new[cell_idx]

        for i in range(20):
            if cell_old[i] != cell_new[i]:
                if i not in all_changed_bytes:
                    all_changed_bytes[i] = []
                all_changed_bytes[i].append((col, cell_old[i], cell_new[i]))

    print("Byte positions that changed:")
    for byte_pos in sorted(all_changed_bytes.keys()):
        byte_type = "ODD" if byte_pos % 2 == 1 else "EVEN"
        print(f"\n  Byte {byte_pos:2d} ({byte_type}):")
        for col, old, new in all_changed_bytes[byte_pos]:
            xor = old ^ new
            print(f"    Column {col}: 0x{old:02X} -> 0x{new:02X}  (XOR: 0x{xor:02X})")

    if all_changed_bytes:
        odd_bytes = [b for b in all_changed_bytes.keys() if b % 2 == 1]
        even_bytes = [b for b in all_changed_bytes.keys() if b % 2 == 0]
        print(f"\n  ODD byte positions:  {odd_bytes}")
        print(f"  EVEN byte positions: {even_bytes}")

if __name__ == "__main__":
    main()
