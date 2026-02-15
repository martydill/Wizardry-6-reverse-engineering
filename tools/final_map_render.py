#!/usr/bin/env python3
"""
Final polished ASCII map renderer for Wizardry 6.
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

def render_ascii_map(cells, title="Wizardry 6 - First Map"):
    """Render a clean ASCII map."""
    print(f"\n{title}")
    print("="*80)
    print()

    # Column headers
    print("     ", end="")
    for col in range(0, 20, 5):
        print(f"{col:5d}", end="    ")
    print()

    print("    ┌", end="")
    for col in range(20):
        print("──", end="")
    print("┐")

    for row in range(20):
        print(f" {row:2d} │", end="")

        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Determine what to display
            if byte_3 & 0x80 and byte_5 & 0x80:
                # Both high bits = strong wall
                char = '██'
            elif byte_3 & 0x80 or byte_5 & 0x80:
                # One high bit = wall
                char = '▓▓'
            elif byte_3 & 0xF0 or byte_5 & 0xF0:
                # High nibble bits = partial wall
                char = '▒▒'
            elif byte_0 == 0x02:
                # Special marker
                char = '◆◆'
            elif byte_3 != 0 or byte_5 != 0:
                # Has data = floor
                char = '··'
            else:
                # Empty
                char = '  '

            print(char, end="")

        print("│")

    print("    └", end="")
    for col in range(20):
        print("──", end="")
    print("┘")

    print()
    print("Legend:")
    print("  ██ = Strong wall (both byte 3 & 5 bit 7 set)")
    print("  ▓▓ = Wall (one high bit set)")
    print("  ▒▒ = Partial wall (high nibble bits)")
    print("  ·· = Floor with data")
    print("  ◆◆ = Special tile")
    print("     = Empty space")

def render_simple_map(cells, title="Simple Map"):
    """Render using just ASCII characters."""
    print(f"\n{title}")
    print("="*60)
    print()

    # Column headers
    print("   ", end="")
    for col in range(20):
        print(f"{col%10}", end="")
    print()
    print("   +" + "-"*20 + "+")

    for row in range(20):
        print(f"{row:2d}|", end="")

        for col in range(20):
            cell_idx = row * 20 + col
            cell_data = cells[cell_idx]

            byte_0 = cell_data[0]
            byte_3 = cell_data[3]
            byte_5 = cell_data[5]

            # Determine character
            if byte_3 & 0x80 and byte_5 & 0x80:
                char = '#'  # Strong wall
            elif byte_3 & 0x80 or byte_5 & 0x80:
                char = '#'  # Wall
            elif byte_0 == 0x02:
                char = '@'  # Special
            elif byte_3 != 0 or byte_5 != 0:
                char = '.'  # Floor
            else:
                char = ' '  # Empty

            print(char, end="")

        print("|")

    print("   +" + "-"*20 + "+")
    print()
    print("Legend: # = wall, . = floor, @ = special")

def show_statistics(cells):
    """Show map statistics."""
    print("\nMap Statistics:")
    print("="*60)

    stats = {
        'empty': 0,
        'floor': 0,
        'special': 0,
        'wall_both': 0,
        'wall_b3': 0,
        'wall_b5': 0,
    }

    for cell_data in cells:
        byte_0 = cell_data[0]
        byte_3 = cell_data[3]
        byte_5 = cell_data[5]

        if byte_3 == 0 and byte_5 == 0:
            stats['empty'] += 1
        elif byte_3 & 0x80 and byte_5 & 0x80:
            stats['wall_both'] += 1
        elif byte_3 & 0x80:
            stats['wall_b3'] += 1
        elif byte_5 & 0x80:
            stats['wall_b5'] += 1
        elif byte_0 == 0x02:
            stats['special'] += 1
        else:
            stats['floor'] += 1

    total = 400
    print(f"  Empty cells:              {stats['empty']:3d} ({stats['empty']/4:.1f}%)")
    print(f"  Floor cells:              {stats['floor']:3d} ({stats['floor']/4:.1f}%)")
    print(f"  Special cells (@):        {stats['special']:3d} ({stats['special']/4:.1f}%)")
    print(f"  Walls (both bits):        {stats['wall_both']:3d} ({stats['wall_both']/4:.1f}%)")
    print(f"  Walls (byte 3 bit 7):     {stats['wall_b3']:3d} ({stats['wall_b3']/4:.1f}%)")
    print(f"  Walls (byte 5 bit 7):     {stats['wall_b5']:3d} ({stats['wall_b5']/4:.1f}%)")

def main():
    filepath = Path("gamedata/newgameold.dbs")

    if not filepath.exists():
        print(f"Error: {filepath} not found")
        sys.exit(1)

    cells = read_map_data(filepath)

    show_statistics(cells)
    render_simple_map(cells, "Wizardry 6 - First Map (Simple ASCII)")
    render_ascii_map(cells, "Wizardry 6 - First Map (Enhanced)")

    print("\n" + "="*80)
    print("Note: Cells (3,15) and (4,19) have the added wall flags")
    print("      Look for the walls in the upper-right portion of the map!")

if __name__ == "__main__":
    main()
