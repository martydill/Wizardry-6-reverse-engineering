#!/usr/bin/env python3
"""Analyze wall encoding based on the differences found."""

import sys
from pathlib import Path

def analyze_byte_as_walls(byte_val):
    """Try to interpret a byte as wall flags."""
    # Common wall bit patterns (guessing):
    # Bit 7 (0x80) = North wall
    # Bit 6 (0x40) = South wall
    # Bit 5 (0x20) = East wall
    # Bit 4 (0x10) = West wall
    # Lower bits might be special properties

    walls = []
    if byte_val & 0x80:
        walls.append("N")
    if byte_val & 0x40:
        walls.append("S")
    if byte_val & 0x20:
        walls.append("E")
    if byte_val & 0x10:
        walls.append("W")

    return f"{byte_val:02X} = {byte_val:08b} -> {'+'.join(walls) if walls else 'none'}"

def find_map_structure(filepath):
    """Try to find repeating structure around the changed bytes."""
    with open(filepath, 'rb') as f:
        data = f.read()

    # The differences were at:
    # 0x25B, 0x25D (2 bytes apart)
    # 0x31D (0xC2 = 194 bytes after 0x25B)

    offsets = [0x25B, 0x25D, 0x31D]

    print("Analyzing structure around changed bytes:\n")
    print("="*70)

    for offset in offsets:
        print(f"\nOffset 0x{offset:08X} ({offset}):")

        # Look for patterns - check every N bytes before this offset
        # to see if there's a repeating structure

        # Show 64 bytes around this location
        start = max(0, offset - 32)
        end = min(len(data), offset + 32)

        # Print in rows of 16 bytes
        for row_start in range(start, end, 16):
            row_end = min(row_start + 16, end)

            # Print offset
            print(f"  {row_start:08X}: ", end="")

            # Print hex
            for i in range(row_start, row_end):
                if i == offset:
                    print(f"[{data[i]:02X}]", end=" ")
                else:
                    print(f"{data[i]:02X}", end=" ")

            # Pad if needed
            for i in range(row_end, row_start + 16):
                print("   ", end="")

            # Print ASCII
            print("  ", end="")
            for i in range(row_start, row_end):
                c = data[i]
                if 32 <= c < 127:
                    ch = chr(c)
                else:
                    ch = "."

                if i == offset:
                    print(f"[{ch}]", end="")
                else:
                    print(ch, end="")

            print()

    print("\n" + "="*70)
    print("Analyzing difference pattern:\n")

    print("If these bytes represent walls on all 4 sides in top-right corner:")
    print("  User said: newgameold has 'walls on all 4 sides'")
    print()

    # Check the actual bytes
    byte_25B = data[0x25B]
    byte_25D = data[0x25D]
    byte_31D = data[0x31D]

    print(f"Offset 0x25B in newgameold: {analyze_byte_as_walls(byte_25B)}")
    print(f"Offset 0x25D in newgameold: {analyze_byte_as_walls(byte_25D)}")
    print(f"Offset 0x31D in newgameold: {analyze_byte_as_walls(byte_31D)}")

    print("\nAlternative interpretation (different bit assignment):")
    print("  0x80 = 10000000")
    print("  0xA0 = 10100000")

    print("\nLooking for grid structure:")
    # Assume map might be stored as grid cells
    # Check if there's a repeating pattern

    # Distance between first two changes: 0x25D - 0x25B = 2 bytes
    # Distance to third change: 0x31D - 0x25B = 0xC2 = 194 bytes

    print(f"  Offset 0x25B to 0x25D: {0x25D - 0x25B} bytes apart")
    print(f"  Offset 0x25B to 0x31D: {0x31D - 0x25B} bytes apart (0x{0x31D - 0x25B:X})")
    print(f"  Offset 0x25D to 0x31D: {0x31D - 0x25D} bytes apart (0x{0x31D - 0x25D:X})")

    # Try some grid sizes
    print("\nTrying to find grid pattern:")
    for stride in [16, 20, 32, 64, 97, 194]:
        print(f"  If stride = {stride}: 0x31D = 0x25B + {(0x31D - 0x25B) // stride} rows")

def main():
    file_path = Path("gamedata/newgameold.dbs")

    if not file_path.exists():
        print(f"Error: {file_path} not found")
        sys.exit(1)

    find_map_structure(file_path)

if __name__ == "__main__":
    main()
