#!/usr/bin/env python3
"""
Analyze the horizontal wall changes in the rightmost column.
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

    if not file_new.exists() or not file_old.exists():
        print("Error: Files not found")
        sys.exit(1)

    data_new = read_file(file_new)
    data_old = read_file(file_old)

    print("Analyzing horizontal walls on rightmost column (column 19)")
    print("="*70)
    print()

    # Find all differences
    diffs = []
    for i in range(min(len(data_new), len(data_old))):
        if data_new[i] != data_old[i]:
            diffs.append((i, data_old[i], data_new[i]))

    print(f"Total byte differences: {len(diffs)}")
    print()

    # Assuming 8 bytes per cell, 20x20 grid
    print("Mapping changes to cells (8 bytes per cell):")
    print("="*70)
    print()
    print(f"{'Offset':<12} {'Cell':<8} {'Row,Col':<12} {'Byte':<8} {'Old':<8} {'New':<8} {'Change':<12}")
    print("-"*70)

    cell_changes = {}

    for offset, old, new in diffs:
        cell_idx = offset // 8
        byte_in_cell = offset % 8
        row = cell_idx // 20
        col = cell_idx % 20

        if cell_idx not in cell_changes:
            cell_changes[cell_idx] = []

        cell_changes[cell_idx].append((byte_in_cell, old, new))

        xor = old ^ new
        change_dir = "ADD 0x80" if new > old else "REM 0x80"

        print(f"0x{offset:08X}  {cell_idx:6d}  ({row:2d},{col:2d})     byte {byte_in_cell}  0x{old:02X}    0x{new:02X}    {change_dir}")

    print()
    print("="*70)
    print("Cells affected (grouped by cell):")
    print("="*70)
    print()

    for cell_idx in sorted(cell_changes.keys()):
        row = cell_idx // 20
        col = cell_idx % 20
        changes = cell_changes[cell_idx]

        print(f"\nCell {cell_idx} at ({row:2d},{col:2d}) - Column {'19 (RIGHTMOST)' if col == 19 else str(col)}:")

        for byte_idx, old, new in changes:
            xor = old ^ new
            change = "ADDED bit 7" if new > old else "REMOVED bit 7"
            print(f"  Byte {byte_idx}: 0x{old:02X} -> 0x{new:02X} ({change})")

    # Now analyze the pattern
    print()
    print("="*70)
    print("PATTERN ANALYSIS:")
    print("="*70)
    print()

    # Group cells by column
    by_column = {}
    for cell_idx in cell_changes.keys():
        col = cell_idx % 20
        if col not in by_column:
            by_column[col] = []
        by_column[col].append(cell_idx)

    for col in sorted(by_column.keys()):
        cells = by_column[col]
        rows = [c // 20 for c in cells]
        print(f"Column {col}: {len(cells)} cells affected (rows {min(rows)}-{max(rows)})")

    # Check if it's the rightmost column
    if 19 in by_column:
        print()
        print("RIGHTMOST COLUMN (19) ANALYSIS:")
        print("-"*70)
        cells = sorted(by_column[19])

        for cell_idx in cells:
            row = cell_idx // 20
            changes = cell_changes[cell_idx]

            # Get the specific bytes that changed
            changed_bytes = {b: (old, new) for b, old, new in changes}

            print(f"\nRow {row:2d} (cell {cell_idx}):")
            for byte_idx in sorted(changed_bytes.keys()):
                old, new = changed_bytes[byte_idx]
                print(f"  Byte {byte_idx}: 0x{old:02X} -> 0x{new:02X}")

    # Analyze byte positions
    print()
    print("="*70)
    print("BYTE POSITION ANALYSIS:")
    print("="*70)
    print()

    byte_pos_counts = {}
    for cell_idx, changes in cell_changes.items():
        for byte_idx, old, new in changes:
            if byte_idx not in byte_pos_counts:
                byte_pos_counts[byte_idx] = 0
            byte_pos_counts[byte_idx] += 1

    print("Which byte positions changed most frequently:")
    for byte_idx in sorted(byte_pos_counts.keys()):
        count = byte_pos_counts[byte_idx]
        print(f"  Byte {byte_idx}: changed in {count} cells")

    print()
    print("="*70)
    print("HYPOTHESIS:")
    print("If horizontal walls were added between each row in column 19,")
    print("we'd expect to see changes in:")
    print("  - Cells (0,19), (1,19), (2,19), ... (19,19) = 20 cells")
    print("  - OR their northern neighbors if walls are stored in the cell above")
    print("="*70)

if __name__ == "__main__":
    main()
