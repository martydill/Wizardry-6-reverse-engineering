#!/usr/bin/env python3
"""
Clean dungeon map renderer with walls between cells.
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

def render_dungeon(cells, title="Wizardry 6 - Castle Level 1"):
    """Render dungeon map with walls between cells."""
    print(f"\n{title}")
    print("="*80)
    print()

    # Build the grid (each cell is 2 chars wide + walls)
    # Total width: 20 cells * 2 chars + 21 walls = 61 chars
    # Total height: 20 cells * 1 row + 21 wall rows = 41 rows

    height = 41
    width = 61

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Draw outer border
    for c in range(width):
        grid[0][c] = '─'
        grid[height-1][c] = '─'
    for r in range(height):
        grid[r][0] = '│'
        grid[r][width-1] = '│'
    grid[0][0] = '┌'
    grid[0][width-1] = '┐'
    grid[height-1][0] = '└'
    grid[height-1][width-1] = '┘'

    # Process each cell
    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Cell position in grid
            # Cells are at odd row/column positions
            grid_row = row * 2 + 1
            grid_col = col * 3 + 1

            # Cell content (2 chars wide)
            if byte_0 == 0x02:
                content = '@@'
            elif byte_0 != 0 or byte_3 != 0 or byte_5 != 0:
                content = ' ·'
            else:
                content = '  '

            grid[grid_row][grid_col] = content[0]
            grid[grid_row][grid_col+1] = content[1]

            # Walls
            has_north = bool(byte_3 & 0x80)
            has_south = bool(byte_3 & 0x40)
            has_east = bool(byte_5 & 0x80)
            has_west = bool(byte_5 & 0x20)

            # North wall (row above)
            if has_north:
                grid[grid_row - 1][grid_col] = '─'
                grid[grid_row - 1][grid_col + 1] = '─'

            # South wall (row below)
            if has_south:
                grid[grid_row + 1][grid_col] = '─'
                grid[grid_row + 1][grid_col + 1] = '─'

            # West wall (column to left)
            if has_west:
                grid[grid_row][grid_col - 1] = '│'

            # East wall (column to right)
            if has_east:
                grid[grid_row][grid_col + 2] = '│'

    # Draw corners and intersections
    for r in range(0, height, 2):
        for c in range(0, width, 3):
            if r == 0 or r == height - 1 or c == 0 or c == width - 1:
                continue  # Skip border

            # Check what's connected
            up = (r > 0) and grid[r-1][c] in ['│', '─', '┼', '├', '┤', '┬', '┴']
            down = (r < height-1) and grid[r+1][c] in ['│', '─', '┼', '├', '┤', '┬', '┴']
            left = (c > 0) and grid[r][c-1] in ['│', '─', '┼', '├', '┤', '┬', '┴']
            right = (c < width-1) and grid[r][c+1] in ['│', '─', '┼', '├', '┤', '┬', '┴']

            if up and down and left and right:
                grid[r][c] = '┼'
            elif up and down and left:
                grid[r][c] = '┤'
            elif up and down and right:
                grid[r][c] = '├'
            elif up and left and right:
                grid[r][c] = '┴'
            elif down and left and right:
                grid[r][c] = '┬'
            elif up and down:
                grid[r][c] = '│'
            elif left and right:
                grid[r][c] = '─'
            elif up and left:
                grid[r][c] = '┘'
            elif up and right:
                grid[r][c] = '└'
            elif down and left:
                grid[r][c] = '┐'
            elif down and right:
                grid[r][c] = '┌'

    # Print with row numbers
    print("     0    2    4    6    8   10   12   14   16   18  ")
    for r, row_chars in enumerate(grid):
        if r % 2 == 1:
            row_num = r // 2
            print(f" {row_num:2d}  ", end="")
        else:
            print("     ", end="")
        print(''.join(row_chars))

    print()
    print("Legend:")
    print("  @@ = special tile (stairs, encounters)")
    print("   · = floor tile")
    print("  ─│ = walls between cells")
    print()

def main():
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    cells = read_map_data(filepath)

    render_dungeon(cells)

    print("="*80)
    print("\nNote: Walls were added at cells (3,15) and (4,19)")
    print("      Look for the walls in the upper-right area of the map!")
    print()
    print("Wall encoding discovered:")
    print("  Byte 3, bit 7 (0x80) = North wall")
    print("  Byte 3, bit 6 (0x40) = South wall")
    print("  Byte 5, bit 7 (0x80) = East wall")
    print("  Byte 5, bit 5 (0x20) = West wall")

if __name__ == "__main__":
    main()
