#!/usr/bin/env python3
"""
Wizardry 6 - Find Fountain Encoding
Compares map 10 before/after adding fountains to decode their format.
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

def compare_maps(cells_before, cells_after, width, height):
    """Find all cells that changed between two versions."""
    changes = []

    for cell_idx in range(min(len(cells_before), len(cells_after), width * height)):
        file_col = cell_idx // height
        file_row = cell_idx % height

        cell_before = cells_before[cell_idx]
        cell_after = cells_after[cell_idx]

        # Check each byte
        byte_changes = []
        for byte_idx in range(20):
            if cell_before[byte_idx] != cell_after[byte_idx]:
                byte_changes.append({
                    'byte': byte_idx,
                    'before': cell_before[byte_idx],
                    'after': cell_after[byte_idx]
                })

        if byte_changes:
            changes.append({
                'cell_idx': cell_idx,
                'file_row': file_row,
                'file_col': file_col,
                'changes': byte_changes
            })

    return changes

def main():
    # For now, let's assume we have a backup of the original map
    # We'll read the current map and look for patterns

    filepath = Path("gamedata/SCENARIO.DBS")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 - Fountain Encoding Finder")
    print("="*60)
    print()

    offset = 40960
    width = 16
    height = 16

    # Read current map (with fountains)
    print("Reading current map (with fountains)...")
    cells_current = read_map_data(filepath, offset, width, height)

    # Since we don't have a backup, let's look for patterns
    # Fountains in corners should be at:
    # - Top-left: (0, 0)
    # - Top-right: (15, 0)
    # - Bottom-left: (0, 15)
    # - Bottom-right: (15, 15)

    # If file_col = game_col, then:
    # - Top-left: file_col=0, game_row=0
    # - Top-right: file_col=15, game_row=0
    # - Bottom-left: file_col=0, game_row=15
    # - Bottom-right: file_col=15, game_row=15

    # With column-major storage:
    # - Top-left: cell = 0*16 + row
    # - Top-right: cell = 15*16 + row
    # - Bottom-left: cell = 0*16 + row
    # - Bottom-right: cell = 15*16 + row

    print("Expected corner positions (if file_col = game_col):")
    print()

    corners = [
        ("Top-left (0,0)", 0, 0),
        ("Top-right (15,0)", 15, 0),
        ("Bottom-left (0,15)", 0, 15),
        ("Bottom-right (15,15)", 15, 15)
    ]

    for name, game_col, game_row in corners:
        # Possible file positions for this game position
        # If file_col = game_col, we need to figure out file_row

        # Try simple mapping first: file_row = game_row
        file_col = game_col
        file_row = game_row
        cell_idx = file_col * height + file_row

        print(f"{name}:")
        print(f"  Game position: ({game_col}, {game_row})")
        print(f"  File position (simple): col={file_col}, row={file_row}")
        print(f"  Cell index: {cell_idx}")

        if cell_idx < len(cells_current):
            cell = cells_current[cell_idx]
            print(f"  Cell data: {' '.join(f'{b:02X}' for b in cell)}")

        print()

    print("="*60)
    print()

    # Look for unusual byte patterns that might indicate fountains
    print("Scanning for unusual byte patterns (potential fountains)...")
    print()

    # Count byte value frequencies
    byte_value_counts = [{} for _ in range(20)]

    for cell in cells_current:
        for byte_idx in range(20):
            val = cell[byte_idx]
            if val not in byte_value_counts[byte_idx]:
                byte_value_counts[byte_idx][val] = 0
            byte_value_counts[byte_idx][val] += 1

    # Find rare values that appear exactly 4 times (one per corner)
    print("Byte values that appear exactly 4 times:")
    print()

    for byte_idx in range(20):
        rare_values = [val for val, count in byte_value_counts[byte_idx].items()
                      if count == 4 and val != 0]
        if rare_values:
            print(f"Byte {byte_idx:2d}: {[f'0x{v:02X}' for v in rare_values]}")

            # Find which cells have these values
            for val in rare_values:
                cells_with_value = []
                for cell_idx in range(len(cells_current)):
                    if cells_current[cell_idx][byte_idx] == val:
                        file_col = cell_idx // height
                        file_row = cell_idx % height
                        cells_with_value.append((cell_idx, file_row, file_col))

                print(f"  Value 0x{val:02X} in cells: {cells_with_value}")

    print()
    print("="*60)
    print()

    # Alternative: scan EVEN bytes (we know odd bytes are walls)
    print("Checking EVEN bytes (0,2,4,6,8,10,12,14,16,18) for fountain data:")
    print()

    for byte_idx in range(0, 20, 2):
        # Find values that appear 4 times
        rare_values = [val for val, count in byte_value_counts[byte_idx].items()
                      if count == 4 and val != 0]

        if rare_values:
            print(f"Byte {byte_idx:2d} (EVEN):")
            for val in rare_values:
                cells_with_value = []
                for cell_idx in range(len(cells_current)):
                    if cells_current[cell_idx][byte_idx] == val:
                        file_col = cell_idx // height
                        file_row = cell_idx % height
                        cells_with_value.append(f"({file_row},{file_col})")

                print(f"  0x{val:02X}: {', '.join(cells_with_value)}")
            print()

    print("="*60)
    print()

    # Show full data for potential corner cells
    print("Full cell data for candidate positions:")
    print()

    # Try all possible file row values for each corner
    for name, game_col, game_row in corners:
        file_col = game_col

        print(f"{name} (game col={game_col}, row={game_row}):")
        print()

        # Try different file rows
        for test_file_row in range(height):
            cell_idx = file_col * height + test_file_row
            if cell_idx < len(cells_current):
                cell = cells_current[cell_idx]

                # Check if this cell has unusual data
                has_unusual = False

                # Check even bytes for non-zero, non-common values
                for byte_idx in range(0, 20, 2):
                    val = cell[byte_idx]
                    if val != 0:
                        # Check if this is a rare value
                        if byte_value_counts[byte_idx][val] <= 10:
                            has_unusual = True
                            break

                if has_unusual or test_file_row == game_row:
                    print(f"  File row {test_file_row:2d} (cell {cell_idx:3d}):")

                    # Show even bytes
                    even_bytes = [cell[i] for i in range(0, 20, 2)]
                    print(f"    Even bytes: {' '.join(f'{b:02X}' for b in even_bytes)}")

                    # Show odd bytes (walls)
                    odd_bytes = [cell[i] for i in range(1, 20, 2)]
                    print(f"    Odd bytes:  {' '.join(f'{b:02X}' for b in odd_bytes)}")

                    if has_unusual:
                        print(f"    ^ Has unusual values!")
                    print()

        print("-"*60)
        print()

if __name__ == "__main__":
    main()
