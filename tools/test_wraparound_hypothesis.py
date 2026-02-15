#!/usr/bin/env python3
"""
Wizardry 6 - Test Wraparound Hypothesis
Tests if bytes 17-19 in 16x16 map wrap around to rows 0-5.
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

def test_wraparound(cells, width, height):
    """Test if bytes 17-19 wrap to rows 0-5."""

    print("Wraparound Hypothesis:")
    print("  Byte 17 (rows 16-17) -> wraps to rows 0-1 (byte 1)")
    print("  Byte 19 (rows 18-19) -> wraps to rows 2-3 (byte 3)")
    print()
    print("Testing by comparing byte values...")
    print()

    # For each cell, compare:
    # - Byte 1 vs Byte 17
    # - Byte 3 vs Byte 19

    matches_17_to_1 = 0
    matches_19_to_3 = 0
    total_cells_checked = 0

    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height
        file_row = cell_idx % height

        cell = cells[cell_idx]

        byte_1 = cell[1]
        byte_3 = cell[3]
        byte_17 = cell[17]
        byte_19 = cell[19]

        # Check if byte 17 matches byte 1 (both have same walls)
        if (byte_17 & 0xA0) != 0 or (byte_1 & 0xA0) != 0:
            total_cells_checked += 1
            if (byte_17 & 0xA0) == (byte_1 & 0xA0):
                matches_17_to_1 += 1

        # Check if byte 19 matches byte 3
        if (byte_19 & 0xA0) != 0 or (byte_3 & 0xA0) != 0:
            if (byte_19 & 0xA0) == (byte_3 & 0xA0):
                matches_19_to_3 += 1

    print(f"Byte 17 vs Byte 1: {matches_17_to_1} matches (out of cells with walls in either)")
    print(f"Byte 19 vs Byte 3: {matches_19_to_3} matches")
    print()

    if matches_17_to_1 > total_cells_checked * 0.5:
        print("STRONG CORRELATION! Bytes 17 and 1 match frequently.")
    else:
        print("No strong correlation between bytes 17 and 1.")

    print()
    print("="*60)
    print()

    # Sample some cells that have both byte 1 and byte 17 set
    print("Sample cells with both byte 1 AND byte 17:")
    print()

    sample_count = 0
    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height
        file_row = cell_idx % height

        cell = cells[cell_idx]

        byte_1 = cell[1]
        byte_17 = cell[17]

        if (byte_1 & 0xA0) and (byte_17 & 0xA0):
            print(f"Cell {cell_idx} (row={file_row}, col={file_col}):")
            print(f"  Byte  1: 0x{byte_1:02X} (bits: 5={'Y' if byte_1 & 0x20 else 'N'} 7={'Y' if byte_1 & 0x80 else 'N'})")
            print(f"  Byte 17: 0x{byte_17:02X} (bits: 5={'Y' if byte_17 & 0x20 else 'N'} 7={'Y' if byte_17 & 0x80 else 'N'})")

            if (byte_1 & 0xA0) == (byte_17 & 0xA0):
                print("  MATCH!")
            else:
                print("  Different")

            print()

            sample_count += 1
            if sample_count >= 10:
                break

def main():
    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Wraparound Hypothesis Test")
    print("="*60)
    print()

    offset = 40960
    width = 16
    height = 16

    cells = read_map_data(filepath, offset, width, height)
    test_wraparound(cells, width, height)

if __name__ == "__main__":
    main()
