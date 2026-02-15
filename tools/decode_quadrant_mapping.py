#!/usr/bin/env python3
"""
Understand how 2 feature entries map to 4 corner fountains.

Given:
- Map 10 is 16x16
- User added fountains in all 4 corners
- Only 2 entries were modified
- Each entry has byte 0 = 0x04, byte 35 = 0x40

Hypothesis: Each entry represents either:
1. A diagonal pair of corners (TL+BR vs TR+BL)
2. A horizontal pair (Top vs Bottom)
3. A vertical pair (Left vs Right)
4. Quadrants (NW+NE vs SW+SE, or NW+SW vs NE+SE)
"""

def analyze_byte_meanings():
    """Analyze what the bytes in each entry might mean."""

    print("="*80)
    print("FEATURE ENTRY STRUCTURE ANALYSIS")
    print("="*80)
    print()

    print("Entry #0 (0x7D22):")
    print("  Byte  0: 0x04 (  4) <-- ADDED by user")
    print("  Byte 17: 0x20 ( 32) <-- Pre-existing")
    print("  Byte 18: 0x77 (119) <-- Pre-existing")
    print("  Byte 35: 0x40 ( 64) <-- ADDED by user")
    print()
    print("Entry #1 (0x7D7E):")
    print("  Byte  0: 0x04 (  4) <-- ADDED by user")
    print("  Byte 35: 0x40 ( 64) <-- ADDED by user")
    print()

    print("="*80)
    print("HYPOTHESIS TESTING:")
    print("="*80)
    print()

    print("Byte 0 = 0x04:")
    print("  - Likely a feature type ID")
    print("  - 0x04 = 4 could mean 'fountain'")
    print("  - Both entries have same value, so same feature type")
    print()

    print("Byte 35 = 0x40:")
    print("  - 0x40 = 64 = 0b01000000 (bit 6 set)")
    print("  - Could be a flags field")
    print("  - Both entries have same value")
    print()

    print("Bytes 17-18 in Entry #0:")
    print("  - 0x20 = 32, 0x77 = 119")
    print("  - Could be coordinates, but outside 0-15 range for 16x16 map")
    print("  - Could be other attributes (item ID, text message ID, etc.)")
    print("  - Interesting: 0x77 = 119 was seen in spell level encoding!")
    print()

    print("="*80)
    print("QUADRANT/CORNER MAPPING:")
    print("="*80)
    print()

    print("Map 10 corners (16x16):")
    print("  (0,0)   - Top-Left")
    print("  (15,0)  - Top-Right")
    print("  (0,15)  - Bottom-Left")
    print("  (15,15) - Bottom-Right")
    print()

    print("Possible mappings for 2 entries -> 4 corners:")
    print()

    print("  Option 1: Diagonal pairs")
    print("    Entry #0: (0,0) + (15,15)  - Main diagonal")
    print("    Entry #1: (15,0) + (0,15)  - Anti-diagonal")
    print()

    print("  Option 2: Horizontal pairs")
    print("    Entry #0: (0,0) + (15,0)   - Top edge")
    print("    Entry #1: (0,15) + (15,15) - Bottom edge")
    print()

    print("  Option 3: Vertical pairs")
    print("    Entry #0: (0,0) + (0,15)   - Left edge")
    print("    Entry #1: (15,0) + (15,15) - Right edge")
    print()

    print("  Option 4: Quadrant-based")
    print("    Entry #0: NW + NE (top half)")
    print("    Entry #1: SW + SE (bottom half)")
    print()

    print("="*80)
    print("COORDINATE ENCODING ANALYSIS:")
    print("="*80)
    print()

    print("If bytes encode coordinates in 16x16 map:")
    print()

    # Try different encodings for corners
    corners = [(0, 0), (15, 0), (0, 15), (15, 15)]

    print("  Standard encoding (1 byte each):")
    for x, y in corners:
        print(f"    ({x:2d},{y:2d}) -> X=0x{x:02X} Y=0x{y:02X}")

    print()
    print("  Packed encoding (nibbles):")
    for x, y in corners:
        packed = (x << 4) | y
        print(f"    ({x:2d},{y:2d}) -> 0x{packed:02X} ({packed:3d})")

    print()
    print("  Bitfield encoding:")
    for x, y in corners:
        # Various bit patterns
        bit_x = (1 << x) if x < 8 else 0
        bit_y = (1 << y) if y < 8 else 0
        print(f"    ({x:2d},{y:2d}) -> X_bit=0x{bit_x:04X} Y_bit=0x{bit_y:04X}")

    print()
    print("="*80)
    print("LOOKING FOR POSITION DATA:")
    print("="*80)
    print()

    print("Question: Where are the X,Y coordinates of the fountains stored?")
    print()
    print("Possibilities:")
    print("  1. In the 92-byte entries (somewhere we haven't identified yet)")
    print("  2. In the map cell data itself (the 20 bytes per cell)")
    print("  3. In a separate lookup table")
    print("  4. Derived algorithmically (e.g., 'entry N = corners of quadrant N')")
    print()

    print("Next step: Check if map cell data changed for the 4 corner cells!")

def check_corner_cells():
    """Check if the corner cells in Map 10 have any feature markers."""

    print("\n" + "="*80)
    print("CHECKING MAP 10 CORNER CELLS:")
    print("="*80)
    print()

    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()

    with open('gamedata/NEWGAME0.DBS', 'rb') as f:
        orig_data = f.read()

    map10_offset = 0xA000
    cell_size = 20

    corners = {
        'Top-Left (0,0)': (0, 0),
        'Top-Right (15,0)': (15, 0),
        'Bottom-Left (0,15)': (0, 15),
        'Bottom-Right (15,15)': (15, 15)
    }

    print("Column-major storage: cell_index = (col * 16) + row")
    print()

    for corner_name, (x, y) in corners.items():
        cell_index = x * 16 + y
        cell_offset = map10_offset + (cell_index * cell_size)

        print(f"{corner_name}:")
        print(f"  Cell index: {cell_index}")
        print(f"  Offset: 0x{cell_offset:08X}")

        # Check if this cell changed
        cell_orig = orig_data[cell_offset:cell_offset + cell_size]
        cell_new = data[cell_offset:cell_offset + cell_size]

        if cell_orig != cell_new:
            print(f"  ** CELL CHANGED!")
            for i in range(cell_size):
                if cell_orig[i] != cell_new[i]:
                    print(f"    Byte {i:2d}: 0x{cell_orig[i]:02X} -> 0x{cell_new[i]:02X}")
        else:
            print(f"  Cell unchanged")

        # Show a few bytes anyway
        print(f"  First 10 bytes: {' '.join(f'{b:02X}' for b in cell_new[:10])}")
        print()

def main():
    analyze_byte_meanings()
    check_corner_cells()

if __name__ == '__main__':
    main()
