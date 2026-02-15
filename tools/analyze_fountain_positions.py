#!/usr/bin/env python3
"""
Wizardry 6 - Analyze Fountain Positions
Checks if byte 18 = 0xA0 marks the 4 corner fountains.
"""

import sys
from pathlib import Path

def read_map_data(filepath, offset, width, height, bytes_per_cell=20):
    """Read map data from specific offset."""
    total_cells = width * height

    with open(filepath, 'rb') as f:
        f.seek(offset)
        data = f.read(total_cells * bytes_per_cell)

    cells = []
    for i in range(total_cells):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])

    return cells

def main():
    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Fountain Position Analysis")
    print("="*60)
    print()

    offset = 40960
    width = 16
    height = 16

    cells = read_map_data(filepath, offset, width, height)

    # Find cells with byte 18 = 0xA0 (the value that appears exactly 4 times)
    print("Cells with byte 18 = 0xA0:")
    print()

    fountain_cells = []
    for cell_idx in range(len(cells)):
        if cells[cell_idx][18] == 0xA0:
            file_col = cell_idx // height
            file_row = cell_idx % height
            fountain_cells.append((cell_idx, file_row, file_col))

    for cell_idx, file_row, file_col in fountain_cells:
        print(f"Cell {cell_idx:3d}: file_row={file_row:2d}, file_col={file_col:2d}")

        # Show full cell data
        cell = cells[cell_idx]
        print(f"  Even bytes: {' '.join(f'{cell[i]:02X}' for i in range(0, 20, 2))}")
        print(f"  Odd bytes:  {' '.join(f'{cell[i]:02X}' for i in range(1, 20, 2))}")
        print()

    print("="*60)
    print()

    # Expected corners (game coordinates):
    # Top-left: (0, 0)
    # Top-right: (15, 0)
    # Bottom-left: (0, 15)
    # Bottom-right: (15, 15)

    print("ANALYSIS:")
    print("-"*60)
    print()

    if len(fountain_cells) == 4:
        print("Found exactly 4 fountains! ✓")
        print()

        # Check if they're at expected columns
        file_cols = [fc[2] for fc in fountain_cells]
        print(f"File columns: {sorted(file_cols)}")

        if 0 in file_cols and 15 in file_cols:
            print("  Contains columns 0 and 15 (left and right edges) ✓")

            # Count how many are at each column
            col_0_count = file_cols.count(0)
            col_15_count = file_cols.count(15)

            print(f"  Column 0: {col_0_count} fountains (should be 2 for top-left and bottom-left)")
            print(f"  Column 15: {col_15_count} fountains (should be 2 for top-right and bottom-right)")
            print()

            # Look at file rows for column 0
            col_0_rows = [fc[1] for fc in fountain_cells if fc[2] == 0]
            col_15_rows = [fc[1] for fc in fountain_cells if fc[2] == 15]

            print(f"Column 0 file rows: {col_0_rows}")
            print(f"Column 15 file rows: {col_15_rows}")
            print()

            # If file_row directly mapped to game_row:
            # Top-left (game row 0) → file_row should be 0
            # Bottom-left (game row 15) → file_row should be 15
            # Top-right (game row 0) → file_row should be 0
            # Bottom-right (game row 15) → file_row should be 15

            print("If file_row = game_row (simple mapping):")
            print(f"  Expected: col 0 rows [0, 15], col 15 rows [0, 15]")
            print(f"  Actual:   col 0 rows {sorted(col_0_rows)}, col 15 rows {sorted(col_15_rows)}")

            if col_0_rows == [0, 15] or set(col_0_rows) == {0, 15}:
                print("  Column 0 MATCHES simple mapping! ✓")
            else:
                print("  Column 0 does NOT match simple mapping")

            if col_15_rows == [0, 15] or set(col_15_rows) == {0, 15}:
                print("  Column 15 MATCHES simple mapping! ✓")
            else:
                print("  Column 15 does NOT match simple mapping")

        else:
            print("  Does NOT contain both columns 0 and 15")
            print("  This might not be the fountain marker, or column mapping is different")

    else:
        print(f"Found {len(fountain_cells)} fountains (expected 4)")
        print("Byte 18 = 0xA0 might not be the fountain marker")

    print()
    print("="*60)
    print()

    # Try other candidates
    print("Checking other potential fountain markers:")
    print()

    # Check other bytes that have exactly 4 occurrences of some value
    candidates = [
        (0, 0x0A), (0, 0x02), (0, 0xA0),
        (17, 0x07),
    ]

    for byte_idx, value in candidates:
        print(f"Byte {byte_idx}, value 0x{value:02X}:")

        cells_with_value = []
        for cell_idx in range(len(cells)):
            if cells[cell_idx][byte_idx] == value:
                file_col = cell_idx // height
                file_row = cell_idx % height
                cells_with_value.append((cell_idx, file_row, file_col))

        if len(cells_with_value) == 4:
            file_cols = [c[2] for c in cells_with_value]
            file_rows = [c[1] for c in cells_with_value]

            print(f"  Found 4 cells: {[(r, c) for _, r, c in cells_with_value]}")
            print(f"  Columns: {sorted(set(file_cols))}")
            print(f"  Rows: {sorted(set(file_rows))}")

            # Check if it's corner-like
            if 0 in file_cols and 15 in file_cols:
                print(f"  ✓ Has left and right edges!")
        else:
            print(f"  Found {len(cells_with_value)} cells (not 4)")

        print()

if __name__ == "__main__":
    main()
