#!/usr/bin/env python3
"""
Side-by-side comparison of maps with and without added walls.
"""

import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def read_map_data(filepath, start_offset=0):
    """Read map cell data."""
    with open(filepath, 'rb') as f:
        f.seek(start_offset)
        data = f.read(400 * 8)

    cells = []
    for i in range(400):
        cell_data = data[i*8:(i+1)*8]
        cells.append(cell_data if len(cell_data) == 8 else bytes([0] * 8))

    return cells

def render_map_simple(cells):
    """Render map as simple 2D grid."""
    lines = []

    # Header
    header = "    "
    for col in range(20):
        header += f"{col%10} "
    lines.append(header)
    lines.append("    " + "─" * 40)

    for row in range(20):
        line = f" {row:2d}│"
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Determine cell character
            if byte_3 & 0x80 or byte_5 & 0x80:
                # High bit set = wall
                char = '█'
            elif byte_3 != 0 or byte_5 != 0:
                # Some data = floor with features
                char = '·'
            else:
                # Empty
                char = ' '

            line += char + ' '

        lines.append(line)

    return lines

def highlight_differences(cells1, cells2):
    """Show cells that differ between two maps."""
    print("\nDifferences between maps:")
    print("X = cells that changed")
    print("="*60)

    print("    ", end="")
    for col in range(20):
        print(f"{col%10} ", end="")
    print()
    print("    " + "─" * 40)

    changes = []

    for row in range(20):
        print(f" {row:2d}│", end="")
        for col in range(20):
            cell_idx = row * 20 + col
            c1 = cells1[cell_idx]
            c2 = cells2[cell_idx]

            if c1[3] != c2[3] or c1[5] != c2[5]:
                print('X ', end="")
                changes.append((row, col, c1[3], c1[5], c2[3], c2[5]))
            else:
                print('. ', end="")
        print()

    print()
    print("Changed cells:")
    for row, col, old_b3, old_b5, new_b3, new_b5 in changes:
        print(f"  ({row:2d},{col:2d}): byte3 {old_b3:02X}→{new_b3:02X}, byte5 {old_b5:02X}→{new_b5:02X}")

def render_dungeon_comparison(cells1, cells2, title1, title2):
    """Render two maps side by side."""
    print("\nSide-by-side comparison:")
    print("="*100)

    # Header
    print(f"\n{title1:40s}  |  {title2}")
    print("─" * 100)

    for row in range(20):
        # Line for map 1
        line1 = f" {row:2d} "
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells1[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]
            byte_0 = cell_data[0]

            # Determine character
            if byte_3 & 0x80 or byte_5 & 0x80:
                char = '█'  # Solid block for walls
            elif byte_0 == 0x02:
                char = '@'  # Special marker
            elif byte_3 != 0 or byte_5 != 0:
                char = '·'  # Floor with data
            else:
                char = ' '  # Empty

            line1 += char

        # Line for map 2
        line2 = f" {row:2d} "
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells2[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]
            byte_0 = cell_data[0]

            if byte_3 & 0x80 or byte_5 & 0x80:
                char = '█'
            elif byte_0 == 0x02:
                char = '@'
            elif byte_3 != 0 or byte_5 != 0:
                char = '·'
            else:
                char = ' '

            line2 += char

        # Print both lines side by side
        print(f"{line1}  |  {line2}")

    print("─" * 100)
    print("\nLegend: █=wall bits set, ·=data present, @=special, space=empty")

def show_region(cells, title, row_start, row_end, col_start, col_end):
    """Show a specific region of the map in detail."""
    print(f"\n{title}")
    print("="*60)

    # Header
    print("    ", end="")
    for col in range(col_start, col_end):
        print(f" {col:2d} ", end="")
    print()

    for row in range(row_start, row_end):
        print(f" {row:2d} ", end="")
        for col in range(col_start, col_end):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            if byte_3 == 0 and byte_5 == 0:
                print("  ·  ", end="")
            else:
                print(f"{byte_3:02X}:{byte_5:02X}", end=" ")
        print()

def main():
    file_old = Path("gamedata/newgameold.dbs")
    file_new = Path("gamedata/newgame.dbs")

    if not file_old.exists() or not file_new.exists():
        print("Error: Files not found")
        sys.exit(1)

    print("Comparing map files:")
    print(f"  newgame.dbs    = without walls")
    print(f"  newgameold.dbs = WITH walls in top-right corner")
    print()

    cells_new = read_map_data(file_new)
    cells_old = read_map_data(file_old)

    highlight_differences(cells_new, cells_old)

    render_dungeon_comparison(cells_new, cells_old,
                            "newgame.dbs (no walls)",
                            "newgameold.dbs (with walls)")

    print("\n" + "="*100)
    print("Top-right region detail (rows 2-6, cols 13-20):")
    show_region(cells_old, "newgameold.dbs (with walls added)", 2, 7, 13, 20)
    show_region(cells_new, "newgame.dbs (original)", 2, 7, 13, 20)

if __name__ == "__main__":
    main()
