#!/usr/bin/env python3
"""
Render the first map as ASCII art based on wall data in bytes 3 and 5.
"""

import sys
from pathlib import Path

def read_map_data(filepath, start_offset=0):
    """Read map cell data (400 cells, 8 bytes each)."""
    with open(filepath, 'rb') as f:
        f.seek(start_offset)
        data = f.read(400 * 8)  # 20x20 grid, 8 bytes per cell

    cells = []
    for i in range(400):
        cell_data = data[i*8:(i+1)*8]
        if len(cell_data) == 8:
            cells.append(cell_data)
        else:
            cells.append(bytes([0] * 8))

    return cells

def get_walls(cell_data, interpretation=1):
    """
    Extract wall flags from cell data.

    interpretation 1: bit 7 in byte 3/5 = walls
    interpretation 2: check multiple bits
    interpretation 3: check lower bits too
    """
    byte_3 = cell_data[3]
    byte_5 = cell_data[5]

    walls = {'N': False, 'S': False, 'E': False, 'W': False}

    if interpretation == 1:
        # Hypothesis 1: Byte 3 bit 7 = North, Byte 5 bit 7 = East, bit 5 = West
        if byte_3 & 0x80:
            walls['N'] = True
        if byte_3 & 0x40:
            walls['S'] = True
        if byte_5 & 0x80:
            walls['E'] = True
        if byte_5 & 0x20:
            walls['W'] = True

    elif interpretation == 2:
        # Try checking if any high bits are set
        if byte_3 & 0xF0:  # High nibble
            walls['N'] = True
        if byte_5 & 0xF0:
            walls['E'] = True

    elif interpretation == 3:
        # Check all non-zero values
        if byte_3 != 0:
            walls['N'] = True
        if byte_5 != 0:
            walls['E'] = True

    return walls

def render_map_simple(cells, interpretation=1):
    """Render map using simple ASCII characters."""
    print(f"\nMap rendering (interpretation {interpretation}):")
    print("Using: # for walls, . for open space")
    print("="*60)
    print()

    # Create a grid for rendering (each cell is 3x3 characters)
    grid = []
    for row in range(20):
        grid.append([])
        for col in range(20):
            grid[row].append('.')

    # Mark cells with walls
    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            walls = get_walls(cell_data, interpretation)

            # If any walls, mark with #
            if any(walls.values()):
                grid[row][col] = '#'

    # Print grid
    print("   ", end="")
    for col in range(20):
        print(f"{col%10}", end="")
    print()

    for row in range(20):
        print(f"{row:2d} ", end="")
        for col in range(20):
            print(grid[row][col], end="")
        print()

def render_map_box_drawing(cells, interpretation=1):
    """Render map using box-drawing characters."""
    print(f"\nMap with box-drawing (interpretation {interpretation}):")
    print("="*60)
    print()

    # Create a grid that's 41x41 (20 cells + 21 walls/corners)
    # Each cell takes up 2x2 chars (1 for cell, 1 for wall)
    grid = [[' ' for _ in range(41)] for _ in range(41)]

    # Draw the outer border
    for i in range(41):
        grid[0][i] = '─'
        grid[40][i] = '─'
        grid[i][0] = '│'
        grid[i][40] = '│'

    grid[0][0] = '┌'
    grid[0][40] = '┐'
    grid[40][0] = '└'
    grid[40][40] = '┘'

    # Fill in cell walls
    for row in range(20):
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            walls = get_walls(cell_data, interpretation)

            # Position in grid (each cell is at grid[row*2+1][col*2+1])
            grid_row = row * 2 + 1
            grid_col = col * 2 + 1

            # Draw the cell center
            byte_0 = cell_data[0]
            if byte_0 != 0:
                grid[grid_row][grid_col] = '·'
            else:
                grid[grid_row][grid_col] = ' '

            # Draw walls
            if walls['N']:
                grid[grid_row - 1][grid_col] = '─'
            if walls['S']:
                grid[grid_row + 1][grid_col] = '─'
            if walls['E']:
                grid[grid_row][grid_col + 1] = '│'
            if walls['W']:
                grid[grid_row][grid_col - 1] = '│'

    # Draw corners where walls meet
    for r in range(0, 41, 2):
        for c in range(0, 41, 2):
            if r == 0 or r == 40 or c == 0 or c == 40:
                continue  # Skip outer border

            # Check what's around this corner
            up = grid[r-1][c] in ['─', '│', '┼', '├', '┤', '┬', '┴']
            down = grid[r+1][c] in ['─', '│', '┼', '├', '┤', '┬', '┴']
            left = grid[r][c-1] in ['─', '│', '┼', '├', '┤', '┬', '┴']
            right = grid[r][c+1] in ['─', '│', '┼', '├', '┤', '┬', '┴']

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

    # Print grid
    for row in grid:
        print(''.join(row))

def show_wall_stats(cells):
    """Show statistics about walls in the map."""
    print("\nWall statistics:")
    print("="*60)

    counts = {'byte3_high': 0, 'byte5_high': 0, 'byte3_nonzero': 0, 'byte5_nonzero': 0}

    for cell_data in cells:
        if cell_data[3] & 0x80:
            counts['byte3_high'] += 1
        if cell_data[5] & 0x80:
            counts['byte5_high'] += 1
        if cell_data[3] != 0:
            counts['byte3_nonzero'] += 1
        if cell_data[5] != 0:
            counts['byte5_nonzero'] += 1

    print(f"Cells with byte 3 bit 7 set: {counts['byte3_high']} ({counts['byte3_high']/4:.1f}%)")
    print(f"Cells with byte 5 bit 7 set: {counts['byte5_high']} ({counts['byte5_high']/4:.1f}%)")
    print(f"Cells with byte 3 non-zero:  {counts['byte3_nonzero']} ({counts['byte3_nonzero']/4:.1f}%)")
    print(f"Cells with byte 5 non-zero:  {counts['byte5_nonzero']} ({counts['byte5_nonzero']/4:.1f}%)")

def show_changed_cells(cells):
    """Highlight the cells that changed in newgameold."""
    print("\nChanged cells marked with 'X':")
    print("="*60)
    print()

    print("   ", end="")
    for col in range(20):
        print(f"{col%10}", end="")
    print()

    changed = [(3, 15), (4, 19)]

    for row in range(20):
        print(f"{row:2d} ", end="")
        for col in range(20):
            if (row, col) in changed:
                print('X', end="")
            else:
                cell_idx = row * 20 + col
                walls = get_walls(cells[cell_idx], 1)
                if any(walls.values()):
                    print('·', end="")
                else:
                    print(' ', end="")
        print()

def main():
    # Set UTF-8 encoding for Windows console
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print(f"Reading map data from {filepath}")
    cells = read_map_data(filepath)

    if len(cells) != 400:
        print(f"Error: Expected 400 cells, got {len(cells)}")
        sys.exit(1)

    show_wall_stats(cells)
    show_changed_cells(cells)

    # Try different rendering approaches
    render_map_simple(cells, interpretation=1)
    render_map_box_drawing(cells, interpretation=1)

    print("\n" + "="*60)
    print("Legend:")
    print("  · = cell with wall data")
    print("  X = cells that were changed (had walls added)")
    print("  ─│┌┐└┘├┤┬┴┼ = box-drawing characters for walls")

if __name__ == "__main__":
    main()
