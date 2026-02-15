#!/usr/bin/env python3
"""
Wizardry 6 - Analyze Map 10 Byte Usage
Deep dive into which cells use which bytes to understand the encoding.
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
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def analyze_byte_usage_by_file_row(cells, width, height):
    """Analyze which bytes are used in cells at each file row."""

    # For each file row, track which bytes have walls
    row_byte_usage = {}

    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height  # Column-major
        file_row = cell_idx % height

        if file_row not in row_byte_usage:
            row_byte_usage[file_row] = {byte_idx: 0 for byte_idx in range(1, 20, 2)}

        cell = cells[cell_idx]

        # Check all ODD bytes
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]
            if byte_val & 0xA0:  # Has bit 5 or 7
                row_byte_usage[file_row][byte_idx] += 1

    return row_byte_usage

def main():
    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Map 10 Byte Usage Analysis")
    print("="*60)
    print()

    # Load map 10 (16x16)
    offset = 40960
    width = 16
    height = 16

    cells = read_map_data(filepath, offset, width, height)

    # Analyze byte usage by file row
    row_byte_usage = analyze_byte_usage_by_file_row(cells, width, height)

    print("Byte usage by file row:")
    print("(Shows how many cells in each file row use each byte)")
    print()
    print("File Row | Bytes 1  3  5  7  9 11 13 15 17 19")
    print("---------+-----------------------------------")

    for file_row in range(height):
        usage = row_byte_usage.get(file_row, {})
        counts = [usage.get(b, 0) for b in range(1, 20, 2)]
        counts_str = ' '.join(f'{c:2d}' for c in counts)
        print(f"   {file_row:2d}    | {counts_str}")

    print()
    print("="*60)
    print()

    # Look for patterns
    print("PATTERN ANALYSIS:")
    print("-"*60)
    print()

    # Hypothesis: File row N might be responsible for game row N
    # and the bytes used tell us which Y-positions have walls

    print("Hypothesis: File row N stores walls for game row N")
    print()
    print("If true, we'd expect:")
    print("  - File row 0: uses byte 1 (rows 0-1)")
    print("  - File row 1: uses byte 1 (rows 0-1)")
    print("  - File row 2: uses byte 3 (rows 2-3)")
    print("  - File row 3: uses byte 3 (rows 2-3)")
    print("  - etc.")
    print()

    # Check which byte each row uses most
    print("Which byte is used MOST in each file row:")
    print()

    for file_row in range(height):
        usage = row_byte_usage.get(file_row, {})
        if usage:
            max_byte = max(usage, key=usage.get)
            max_count = usage[max_byte]
            row_range = f"{(max_byte-1)//2*2}-{(max_byte-1)//2*2+1}"
            print(f"  File row {file_row:2d}: byte {max_byte:2d} ({max_count} cells) = game rows {row_range}")

    print()
    print("="*60)
    print()

    # Alternative hypothesis: maybe the byte that corresponds to the file row
    print("Alternative check: Does file row use its 'own' byte most?")
    print()
    print("File Row | Expected Byte | Actual Most Used | Match?")
    print("---------+---------------+------------------+-------")

    for file_row in range(height):
        # Expected byte for this row: byte 1 for rows 0-1, byte 3 for rows 2-3, etc.
        expected_byte = (file_row // 2) * 2 + 1

        usage = row_byte_usage.get(file_row, {})
        if usage:
            max_byte = max(usage, key=usage.get)
            max_count = usage[max_byte]
            match = "YES" if max_byte == expected_byte else "NO"
            print(f"   {file_row:2d}    |      {expected_byte:2d}       |      {max_byte:2d} ({max_count:2d})     | {match}")
        else:
            print(f"   {file_row:2d}    |      {expected_byte:2d}       |      --          | --")

    print()
    print("="*60)
    print()

    # Count total usage of bytes 17 and 19 (which shouldn't exist in 16x16)
    total_byte_17 = sum(row_byte_usage[r][17] for r in range(height) if 17 in row_byte_usage[r])
    total_byte_19 = sum(row_byte_usage[r][19] for r in range(height) if 19 in row_byte_usage[r])

    print(f"Byte 17 usage (rows 16-17): {total_byte_17} cell-occurrences")
    print(f"Byte 19 usage (rows 18-19): {total_byte_19} cell-occurrences")
    print()
    print("These bytes represent rows BEYOND the 16x16 map!")
    print("This suggests:")
    print("  1. The encoding might wrap around, OR")
    print("  2. Cells store redundant data, OR")
    print("  3. The map file format is standardized for 20x20 regardless of actual size")

if __name__ == "__main__":
    main()
