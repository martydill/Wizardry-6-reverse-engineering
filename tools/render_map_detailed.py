#!/usr/bin/env python3
"""
More detailed map rendering with multiple interpretation attempts.
"""

import sys
import io
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def read_map_data(filepath, start_offset=0):
    """Read map cell data (400 cells, 8 bytes each)."""
    with open(filepath, 'rb') as f:
        f.seek(start_offset)
        data = f.read(400 * 8)

    cells = []
    for i in range(400):
        cell_data = data[i*8:(i+1)*8]
        if len(cell_data) == 8:
            cells.append(cell_data)
        else:
            cells.append(bytes([0] * 8))

    return cells

def render_cell_based_walls(cells):
    """
    Render walls where each cell can have walls on all 4 sides.
    This creates a grid where walls can be drawn around each cell.
    """
    print("\nDetailed wall rendering (cell-based):")
    print("Each cell shows if it has walls: N/S/E/W")
    print("="*80)
    print()

    # Create a 41x81 grid (20 cells, each cell is 4 chars wide, 2 chars tall)
    grid = [[' ' for _ in range(81)] for _ in range(41)]

    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Position in grid
            grid_row = row * 2
            grid_col = col * 4

            # Check various wall indicators
            has_n_wall = byte_3 & 0x80  # Bit 7
            has_s_wall = byte_3 & 0x40  # Bit 6
            has_e_wall = byte_5 & 0x80  # Bit 7
            has_w_wall = byte_5 & 0x20  # Bit 5

            # Alternative: check if ANY bits are set
            has_data_3 = byte_3 != 0
            has_data_5 = byte_5 != 0

            # Draw cell border
            # Top wall
            if has_n_wall:
                grid[grid_row][grid_col] = '+'
                grid[grid_row][grid_col+1] = '─'
                grid[grid_row][grid_col+2] = '─'
                grid[grid_row][grid_col+3] = '+'

            # Bottom wall
            if has_s_wall:
                grid[grid_row+1][grid_col] = '+'
                grid[grid_row+1][grid_col+1] = '─'
                grid[grid_row+1][grid_col+2] = '─'
                grid[grid_row+1][grid_col+3] = '+'

            # Left wall
            if has_w_wall:
                grid[grid_row][grid_col] = '+'
                grid[grid_row+1][grid_col] = '+'

            # Right wall
            if has_e_wall:
                grid[grid_row][grid_col+3] = '+'
                grid[grid_row+1][grid_col+3] = '+'

            # Draw wall lines
            if has_w_wall:
                if grid[grid_row][grid_col] == '+' and grid[grid_row+1][grid_col] == '+':
                    # Only set middle if both corners exist
                    pass  # Grid is 2 rows tall, no middle
            if has_e_wall:
                if grid[grid_row][grid_col+3] == '+' and grid[grid_row+1][grid_col+3] == '+':
                    pass

            # Mark cell center with byte values if non-zero
            if has_data_3 or has_data_5:
                # Show abbreviated byte values
                if byte_3 > 0 and byte_5 > 0:
                    grid[grid_row+1][grid_col+1] = chr(ord('a') + (byte_3 % 26))
                    grid[grid_row+1][grid_col+2] = chr(ord('A') + (byte_5 % 26))
                elif byte_3 > 0:
                    grid[grid_row+1][grid_col+1] = chr(ord('a') + (byte_3 % 26))
                elif byte_5 > 0:
                    grid[grid_row+1][grid_col+2] = chr(ord('A') + (byte_5 % 26))

    # Print grid
    for row in grid:
        print(''.join(row))

def render_dungeon_style(cells):
    """
    Render in classic dungeon crawler style where walls are between cells.
    Each cell is represented by a space, walls are # characters.
    """
    print("\nClassic dungeon style:")
    print("# = wall, . = floor, @ = special")
    print("="*80)
    print()

    # Create a 41x41 grid (20 cells + walls between them)
    grid = [[' ' for _ in range(41)] for _ in range(41)]

    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            # Grid position (cells are at odd coordinates)
            grid_row = row * 2 + 1
            grid_col = col * 2 + 1

            # Put floor marker
            byte_0 = cell_data[0]
            if byte_0 == 0:
                grid[grid_row][grid_col] = '.'
            elif byte_0 == 0x02:
                grid[grid_row][grid_col] = '@'  # Special tile
            else:
                grid[grid_row][grid_col] = '·'

            # Check for walls
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Try: Byte 3 high bit = north wall
            if byte_3 & 0x80:
                grid[grid_row - 1][grid_col] = '#'

            # Try: Byte 5 bit 7 = east wall
            if byte_5 & 0x80:
                grid[grid_row][grid_col + 1] = '#'

            # Try: Byte 5 bit 5 = west wall
            if byte_5 & 0x20:
                grid[grid_row][grid_col - 1] = '#'

            # Try: Byte 3 bit 6 = south wall
            if byte_3 & 0x40:
                grid[grid_row + 1][grid_col] = '#'

    # Fill corners
    for r in range(0, 41, 2):
        for c in range(0, 41, 2):
            # Check adjacent cells
            up = (r > 0) and grid[r-1][c] == '#'
            down = (r < 40) and grid[r+1][c] == '#'
            left = (c > 0) and grid[r][c-1] == '#'
            right = (c < 40) and grid[r][c+1] == '#'

            if up or down or left or right:
                grid[r][c] = '#'

    # Print with coordinates
    print("  ", end="")
    for c in range(0, 41, 2):
        print(f"{(c//2)%10}", end=" ")
    print()

    for r, row in enumerate(grid):
        if r % 2 == 1:
            print(f"{(r//2):2d}", end="")
        else:
            print("  ", end="")
        print(''.join(row))

def show_byte_values_grid(cells):
    """Show the actual byte 3 and 5 values in a grid."""
    print("\nByte 3 and 5 values (hex):")
    print("Format: [byte3:byte5]")
    print("="*80)
    print()

    print("   ", end="")
    for col in range(20):
        print(f"  {col%10}  ", end="")
    print()

    for row in range(20):
        print(f"{row:2d} ", end="")
        for col in range(20):
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
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print(f"Reading map data from {filepath}\n")
    cells = read_map_data(filepath)

    show_byte_values_grid(cells)
    render_dungeon_style(cells)
    # render_cell_based_walls(cells)

    print("\n" + "="*80)
    print("Note: X marks at (3,15) and (4,19) should show added walls")

if __name__ == "__main__":
    main()
