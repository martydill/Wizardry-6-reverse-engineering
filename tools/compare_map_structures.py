#!/usr/bin/env python3
"""
Wizardry 6 - Compare Map Structures
Compares wall encoding between 16x16 and 20x20 maps to find coordinate mapping pattern.
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

def analyze_cell_wall_bytes(cells, width, height):
    """Analyze which cells have walls in which bytes."""
    analysis = []

    for cell_idx in range(min(len(cells), width * height)):
        file_col = cell_idx // height  # Column-major
        file_row = cell_idx % height

        cell = cells[cell_idx]
        wall_bytes = {}

        # Check all ODD bytes
        for byte_idx in range(1, 20, 2):
            byte_val = cell[byte_idx]
            if byte_val & 0xA0:  # Has bit 5 or 7
                wall_bytes[byte_idx] = byte_val

        if wall_bytes:
            analysis.append({
                'cell_idx': cell_idx,
                'file_row': file_row,
                'file_col': file_col,
                'wall_bytes': wall_bytes
            })

    return analysis

def main():
    # Load map 0 (20x20) from NEWGAME.DBS
    map0_path = Path("gamedata/NEWGAME.DBS")
    map0_cells = []
    if map0_path.exists():
        map0_cells = read_map_data(map0_path, 0, 20, 20)

    # Load map 10 (16x16) from SCENARIO.DBS
    map10_path = Path("gamedata/SCENARIO.DBS")
    map10_cells = []
    if map10_path.exists():
        map10_cells = read_map_data(map10_path, 40960, 16, 16)

    print("Wizardry 6 - Map Structure Comparison")
    print("="*60)
    print()

    # Analyze both maps
    print("Map 0 (20x20) - Analysis:")
    print("-"*60)
    map0_analysis = analyze_cell_wall_bytes(map0_cells, 20, 20)
    print(f"Cells with walls: {len(map0_analysis)}/400")
    print()

    # Show distribution by file column
    col_dist_map0 = {}
    for item in map0_analysis:
        col = item['file_col']
        col_dist_map0[col] = col_dist_map0.get(col, 0) + 1

    print("Distribution by file column:")
    for col in sorted(col_dist_map0.keys()):
        count = col_dist_map0[col]
        rows = [item['file_row'] for item in map0_analysis if item['file_col'] == col]
        print(f"  Col {col:2d}: {count:3d} cells - rows {min(rows)}-{max(rows)}")

    print()
    print("="*60)
    print()

    print("Map 10 (16x16) - Analysis:")
    print("-"*60)
    map10_analysis = analyze_cell_wall_bytes(map10_cells, 16, 16)
    print(f"Cells with walls: {len(map10_analysis)}/256")
    print()

    # Show distribution by file column
    col_dist_map10 = {}
    for item in map10_analysis:
        col = item['file_col']
        col_dist_map10[col] = col_dist_map10.get(col, 0) + 1

    print("Distribution by file column:")
    for col in sorted(col_dist_map10.keys()):
        count = col_dist_map10[col]
        rows = [item['file_row'] for item in map10_analysis if item['file_col'] == col]
        print(f"  Col {col:2d}: {count:3d} cells - rows {min(rows)}-{max(rows)}")

    print()
    print("="*60)
    print()

    # Compare patterns
    print("COMPARISON:")
    print("-"*60)

    print(f"Map 0 (20x20): {len(col_dist_map0)} file columns have walls")
    print(f"Map 10 (16x16): {len(col_dist_map10)} file columns have walls")
    print()

    # For map 10, let's look at the relationship between file column and game column
    # If file column = game column, we should see walls spread across columns 0-15
    # If there's a different mapping, we might see a different pattern

    print("Hypothesis testing:")
    print()
    print("1. Simple mapping (file col = game col):")
    print(f"   Expected columns with walls: 0-15")
    print(f"   Actual columns with walls: {min(col_dist_map10.keys())}-{max(col_dist_map10.keys())}")
    if set(col_dist_map10.keys()) == set(range(16)):
        print("   MATCH! All 16 columns have walls.")
    else:
        missing = set(range(16)) - set(col_dist_map10.keys())
        extra = set(col_dist_map10.keys()) - set(range(16))
        if missing:
            print(f"   Missing columns: {sorted(missing)}")
        if extra:
            print(f"   Extra columns: {sorted(extra)}")

    print()

    # Look at byte patterns
    print("2. Byte usage patterns:")
    print()

    # Count which bytes are used in each map
    bytes_map0 = set()
    for item in map0_analysis:
        bytes_map0.update(item['wall_bytes'].keys())

    bytes_map10 = set()
    for item in map10_analysis:
        bytes_map10.update(item['wall_bytes'].keys())

    print(f"   Map 0 uses bytes: {sorted(bytes_map0)}")
    print(f"   Map 10 uses bytes: {sorted(bytes_map10)}")
    print()

    # For map 10 (16 rows), we'd expect to use bytes 1-15
    # (byte 1 = rows 0-1, ..., byte 15 = rows 14-15)
    expected_bytes_16x16 = list(range(1, 16, 2))  # [1,3,5,7,9,11,13,15]
    print(f"   Expected for 16x16: {expected_bytes_16x16}")

    if bytes_map10 == set(expected_bytes_16x16):
        print("   MATCH! Byte usage matches 16x16 map.")
    else:
        missing = set(expected_bytes_16x16) - bytes_map10
        extra = bytes_map10 - set(expected_bytes_16x16)
        if missing:
            print(f"   Missing bytes: {sorted(missing)}")
        if extra:
            print(f"   Extra bytes (should not be used): {sorted(extra)}")

    print()
    print("="*60)
    print()

    # Sample some cells to show the data
    print("SAMPLE DATA:")
    print("-"*60)
    print()

    print("Map 10 - First 5 cells with walls:")
    for i, item in enumerate(map10_analysis[:5]):
        print(f"Cell {item['cell_idx']:3d} (file row={item['file_row']:2d}, col={item['file_col']:2d}):")
        for byte_idx in sorted(item['wall_bytes'].keys()):
            byte_val = item['wall_bytes'][byte_idx]
            bits = f"bit5={'Y' if byte_val & 0x20 else 'N'} bit7={'Y' if byte_val & 0x80 else 'N'}"
            row_range = f"rows {(byte_idx-1)//2*2}-{(byte_idx-1)//2*2+1}"
            print(f"  Byte {byte_idx:2d} ({row_range}): 0x{byte_val:02X} ({bits})")
        print()

if __name__ == "__main__":
    main()
