#!/usr/bin/env python3
"""
Visualize the feature mapping for both fountains and sconces.
"""

def print_summary():
    """Print a summary of the discoveries."""
    print("=" * 80)
    print("WIZARDRY 6 FEATURE SYSTEM - COMPLETE ANALYSIS")
    print("=" * 80)
    print()

    print("Test Case 1: 4 Corner Fountains")
    print("  Positions: (0,0), (15,0), (0,15), (15,15)")
    print("  Changes: 4 bytes in 2 entries")
    print()

    print("Test Case 2: 4 Center Sconces (Quadrant Corners)")
    print("  Positions: (7,7), (8,7), (7,8), (8,8)")
    print("  Changes: 4 additional bytes in SAME 2 entries")
    print()

    print("=" * 80)
    print("BREAKTHROUGH: Multiple Features Per Entry!")
    print("=" * 80)
    print()

def print_entry_changes():
    """Show the byte changes in each entry."""
    print("=" * 80)
    print("ENTRY CHANGES:")
    print("=" * 80)
    print()

    print("Entry #0 (0x7D22) - 5 bytes changed:")
    print("  +---+-------+---------+-----------+---------------------------+")
    print("  | # | Hex   | Old->New| Decimal   | Meaning                   |")
    print("  +---+-------+---------+-----------+---------------------------+")
    print("  | 0 | 0x00  | 00->04  |   0 ->  4 | Fountain type ID          |")
    print("  |31 | 0x1F  | 00->30  |   0 -> 48 | Sconce attribute?         |")
    print("  |35 | 0x23  | 00->40  |   0 -> 64 | Enable flag (bit 6)       |")
    print("  |60 | 0x3C  | 00->03  |   0 ->  3 | Sconce type ID            |")
    print("  |67 | 0x43  | 00->30  |   0 -> 48 | Sconce attribute?         |")
    print("  +---+-------+---------+-----------+---------------------------+")
    print()

    print("Entry #1 (0x7D7E) - 3 bytes changed:")
    print("  +---+-------+---------+-----------+---------------------------+")
    print("  | # | Hex   | Old->New| Decimal   | Meaning                   |")
    print("  +---+-------+---------+-----------+---------------------------+")
    print("  | 0 | 0x00  | 00->04  |   0 ->  4 | Fountain type ID          |")
    print("  | 4 | 0x04  | 00->03  |   0 ->  3 | Sconce type ID            |")
    print("  |35 | 0x23  | 00->40  |   0 -> 64 | Enable flag (bit 6)       |")
    print("  +---+-------+---------+-----------+---------------------------+")
    print()

def print_feature_types():
    """Show the discovered feature type IDs."""
    print("=" * 80)
    print("FEATURE TYPE IDs:")
    print("=" * 80)
    print()

    print("  0x03 = Sconce")
    print("  0x04 = Fountain")
    print("  0x40 = Enable flag (byte 35)")
    print("  0x30 = Unknown attribute (sconce-related)")
    print()

def print_position_mapping():
    """Show the hypothesized position mapping."""
    print("=" * 80)
    print("POSITION MAPPING THEORY: Diagonal Pairs")
    print("=" * 80)
    print()

    print("Entry #0 controls MAIN DIAGONAL positions:")
    print()
    print("     0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 0 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 1 |   | . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 2 |   |   | . |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" . |   |   |   | . |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 7 |   |   |   |   |   |   |   | S |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 8 |   |   |   |   |   |   |   |   | S |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" . |   |   |   |   |   |   |   |   |   | . |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print("15 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print()
    print("  F = Fountain at (0,0) and (15,15)")
    print("  S = Sconce at (7,7) and (8,8)")
    print("  . = Main diagonal")
    print()

    print("Entry #1 controls ANTI-DIAGONAL positions:")
    print()
    print("     0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 0 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 1 |   |   |   |   |   |   |   |   |   |   |   |   |   |   | . |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 2 |   |   |   |   |   |   |   |   |   |   |   |   |   | . |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" . |   |   |   |   |   |   |   |   |   |   |   |   | . |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 7 |   |   |   |   |   |   |   |   | S |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" 8 |   |   |   |   |   |   |   | S |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print(" . |   |   |   |   |   |   | . |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print("15 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |")
    print("   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+")
    print()
    print("  F = Fountain at (15,0) and (0,15)")
    print("  S = Sconce at (8,7) and (7,8)")
    print("  . = Anti-diagonal")
    print()

def print_key_insights():
    """Print the key discoveries."""
    print("=" * 80)
    print("KEY INSIGHTS:")
    print("=" * 80)
    print()

    insights = [
        "1. Each entry can hold MULTIPLE feature types",
        "   - Entry #0: Fountains (byte 0) + Sconces (byte 60)",
        "   - Entry #1: Fountains (byte 0) + Sconces (byte 4)",
        "",
        "2. Positions follow DIAGONAL PATTERNS",
        "   - Entry #0 = Main diagonal (0,0)->(15,15)",
        "   - Entry #1 = Anti-diagonal (15,0)->(0,15)",
        "",
        "3. Feature type IDs identified:",
        "   - 0x03 = Sconce",
        "   - 0x04 = Fountain",
        "",
        "4. Byte 35 = Universal enable flag (0x40)",
        "   - Same flag activates ALL features in entry",
        "",
        "5. Mystery value 0x30 appears in Entry #0 only",
        "   - At bytes 31 and 67 (sconce-related)",
        "   - Not present in Entry #1",
        "   - Possibly position/orientation data?",
        "",
        "6. Feature slots at DIFFERENT byte positions",
        "   - Not a fixed slot structure",
        "   - Entry #0: sconce at byte 60",
        "   - Entry #1: sconce at byte 4",
        "",
        "7. Still NO explicit X,Y coordinates found",
        "   - Positions are implicit based on entry number",
        "   - Very efficient storage design",
    ]

    for insight in insights:
        print(f"  {insight}")

    print()

def print_next_steps():
    """Print recommended next tests."""
    print("=" * 80)
    print("RECOMMENDED NEXT TESTS:")
    print("=" * 80)
    print()

    print("To confirm diagonal theory:")
    print("  1. Remove ONLY top-left fountain (0,0)")
    print("     -> Should change Entry #0, byte 0")
    print()
    print("  2. Remove ONLY top-right fountain (15,0)")
    print("     -> Should change Entry #1, byte 0")
    print()
    print("  3. Add fountain at (1,1) ONLY")
    print("     -> Which entry changes? New pattern?")
    print()

    print("To understand 0x30 value:")
    print("  1. Remove sconces one at a time")
    print("     -> See which bytes clear")
    print()
    print("  2. Add sconces at different positions")
    print("     -> Does 0x30 change?")
    print()

def main():
    print_summary()
    print()
    print_entry_changes()
    print()
    print_feature_types()
    print()
    print_position_mapping()
    print()
    print_key_insights()
    print()
    print_next_steps()

if __name__ == '__main__':
    main()
