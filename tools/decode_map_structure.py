#!/usr/bin/env python3
"""
Decode map structure from newgame.dbs based on the wall differences.

Wizardry maps are typically 20x20 grids. Wall data might be stored as:
- 2 bytes per cell (one for H walls, one for V walls)
- Or 1 byte per cell with walls as bits
- Or separate layers for each wall direction
"""

import sys
from pathlib import Path

def analyze_map_data(filepath):
    """Analyze the map data structure."""
    with open(filepath, 'rb') as f:
        data = f.read()

    print("Analyzing Wizardry 6 map structure")
    print("="*70)
    print()

    # The changed offsets in newgameold
    changes = [
        (0x25B, 0x00, 0x80),
        (0x25D, 0x00, 0x80),
        (0x31D, 0x00, 0xA0),
    ]

    print("Hypothesis 1: 20x20 map with 2 bytes per cell")
    print("  20x20 = 400 cells, 2 bytes/cell = 800 bytes per map")
    print()

    # Top-right corner in a 20x20 grid (0-indexed)
    # Row 0, Column 19 (if row-major) = offset: 0*20 + 19 = cell 19
    # Cell 19 * 2 bytes = offset 38 (0x26)

    # But let's check what cells our offsets correspond to
    print("Hypothesis 2: Each cell has N bytes")
    print()

    for bytes_per_cell in [1, 2, 4, 8]:
        print(f"  If {bytes_per_cell} bytes per cell:")
        for offset, old, new in changes:
            cell = offset // bytes_per_cell
            byte_in_cell = offset % bytes_per_cell
            row = cell // 20
            col = cell % 20
            print(f"    0x{offset:03X}: Cell {cell:3d} ({row:2d},{col:2d}) byte {byte_in_cell}")
        print()

    print("="*70)
    print("Hypothesis 3: Walls stored as separate layers")
    print()

    # Maybe each wall direction is stored separately?
    # 20x20 = 400 bytes per layer
    # 4 directions = 4 layers?

    print("  If 20x20 grid (400 bytes per direction):")
    for offset, old, new in changes:
        layer = offset // 400
        cell_in_layer = offset % 400
        row = cell_in_layer // 20
        col = cell_in_layer % 20
        print(f"    0x{offset:03X}: Layer {layer}, Cell ({row:2d},{col:2d})")

    print()
    print("="*70)
    print("Looking at offset spacing:")
    print()

    print(f"  0x25B to 0x25D: {0x25D - 0x25B:3d} bytes (0x{0x25D - 0x25B:02X})")
    print(f"  0x25D to 0x31D: {0x31D - 0x25D:3d} bytes (0x{0x31D - 0x25D:02X})")
    print(f"  0x25B to 0x31D: {0x31D - 0x25B:3d} bytes (0x{0x31D - 0x25B:02X})")
    print()

    # 192 bytes = 0xC0
    # Could this be 96 * 2?  Or 64 * 3?
    print("  If stride = 194 bytes:")
    print(f"    194 = 97 * 2 (possibly 2 bytes wide?)")
    print()

    print("="*70)
    print("Bit analysis of changed bytes:")
    print()

    print("  0x80 = 10000000 (bit 7)")
    print("  0xA0 = 10100000 (bits 7, 5)")
    print()
    print("  If walls are stored as bits in each byte:")
    print("    Bit 7 (0x80) = North wall?")
    print("    Bit 6 (0x40) = South wall?")
    print("    Bit 5 (0x20) = East wall?")
    print("    Bit 4 (0x10) = West wall?")
    print()
    print("  Then for 'walls on all 4 sides':")
    print("    0x25B: bit 7 set = North wall")
    print("    0x25D: bit 7 set = North wall (why two?)")
    print("    0x31D: bits 7,5 set = North + East walls")
    print()
    print("  Missing: South and West walls...")
    print()

    print("="*70)
    print("Alternative: Each byte stores 2 walls (high/low nibble)?")
    print()
    print("  0x80 = 1000 0000 -> high nibble 8, low nibble 0")
    print("  0xA0 = 1010 0000 -> high nibble A, low nibble 0")
    print()

    # Look at nearby bytes that have non-zero values
    print("="*70)
    print("Examining non-zero bytes near changes:")
    print()

    for offset, old, new in changes:
        print(f"Near 0x{offset:03X}:")
        start = max(0, offset - 16)
        end = min(len(data), offset + 16)

        nonzero = []
        for i in range(start, end):
            if data[i] != 0:
                nonzero.append((i, data[i]))

        for i, val in nonzero:
            marker = " <--" if i == offset else ""
            print(f"  0x{i:03X}: {val:02X} = {val:08b}{marker}")
        print()

def main():
    file_old = Path("gamedata/newgameold.dbs")
    file_new = Path("gamedata/newgame.dbs")

    if not file_old.exists():
        print(f"Error: {file_old} not found")
        sys.exit(1)

    print("Analysis based on newgameold.dbs (has walls)")
    print()
    analyze_map_data(file_old)

if __name__ == "__main__":
    main()
