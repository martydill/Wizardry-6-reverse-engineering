#!/usr/bin/env python3
"""
Wizardry 6 - Find Map 10 in SCENARIO.DBS
Scans the scenario file to locate map 10 (16x16).
"""

import sys
from pathlib import Path

def analyze_wall_distribution(cells, width, height):
    """Analyze which cells contain wall data."""
    cells_with_walls = []

    for cell_idx in range(min(len(cells), width * height)):
        if cell_idx >= len(cells):
            break

        file_col = cell_idx // height  # Column-major
        file_row = cell_idx % height

        cell = cells[cell_idx]
        has_walls = False
        wall_bytes = []

        # Check all ODD bytes for wall bits
        for byte_idx in range(1, min(20, len(cell)), 2):
            byte_val = cell[byte_idx]

            if byte_val & 0xA0:  # Has bit 5 or 7
                has_walls = True
                wall_bytes.append((byte_idx, byte_val))

        if has_walls:
            cells_with_walls.append({
                'cell_idx': cell_idx,
                'file_row': file_row,
                'file_col': file_col,
                'wall_bytes': wall_bytes
            })

    return cells_with_walls

def scan_for_maps(data, bytes_per_cell=20):
    """Scan the file for map-like structures."""
    results = []

    # Try different map sizes
    map_sizes = [
        (16, 16, "16x16 (256 cells)"),
        (20, 20, "20x20 (400 cells)"),
        (28, 28, "28x28 (784 cells)"),
    ]

    # Scan at regular intervals (every 1KB)
    for offset in range(0, len(data), 1024):
        for width, height, desc in map_sizes:
            cells_needed = width * height
            bytes_needed = cells_needed * bytes_per_cell

            if offset + bytes_needed > len(data):
                continue

            # Extract cells
            cells = []
            valid = True
            for i in range(cells_needed):
                start = offset + i * bytes_per_cell
                end = start + bytes_per_cell
                if end > len(data):
                    valid = False
                    break
                cells.append(data[start:end])

            if not valid:
                continue

            # Analyze for walls
            walls = analyze_wall_distribution(cells, width, height)

            # If we find a decent number of walls, this might be a map
            if 20 <= len(walls) <= cells_needed:
                results.append({
                    'offset': offset,
                    'size': (width, height),
                    'desc': desc,
                    'wall_count': len(walls),
                    'cells': cells,
                    'walls': walls
                })

    return results

def main():
    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Map 10 Finder")
    print("="*60)
    print()

    # Read the whole file
    with open(filepath, 'rb') as f:
        data = f.read()

    file_size = len(data)
    print(f"SCENARIO.DBS size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print()

    print("Scanning for map structures...")
    print("(Looking for regions with 20-80% cells containing wall data)")
    print()

    results = scan_for_maps(data)

    print(f"Found {len(results)} potential maps")
    print()

    # Show the most promising candidates
    for i, result in enumerate(results[:20]):  # Show first 20
        print(f"Map candidate #{i+1}:")
        print(f"  Offset: {result['offset']:6d} (0x{result['offset']:05X})")
        print(f"  Size: {result['desc']}")
        print(f"  Walls: {result['wall_count']} cells with wall data")

        # Show wall distribution by column
        walls = result['walls']
        width, height = result['size']

        col_counts = {}
        for w in walls:
            col = w['file_col']
            col_counts[col] = col_counts.get(col, 0) + 1

        # Show a compact view
        cols_with_walls = sorted(col_counts.keys())
        if len(cols_with_walls) > 0:
            print(f"  Columns with walls: {min(cols_with_walls)}-{max(cols_with_walls)} ({len(cols_with_walls)} total)")

        print()

    print("="*60)
    print()

    # Let's specifically look for 16x16 maps
    maps_16x16 = [r for r in results if r['size'] == (16, 16)]

    if len(maps_16x16) > 0:
        print(f"Found {len(maps_16x16)} potential 16x16 maps:")
        print()

        for i, result in enumerate(maps_16x16[:10]):
            print(f"16x16 Map #{i+1}:")
            print(f"  Offset: {result['offset']:6d} (0x{result['offset']:05X})")
            print(f"  Walls: {result['wall_count']} cells")

            # If this is around the 10th map, it might be map 10
            # Let's estimate which map number this might be
            offset = result['offset']
            # Rough estimate: if maps average 6-8KB each
            estimated_map_num = offset // 6000
            print(f"  Estimated map #: ~{estimated_map_num}")
            print()

    # Try specific offsets based on structure
    # SCENARIO.DBS might have a header, then maps
    # Let's try some educated guesses for where map 10 might be
    print("="*60)
    print("Trying specific offsets for Map 10:")
    print()

    # Map 10 as 16x16 would be 5120 bytes
    # If maps average 8000 bytes, map 10 would be around offset 80000
    # But if maps vary in size, we need to scan more carefully

    # Try reading at common map boundaries
    test_offsets = [
        40960,  # 40KB
        49152,  # 48KB
        57344,  # 56KB
        65536,  # 64KB
        73728,  # 72KB
    ]

    for offset in test_offsets:
        if offset + 5120 > file_size:
            continue

        print(f"Offset {offset:6d} (0x{offset:05X}):")

        # Try as 16x16
        cells = []
        for i in range(256):
            start = offset + i * 20
            end = start + 20
            if end <= file_size:
                cells.append(data[start:end])

        walls = analyze_wall_distribution(cells, 16, 16)
        print(f"  16x16: {len(walls):3d} cells with walls")

        if len(walls) > 20:
            # Show distribution
            col_counts = {}
            for w in walls:
                col = w['file_col']
                col_counts[col] = col_counts.get(col, 0) + 1

            cols_with_walls = sorted(col_counts.keys())
            if len(cols_with_walls) > 0:
                print(f"    Columns: {min(cols_with_walls)}-{max(cols_with_walls)}")

                # Show sample wall data
                print(f"    Sample cell {walls[0]['cell_idx']} (row={walls[0]['file_row']}, col={walls[0]['file_col']}):")
                for byte_idx, byte_val in walls[0]['wall_bytes'][:3]:
                    print(f"      Byte {byte_idx:2d}: 0x{byte_val:02X}")

        print()

if __name__ == "__main__":
    main()
