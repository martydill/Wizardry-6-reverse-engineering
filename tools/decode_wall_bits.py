#!/usr/bin/env python3
"""
Decode the wall bit patterns by analyzing the entire map.
"""

import sys
from pathlib import Path
from collections import defaultdict

def analyze_wall_bits(filepath):
    """Analyze bit patterns in the wall bytes."""
    with open(filepath, 'rb') as f:
        data = f.read()

    print("Analyzing wall encoding in bytes 3 and 5")
    print("Hypothesis: Each bit represents a wall direction")
    print("="*70)
    print()

    # Count bit usage across all cells
    bit_counts_3 = [0] * 8
    bit_counts_5 = [0] * 8

    for cell in range(400):
        cell_start = cell * 8
        byte_3 = data[cell_start + 3]
        byte_5 = data[cell_start + 5]

        for bit in range(8):
            if byte_3 & (1 << bit):
                bit_counts_3[bit] += 1
            if byte_5 & (1 << bit):
                bit_counts_5[bit] += 1

    print("Bit usage in byte 3:")
    for bit in range(8):
        print(f"  Bit {bit} (0x{1<<bit:02X}): {bit_counts_3[bit]:3d} cells ({bit_counts_3[bit]/4:5.1f}%)")

    print()
    print("Bit usage in byte 5:")
    for bit in range(8):
        print(f"  Bit {bit} (0x{1<<bit:02X}): {bit_counts_5[bit]:3d} cells ({bit_counts_5[bit]/4:5.1f}%)")

    print()
    print("="*70)
    print("The ADDED bits in newgameold.dbs:")
    print()
    print("  Cell (3,15) byte 3: bit 7 (0x80)")
    print("  Cell (3,15) byte 5: bit 7 (0x80)")
    print("  Cell (4,19) byte 5: bits 7 and 5 (0xA0 = 0x80 | 0x20)")
    print()

    # Find all cells with bit 7 set in byte 3 or 5
    print("="*70)
    print("Cells with bit 7 (0x80) set in byte 3:")
    print()

    cells_with_b3_b7 = []
    for cell in range(400):
        cell_start = cell * 8
        byte_3 = data[cell_start + 3]
        if byte_3 & 0x80:
            row = cell // 20
            col = cell % 20
            cells_with_b3_b7.append((row, col, byte_3))

    for row, col, val in cells_with_b3_b7:
        print(f"  Cell ({row:2d},{col:2d}): {val:02X} = {val:08b}")

    print()
    print("Cells with bit 7 (0x80) set in byte 5:")
    print()

    cells_with_b5_b7 = []
    for cell in range(400):
        cell_start = cell * 8
        byte_5 = data[cell_start + 5]
        if byte_5 & 0x80:
            row = cell // 20
            col = cell % 20
            cells_with_b5_b7.append((row, col, byte_5))

    for row, col, val in cells_with_b5_b7:
        print(f"  Cell ({row:2d},{col:2d}): {val:02X} = {val:08b}")

    print()
    print("="*70)
    print("Looking at lower bits (potential wall directions):")
    print()

    # Check what combinations of low bits appear together
    print("Byte 3 value distribution (non-zero):")
    byte3_dist = defaultdict(int)
    for cell in range(400):
        cell_start = cell * 8
        byte_3 = data[cell_start + 3]
        if byte_3 != 0:
            byte3_dist[byte_3] += 1

    for val, count in sorted(byte3_dist.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {val:02X} = {val:08b}: {count:3d} cells")

    print()
    print("Byte 5 value distribution (non-zero):")
    byte5_dist = defaultdict(int)
    for cell in range(400):
        cell_start = cell * 8
        byte_5 = data[cell_start + 5]
        if byte_5 != 0:
            byte5_dist[byte_5] += 1

    for val, count in sorted(byte5_dist.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {val:02X} = {val:08b}: {count:3d} cells")

    print()
    print("="*70)
    print("SUMMARY:")
    print()
    print("Based on the changes:")
    print("  - Bit 7 in bytes 3 and 5 (0x80) appears to mark walls")
    print("  - Bit 5 in byte 5 (0x20) also changed in cell (4,19)")
    print()
    print("Possible encoding:")
    print("  Byte 3:")
    print("    Bit 7: North wall?")
    print("    Bit 6: South wall?")
    print("    Bits 0-5: Other properties")
    print()
    print("  Byte 5:")
    print("    Bit 7: East wall?")
    print("    Bit 6: ???")
    print("    Bit 5: West wall?")
    print("    Bits 0-4: Other properties")
    print()
    print("  OR bytes 3 and 5 could represent horizontal/vertical walls")
    print("  rather than per-direction walls")

def main():
    file_path = Path("gamedata/newgameold.dbs")

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        sys.exit(1)

    analyze_wall_bits(file_path)

if __name__ == "__main__":
    main()
