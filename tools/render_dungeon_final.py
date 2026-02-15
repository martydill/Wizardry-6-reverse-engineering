#!/usr/bin/env python3
"""
Final dungeon map renderer - walls are BETWEEN cells.
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

def get_walls(cell_data, interpretation='v1'):
    """Get wall flags for a cell."""
    byte_3 = cell_data[3]
    byte_5 = cell_data[5]

    walls = {'N': False, 'S': False, 'E': False, 'W': False}

    if interpretation == 'v1':
        # Byte 3 bit 7 = North, bit 6 = South
        # Byte 5 bit 7 = East, bit 5 = West
        walls['N'] = bool(byte_3 & 0x80)
        walls['S'] = bool(byte_3 & 0x40)
        walls['E'] = bool(byte_5 & 0x80)
        walls['W'] = bool(byte_5 & 0x20)
    elif interpretation == 'v2':
        # Alternative bit assignment
        walls['N'] = bool(byte_3 & 0x80)
        walls['S'] = bool(byte_3 & 0x40)
        walls['E'] = bool(byte_5 & 0x80)
        walls['W'] = bool(byte_5 & 0x40)
    elif interpretation == 'v3':
        # Only North/East stored (South/West are neighbors' North/East)
        walls['N'] = bool(byte_3 & 0x80)
        walls['E'] = bool(byte_5 & 0x80)

    return walls

def render_dungeon_ascii(cells, interpretation='v1', show_coords=True):
    """Render dungeon with walls between cells using ASCII."""
    print(f"\nWizardry 6 - First Map (interpretation {interpretation})")
    print("Walls are drawn between cells")
    print("="*80)
    print()

    lines = []

    # Column headers
    if show_coords:
        header = "    "
        for col in range(0, 20, 5):
            header += f"{col:5d}    "
        lines.append(header)

    # Top border
    border = "   ┌"
    for col in range(20):
        border += "──┬" if col < 19 else "──┐"
    lines.append(border)

    for row in range(20):
        # Line showing top walls and cell content
        line_top = f" {row:2d} │" if show_coords else "   │"
        line_mid = "    │" if show_coords else "   │"

        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            walls = get_walls(cell_data, interpretation)

            byte_0 = cell_data[0]

            # Cell content
            if byte_0 == 0x02:
                content = '@'
            elif byte_0 != 0 or cell_data[3] != 0 or cell_data[5] != 0:
                content = '·'
            else:
                content = ' '

            # West wall
            if walls['W']:
                if col == 0:
                    line_mid = line_mid[:-1] + '│'  # Already have left border
                # else don't add, it's part of the grid

            # Cell with vertical separators
            if walls['E'] or col == 19:
                line_mid += f" {content} │"
            else:
                line_mid += f" {content}  "

            # North wall (shown on this row)
            if walls['N']:
                line_top += "──"
            else:
                line_top += "  "

            # Column separator
            if col < 19:
                line_top += "┬"
            else:
                line_top += "│"

        if row == 0:
            # Skip top wall line for first row (already have border)
            lines.append(line_mid)
        else:
            lines.append(line_top)
            lines.append(line_mid)

    # Bottom border
    border = "   └"
    for col in range(20):
        border += "──┴" if col < 19 else "──┘"
    lines.append(border)

    for line in lines:
        print(line)

def render_simple_dungeon(cells, interpretation='v1'):
    """Simple ASCII using +, -, | characters."""
    print(f"\nSimple ASCII Map (interpretation {interpretation})")
    print("="*70)
    print()

    # Column headers
    print("     ", end="")
    for col in range(20):
        print(f"{col%10}", end=" ")
    print()

    # Top border
    print("   +", end="")
    for col in range(20):
        print("-+", end="")
    print()

    for row in range(20):
        # Top edge of cells (north walls)
        print("   |", end="")
        for col in range(20):
            cell_idx = row * 20 + col
            walls = get_walls(cells[cell_idx], interpretation)

            if walls['N']:
                print("-", end="")
            else:
                print(" ", end="")

            print("|", end="")
        print()

        # Cell content with side walls
        print(f"{row:2d} |", end="")
        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            walls = get_walls(cell_data, interpretation)

            # Content
            if cell_data[0] == 0x02:
                content = '@'
            elif cell_data[0] != 0 or cell_data[3] != 0 or cell_data[5] != 0:
                content = '.'
            else:
                content = ' '

            print(content, end="")

            # East wall
            if walls['E'] or col == 19:
                print("|", end="")
            else:
                print(" ", end="")

        print()

    # Bottom border
    print("   +", end="")
    for col in range(20):
        print("-+", end="")
    print()

def show_changed_region(cells):
    """Highlight the cells where walls were added."""
    print("\nChanged cells (walls added at row 3, col 15 and row 4, col 19):")
    print("Format: [byte3:byte5]  (binary: byte3=NSXXXXXX?, byte5=EWX...?)")
    print("="*70)

    for row in range(2, 6):
        print(f"\nRow {row}:")
        print("  Col:  ", end="")
        for col in range(13, 20):
            print(f"  {col:2d}   ", end="")
        print()

        print("  B3:B5:", end="")
        for col in range(13, 20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]
            b3, b5 = cell_data[3], cell_data[5]

            if b3 == 0 and b5 == 0:
                print("  ---  ", end="")
            else:
                marker = " !" if (row, col) in [(3, 15), (4, 19)] else "  "
                print(f"{b3:02X}:{b5:02X}{marker}", end="")
        print()

        print("  Walls:", end="")
        for col in range(13, 20):
            cell_idx = row * 20 + col
            walls = get_walls(cells[cell_idx], 'v1')
            wall_str = ""
            if walls['N']: wall_str += 'N'
            if walls['S']: wall_str += 'S'
            if walls['E']: wall_str += 'E'
            if walls['W']: wall_str += 'W'

            if wall_str:
                print(f" {wall_str:4s} ", end="")
            else:
                print("  ---  ", end="")
        print()

def main():
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    print("Wizardry 6 Map Renderer")
    print("Reading from: newgameold.dbs (with walls added)")
    print()

    cells = read_map_data(filepath)

    # Show what changed
    show_changed_region(cells)

    # Render with different interpretations
    render_simple_dungeon(cells, 'v1')

    print("\n" + "="*70)
    print("Legend:")
    print("  @ = special tile (encounters, stairs, etc.)")
    print("  . = floor with data")
    print("  - = north wall (above cell)")
    print("  | = east/west wall (on sides of cell)")
    print()
    print("Changed cells at (3,15) and (4,19) should show added walls!")

if __name__ == "__main__":
    main()
