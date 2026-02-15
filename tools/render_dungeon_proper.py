#!/usr/bin/env python3
"""
Proper dungeon map renderer - walls are BETWEEN cells, not on cells.
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

def render_dungeon_walls(cells, interpretation='v1'):
    """
    Render dungeon with walls between cells.
    Each cell is 3 chars wide and 2 chars tall.
    Walls are drawn on the edges between cells.
    """
    print(f"\nDungeon Map (interpretation: {interpretation})")
    print("Walls are drawn BETWEEN cells")
    print("="*80)
    print()

    # Create rendering grid
    # Each cell is 3 chars wide (left wall + space + content)
    # Each cell is 2 chars tall (top wall + cell content)
    # Plus 1 for final right edge and bottom edge
    width = 20 * 3 + 1   # 61 chars
    height = 20 * 2 + 1  # 41 chars

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Process each cell
    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Grid position for this cell
            # Each cell starts at (row*2, col*3)
            grid_row = row * 2
            grid_col = col * 3

            # Determine walls based on interpretation
            has_north = False
            has_south = False
            has_east = False
            has_west = False

            if interpretation == 'v1':
                # Hypothesis: byte 3 bit 7 = North, byte 3 bit 6 = South
                #             byte 5 bit 7 = East, byte 5 bit 5 = West
                has_north = bool(byte_3 & 0x80)
                has_south = bool(byte_3 & 0x40)
                has_east = bool(byte_5 & 0x80)
                has_west = bool(byte_5 & 0x20)

            elif interpretation == 'v2':
                # Alternative: byte 3 = horizontal walls, byte 5 = vertical walls
                has_north = bool(byte_3 & 0x80)
                has_south = bool(byte_3 & 0x40)
                has_east = bool(byte_5 & 0x80)
                has_west = bool(byte_5 & 0x40)

            elif interpretation == 'v3':
                # Maybe walls are stored as North/East only (South/West are implied by neighbor)
                has_north = bool(byte_3 & 0x80)
                has_east = bool(byte_5 & 0x80)
                # Don't set South/West explicitly

            # Draw cell content
            if byte_0 == 0x02:
                grid[grid_row + 1][grid_col + 1] = '@'
            elif byte_0 != 0 or byte_3 != 0 or byte_5 != 0:
                grid[grid_row + 1][grid_col + 1] = '·'
            else:
                grid[grid_row + 1][grid_col + 1] = ' '

            # Draw walls
            # North wall (top edge)
            if has_north:
                grid[grid_row][grid_col + 1] = '─'

            # South wall (bottom edge)
            if has_south:
                grid[grid_row + 2][grid_col + 1] = '─'

            # West wall (left edge)
            if has_west:
                grid[grid_row + 1][grid_col] = '│'

            # East wall (right edge)
            if has_east:
                grid[grid_row + 1][grid_col + 3] = '│'

    # Draw corners where walls meet
    for r in range(0, height, 2):
        for c in range(0, width, 3):
            up = (r > 0) and grid[r-1][c] in ['│', '┼', '├', '┤', '┬', '┴']
            down = (r < height-1) and grid[r+1][c] in ['│', '┼', '├', '┤', '┬', '┴']
            left = (c > 0) and grid[r][c-1] in ['─', '┼', '├', '┤', '┬', '┴']
            right = (c < width-1) and grid[r][c+1] in ['─', '┼', '├', '┤', '┬', '┴']

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
            elif up or down or left or right:
                grid[r][c] = '+'

    # Print with row numbers
    print("   ", end="")
    for col in range(0, 20):
        print(f"{col%10:2s} ", end="")
    print()

    for r, row_data in enumerate(grid):
        if r % 2 == 0:
            print("   ", end="")
        else:
            print(f"{(r//2):2d} ", end="")
        print(''.join(row_data))

def render_simple_dungeon(cells, interpretation='v1'):
    """Simple ASCII dungeon using basic characters."""
    print(f"\nSimple Dungeon Map (interpretation: {interpretation})")
    print("="*80)
    print()

    # Create a grid where each cell is represented by 2x2 chars
    # Format:  +- or |
    #          |X    (where X is cell content)

    lines = []

    # Top border
    line = "   +"
    for col in range(20):
        line += "--+"
    lines.append(line)

    for row in range(20):
        # Line with walls above cells
        line = "   |"
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            byte_3 = cell_data[3]

            # North wall
            if interpretation == 'v1' or interpretation == 'v3':
                has_north = bool(byte_3 & 0x80)
            else:
                has_north = bool(byte_3 & 0x80)

            if has_north:
                line += "--"
            else:
                line += "  "
            line += "|"
        lines.append(line)

        # Line with cell content and side walls
        line = f"{row:2d} |"
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # West wall
            if interpretation == 'v1':
                has_west = bool(byte_5 & 0x20)
            elif interpretation == 'v3':
                has_west = False  # Check previous cell's east
                if col > 0:
                    prev_cell = cells[row * 20 + col - 1]
                    has_west = bool(prev_cell[5] & 0x80)
            else:
                has_west = bool(byte_5 & 0x40)

            # Cell content
            if byte_0 == 0x02:
                content = '@'
            elif byte_0 != 0 or byte_3 != 0 or byte_5 != 0:
                content = '.'
            else:
                content = ' '

            if col == 0 or has_west:
                line += content + " |"
            else:
                line += content + "  "

        lines.append(line)

    # Bottom border
    line = "   +"
    for col in range(20):
        line += "--+"
    lines.append(line)

    for line in lines:
        print(line)

def show_test_region(cells, row_start, row_end, col_start, col_end):
    """Show byte values for a test region."""
    print(f"\nTest region: rows {row_start}-{row_end}, cols {col_start}-{col_end}")
    print("Format: [byte3:byte5]")
    print("="*60)

    print("    ", end="")
    for col in range(col_start, col_end):
        print(f"   {col:2d}  ", end="")
    print()

    for row in range(row_start, row_end):
        print(f" {row:2d} ", end="")
        for col in range(col_start, col_end):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            if byte_3 == 0 and byte_5 == 0:
                print("  ---  ", end="")
            else:
                print(f" {byte_3:02X}:{byte_5:02X} ", end="")
        print()

def main():
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    cells = read_map_data(filepath)

    # Show the changed region
    print("Region where walls were added:")
    show_test_region(cells, 2, 6, 13, 20)

    # Try different interpretations
    print("\n" + "="*80)
    print("Trying different wall bit interpretations...")
    print("="*80)

    for interpretation in ['v1', 'v2', 'v3']:
        render_simple_dungeon(cells, interpretation)
        input(f"\nPress Enter to see next interpretation...")

    # Show detailed version with best interpretation
    render_dungeon_walls(cells, 'v1')

if __name__ == "__main__":
    main()
