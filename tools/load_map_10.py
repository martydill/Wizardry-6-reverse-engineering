#!/usr/bin/env python3
"""
Wizardry 6 - Load Map 10 (16x16)
Explores map 10 to understand coordinate mapping system.
"""

import sys
from pathlib import Path

def read_map_data(filepath, map_number=0, map_width=20, map_height=20, bytes_per_cell=20):
    """Read map data for a specific map number."""
    total_cells = map_width * map_height
    map_size = total_cells * bytes_per_cell

    with open(filepath, 'rb') as f:
        # Maps are stored sequentially in the save file
        # Map 0 starts at offset 0
        offset = map_number * map_size
        f.seek(offset)
        data = f.read(map_size)

    cells = []
    for i in range(total_cells):
        start = i * bytes_per_cell
        end = start + bytes_per_cell
        if end <= len(data):
            cells.append(data[start:end])
        else:
            cells.append(bytes([0] * bytes_per_cell))

    return cells

def analyze_wall_distribution(cells, width, height):
    """Analyze which cells contain wall data."""
    cells_with_walls = []

    for cell_idx in range(len(cells)):
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

def main():
    filepath = Path("gamedata/NEWGAME.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Map 10 Loader")
    print("="*60)
    print()

    # First, let's check the file size
    file_size = filepath.stat().st_size
    print(f"File size: {file_size:,} bytes")
    print()

    # Try to load map 10 as 16x16
    print("Attempting to load Map 10 (16x16)...")
    print()

    # We need to figure out where map 10 starts
    # If maps are stored sequentially:
    #   Map 0: 20x20 = 400 cells = 8000 bytes
    #   Map 1-9: Unknown sizes

    # Let's try different offsets
    # First, assume all maps are 20x20 until map 10
    offset_if_all_20x20 = 10 * (20 * 20 * 20)  # 10 maps × 400 cells × 20 bytes
    print(f"If all maps 0-9 are 20x20: offset = {offset_if_all_20x20:,} bytes")

    # Check if that's within file bounds
    if offset_if_all_20x20 < file_size:
        print("  > Within file bounds, trying this offset...")

        # Read from this offset
        with open(filepath, 'rb') as f:
            f.seek(offset_if_all_20x20)
            preview = f.read(100)

        print(f"  > First 100 bytes at offset {offset_if_all_20x20}:")
        print("    ", ' '.join(f'{b:02X}' for b in preview[:50]))
        print("    ", ' '.join(f'{b:02X}' for b in preview[50:100]))
    else:
        print("  > BEYOND file bounds!")

    print()
    print("Alternative: Map 10 might start after different offsets")
    print("Let's scan for map headers...")
    print()

    # Scan for potential map starts by looking for patterns
    # A 16x16 map should have 256 cells = 5120 bytes
    # Let's look for regions with consistent cell structure

    with open(filepath, 'rb') as f:
        data = f.read()

    # Try reading map 10 with 16x16 dimensions
    # Common map sizes in Wizardry: 16x16, 20x20, 28x28
    map_10_sizes = [
        (16, 16),  # 256 cells = 5120 bytes
        (20, 20),  # 400 cells = 8000 bytes
        (28, 28),  # 784 cells = 15680 bytes
    ]

    print("Trying different map sizes for Map 10:")
    print()

    for width, height in map_10_sizes:
        cells_needed = width * height
        bytes_needed = cells_needed * 20

        print(f"{width}x{height}: {cells_needed} cells = {bytes_needed} bytes")

        # Try reading at different offsets
        # Offset 0: Map 0 (20x20) = 8000 bytes
        # We don't know sizes of maps 1-9, so let's try some educated guesses

        test_offsets = [
            8000,      # Right after map 0
            16000,     # If map 1 is also 20x20
            24000,     # If maps 0-2 are 20x20
            80000,     # If maps 0-9 are all 20x20
        ]

        for offset in test_offsets:
            if offset + bytes_needed <= file_size:
                # Try reading map at this offset
                cells = []
                for i in range(cells_needed):
                    start = offset + i * 20
                    end = start + 20
                    if end <= file_size:
                        cells.append(data[start:end])

                # Analyze for walls
                walls = analyze_wall_distribution(cells, width, height)

                if len(walls) > 0:
                    print(f"  Offset {offset:6d}: {len(walls):3d} cells with walls")

    print()
    print("="*60)
    print("Interactive offset explorer:")
    print("Let me try to find map 10 by scanning the file structure...")
    print()

    # Let's look for a signature that might indicate map boundaries
    # In save files, there might be headers or separators

    # Try the most likely scenario: Map 10 starts at 80000 (10 × 8000)
    likely_offset = 10 * 8000

    if likely_offset + 5120 <= file_size:
        print(f"Reading Map 10 from offset {likely_offset} (assuming 16x16)...")

        cells = []
        for i in range(256):
            start = likely_offset + i * 20
            end = start + 20
            cells.append(data[start:end])

        walls = analyze_wall_distribution(cells, 16, 16)

        print(f"Found {len(walls)} cells with wall data")
        print()

        if len(walls) > 0:
            print("Wall distribution by file column:")
            col_counts = {}
            for w in walls:
                col = w['file_col']
                col_counts[col] = col_counts.get(col, 0) + 1

            for col in sorted(col_counts.keys()):
                rows = [w['file_row'] for w in walls if w['file_col'] == col]
                print(f"  Column {col:2d}: {col_counts[col]:2d} cells - rows {min(rows)}-{max(rows)}")

            print()
            print("Sample wall data:")
            for i, w in enumerate(walls[:5]):
                print(f"  Cell {w['cell_idx']:3d} (file row={w['file_row']:2d}, col={w['file_col']:2d}):")
                for byte_idx, byte_val in w['wall_bytes']:
                    print(f"    Byte {byte_idx:2d}: 0x{byte_val:02X} = {bin(byte_val)}")

if __name__ == "__main__":
    main()
