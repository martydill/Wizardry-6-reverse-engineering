#!/usr/bin/env python3
"""
Investigate the actual data structure by analyzing the offset patterns.
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

    # Find all differences
    diffs = []
    for i in range(min(len(data_new), len(data_old))):
        if data_new[i] != data_old[i]:
            diffs.append((i, data_old[i], data_new[i]))

    print("Analyzing offset patterns for horizontal walls in rightmost column")
    print("="*80)
    print()

    print(f"Total differences: {len(diffs)}")
    print()

    # Show the offsets
    print("Offsets where data changed:")
    print("-"*80)

    for offset, old, new in diffs:
        print(f"0x{offset:04X} ({offset:5d}): 0x{old:02X} -> 0x{new:02X}  (XOR: {old^new:02X})")

    # Calculate spacing between changes
    print()
    print("="*80)
    print("Spacing analysis:")
    print("="*80)
    print()

    offsets = [d[0] for d in diffs]

    print("Offset differences (sequential):")
    for i in range(1, len(offsets)):
        diff = offsets[i] - offsets[i-1]
        print(f"  {offsets[i-1]:04X} -> {offsets[i]:04X}: gap of {diff:3d} (0x{diff:02X}) bytes")

    # Look for patterns
    print()
    print("="*80)
    print("Looking for patterns:")
    print("="*80)
    print()

    # Group by similar spacing
    gaps = {}
    for i in range(1, len(offsets)):
        gap = offsets[i] - offsets[i-1]
        if gap not in gaps:
            gaps[gap] = []
        gaps[gap].append((offsets[i-1], offsets[i]))

    print("Gaps and their frequencies:")
    for gap in sorted(gaps.keys()):
        count = len(gaps[gap])
        print(f"  Gap of {gap:3d} (0x{gap:02X}): occurs {count} times")

    # Most common gap
    most_common_gap = max(gaps.keys(), key=lambda k: len(gaps[k]))
    print(f"\nMost common gap: {most_common_gap} bytes (occurs {len(gaps[most_common_gap])} times)")

    # Check if it's a regular pattern
    print()
    print("="*80)
    print("Testing regular patterns:")
    print("="*80)
    print()

    # Try different byte-per-cell values
    for bytes_per_cell in [2, 4, 8, 10, 16, 20, 32]:
        print(f"\nIf each cell is {bytes_per_cell} bytes:")

        # Calculate which cells would be affected
        cells_affected = set()
        for offset, _, _ in diffs:
            cell_idx = offset // bytes_per_cell
            byte_in_cell = offset % bytes_per_cell
            cells_affected.add(cell_idx)

        print(f"  Affects {len(cells_affected)} distinct cells")

        # If 20x20 grid, show which rows/columns
        if len(cells_affected) <= 20:  # Reasonable number to display
            print(f"  Cell indices: {sorted(cells_affected)}")

            # Try different grid widths
            for grid_width in [10, 16, 20, 32]:
                rows = set()
                cols = set()
                for cell_idx in cells_affected:
                    row = cell_idx // grid_width
                    col = cell_idx % grid_width
                    rows.add(row)
                    cols.add(col)

                if len(cols) == 1:  # All in same column!
                    col_val = list(cols)[0]
                    print(f"    Grid width {grid_width}: ALL changes in COLUMN {col_val}! (rows {min(rows)}-{max(rows)})")
                elif len(rows) == 1:  # All in same row!
                    row_val = list(rows)[0]
                    print(f"    Grid width {grid_width}: ALL changes in ROW {row_val}! (cols {min(cols)}-{max(cols)})")

    # Special analysis: check if the pattern matches "19 horizontal walls"
    print()
    print("="*80)
    print("Expected pattern for 19 horizontal walls in rightmost column:")
    print("="*80)
    print()
    print("If column 19 in a 20-wide grid, and we need to mark walls between rows,")
    print("we'd expect either:")
    print("  - 19 cells affected (one for each gap between rows)")
    print("  - 20 cells affected (if walls stored in both adjacent cells)")
    print("  - Changes in a vertical line in the data structure")
    print()
    print(f"Actual: {len(set(d[0]//8 for d in diffs))} cells affected (assuming 8 bytes/cell)")

    # Look at the actual byte positions that changed
    print()
    print("="*80)
    print("Which byte within each cell changed:")
    print("="*80)
    print()

    for bytes_per_cell in [8, 10]:
        print(f"\nAssuming {bytes_per_cell} bytes per cell:")
        byte_positions = {}
        for offset, _, _ in diffs:
            byte_in_cell = offset % bytes_per_cell
            if byte_in_cell not in byte_positions:
                byte_positions[byte_in_cell] = 0
            byte_positions[byte_in_cell] += 1

        print(f"  Byte position frequencies:")
        for pos in sorted(byte_positions.keys()):
            count = byte_positions[pos]
            print(f"    Byte {pos}: {count} times")

if __name__ == "__main__":
    main()
