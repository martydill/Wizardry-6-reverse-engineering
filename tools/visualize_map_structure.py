#!/usr/bin/env python3
"""
Create a visual summary of what we learned about the map format.
"""

def print_file_layout():
    """Show the NEWGAME.DBS file layout."""
    print("=" * 80)
    print("NEWGAME.DBS FILE STRUCTURE")
    print("=" * 80)
    print()

    print("  0x00000 +----------------------------------------+")
    print("          |                                        |")
    print("          |  Unknown data                          |")
    print("          |  (~32KB)                               |")
    print("          |                                        |")
    print("  0x07B2E +----------------------------------------+ <-- Feature Table Start (approx)")
    print("          |                                        |")
    print("          |  Feature Entries (92 bytes each)       |")
    print("          |                                        |")
    print("  0x07D22 |    Entry #0  +------------------+     | <-- MODIFIED!")
    print("          |              | Byte 0:  0x04    |     |     (Fountain type)")
    print("          |              | Byte 35: 0x40    |     |     (Active flag)")
    print("          |              +------------------+     |")
    print("          |                                        |")
    print("  0x07D7E |    Entry #1  +------------------+     | <-- MODIFIED!")
    print("          |              | Byte 0:  0x04    |     |     (Fountain type)")
    print("          |              | Byte 35: 0x40    |     |     (Active flag)")
    print("          |              +------------------+     |")
    print("          |                                        |")
    print("          |  More entries...                       |")
    print("          |                                        |")
    print("  0x0A000 +----------------------------------------+ <-- Map 10 Data Start")
    print("          |                                        |")
    print("          |  Map 10 (16x16)                        |")
    print("          |  256 cells x 20 bytes = 5,120 bytes    |")
    print("          |                                        |")
    print("          |  Cell data (walls, terrain)            |")
    print("          |  NO feature position data!             |")
    print("          |                                        |")
    print("  0x0B400 +----------------------------------------+")
    print("          |                                        |")
    print("          |  Other maps and data                   |")
    print("          |  (~35KB)                               |")
    print("          |                                        |")
    print("  0x0C2C0 +----------------------------------------+ EOF (49,856 bytes)")
    print()

def print_entry_structure():
    """Show the 92-byte feature entry structure."""
    print("=" * 80)
    print("FEATURE ENTRY STRUCTURE (92 bytes)")
    print("=" * 80)
    print()

    print("  +0x00  +----------------------------------------+")
    print("         | Feature Type ID (1 byte)               | <- 0x00 = Empty, 0x04 = Fountain")
    print("  +0x01  +----------------------------------------+")
    print("         |                                        |")
    print("         | Unknown data (16 bytes)                |")
    print("         |                                        |")
    print("  +0x11  +----------------------------------------+")
    print("         | Unknown (2 bytes)                      | <- Entry #0 had 0x20 0x77 here")
    print("  +0x13  +----------------------------------------+")
    print("         |                                        |")
    print("         | Unknown data (16 bytes)                |")
    print("         |                                        |")
    print("  +0x23  +----------------------------------------+")
    print("  (35)   | Feature Flags (1 byte)                 | <- 0x00 = Disabled, 0x40 = Active")
    print("  +0x24  +----------------------------------------+")
    print("         |                                        |")
    print("         | Unknown data (56 bytes)                |")
    print("         |                                        |")
    print("         |                                        |")
    print("         |                                        |")
    print("  +0x5C  +----------------------------------------+")
    print("  (92)                                             ")
    print()

def print_position_mapping():
    """Show the 2 entries -> 4 corners mapping."""
    print("=" * 80)
    print("FEATURE POSITION MAPPING")
    print("=" * 80)
    print()

    print("Map 10 (16x16) with fountains in all 4 corners:")
    print()
    print("      0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15")
    print("    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print("  0 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |")
    print("    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print("  1 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print("  . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("  . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("  . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 15 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |")
    print("    +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print()
    print("  F = Fountain")
    print()
    print("  Corners:")
    print("    (0,0)   = Top-Left")
    print("    (15,0)  = Top-Right")
    print("    (0,15)  = Bottom-Left")
    print("    (15,15) = Bottom-Right")
    print()

    print("=" * 80)
    print("ENTRY -> POSITION MAPPING (HYPOTHESIS)")
    print("=" * 80)
    print()

    print("  Entry #0 controls 2 fountains:")
    print("    -> Position A")
    print("    -> Position B")
    print()
    print("  Entry #1 controls 2 fountains:")
    print("    -> Position C")
    print("    -> Position D")
    print()

    print("  Most likely mapping (diagonal pairs):")
    print()
    print("    Entry #0 -> (0,0) + (15,15)   [Main diagonal]")
    print("    Entry #1 -> (15,0) + (0,15)   [Anti-diagonal]")
    print()

    print("  Alternative mappings:")
    print()
    print("    Horizontal: Entry #0 = top row, Entry #1 = bottom row")
    print("    Vertical:   Entry #0 = left col, Entry #1 = right col")
    print("    Quadrants:  Entry #0 = north half, Entry #1 = south half")
    print()

def print_key_insights():
    """Print the key discoveries."""
    print("=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    print()

    insights = [
        "1. Feature data is SEPARATE from map cell data",
        "",
        "2. Positions are IMPLICIT - determined by entry index,",
        "   not stored as X,Y coordinates",
        "",
        "3. Each feature entry can control MULTIPLE positions",
        "   (1 entry = 2+ map locations)",
        "",
        "4. Only 2 bytes needed to activate a feature:",
        "   - Byte 0: Feature type (fountain, door, etc.)",
        "   - Byte 35: Enable/disable flag",
        "",
        "5. Map cells (20 bytes) store only walls and terrain,",
        "   NOT interactive features",
        "",
        "6. This is an efficient design for 1990s storage:",
        "   - Common features (4 corner fountains) = 4 bytes",
        "   - vs storing 4 separate position records = 16+ bytes"
    ]

    for insight in insights:
        print(f"  {insight}")

    print()

def main():
    print_file_layout()
    print()
    print_entry_structure()
    print()
    print_position_mapping()
    print()
    print_key_insights()

if __name__ == '__main__':
    main()
