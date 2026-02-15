#!/usr/bin/env python3
"""
Deep analysis of the cross pattern to understand wall encoding.
"""

from pathlib import Path

def read_file(filepath):
    with open(filepath, 'rb') as f:
        return f.read()

def main():
    f_orig = read_file(Path("gamedata/newgameoriginal.dbs"))
    f_new = read_file(Path("gamedata/NEWGAME.DBS"))

    print("DEEP ANALYSIS: Cross Pattern Wall Encoding")
    print("="*80)
    print()

    # Find differences
    diffs = []
    for i in range(min(len(f_orig), len(f_new))):
        if f_orig[i] != f_new[i]:
            diffs.append((i, f_orig[i], f_new[i]))

    print(f"Total changes: {len(diffs)} bytes")
    print()

    # Analyze each change
    print("CHANGE DETAILS:")
    print("-"*80)
    for offset, old, new in diffs:
        cell_idx = offset // 20
        byte_in_cell = offset % 20
        col = cell_idx // 20
        row = cell_idx % 20

        xor = old ^ new

        print(f"\nOffset 0x{offset:04X} ({offset})")
        print(f"  Cell {cell_idx} (Column {col}, Row {row})")
        print(f"  Byte {byte_in_cell} ({'ODD' if byte_in_cell % 2 == 1 else 'EVEN'})")
        print(f"  Value: 0x{old:02X} -> 0x{new:02X}")
        print(f"  XOR: 0x{xor:02X} = {xor:08b}")
        print(f"  Bits set in XOR: {[i for i in range(8) if xor & (1<<i)]}")

    # Look for patterns
    print()
    print("="*80)
    print("PATTERN ANALYSIS:")
    print("="*80)
    print()

    # Group by cell
    by_cell = {}
    for offset, old, new in diffs:
        cell_idx = offset // 20
        byte_in_cell = offset % 20
        if cell_idx not in by_cell:
            by_cell[cell_idx] = []
        by_cell[cell_idx].append((byte_in_cell, old, new))

    print(f"Cells affected: {sorted(by_cell.keys())}")
    print()

    # Analyze byte positions
    byte_positions = set()
    for offset, old, new in diffs:
        byte_in_cell = offset % 20
        byte_positions.add(byte_in_cell)

    print(f"Byte positions affected: {sorted(byte_positions)}")
    print()

    # Analyze bit patterns
    bits_set = {}
    for offset, old, new in diffs:
        xor = old ^ new
        for bit in range(8):
            if xor & (1 << bit):
                if bit not in bits_set:
                    bits_set[bit] = 0
                bits_set[bit] += 1

    print("Bits affected across all changes:")
    for bit in sorted(bits_set.keys(), reverse=True):
        count = bits_set[bit]
        print(f"  Bit {bit}: changed in {count} byte(s)")

    # Check for relationships between cells
    print()
    print("="*80)
    print("CELL RELATIONSHIP:")
    print("="*80)
    print()

    cells = sorted(by_cell.keys())
    if len(cells) == 2:
        cell1, cell2 = cells
        col1, row1 = cell1 // 20, cell1 % 20
        col2, row2 = cell2 // 20, cell2 % 20

        print(f"Cell {cell1}: Column {col1}, Row {row1}")
        print(f"Cell {cell2}: Column {col2}, Row {row2}")
        print()
        print(f"Column difference: {abs(col2 - col1)}")
        print(f"Row difference: {abs(row2 - row1)}")
        print(f"Cell index difference: {cell2 - cell1}")

    # Examine surrounding context
    print()
    print("="*80)
    print("CONTEXT EXAMINATION:")
    print("="*80)
    print()

    for cell_idx in sorted(by_cell.keys()):
        col = cell_idx // 20
        row = cell_idx % 20

        print(f"\nCell {cell_idx} (Column {col}, Row {row}):")

        # Show full 20-byte structure for this cell
        offset = cell_idx * 20
        cell_orig = f_orig[offset:offset+20]
        cell_new = f_new[offset:offset+20]

        print("  ORIGINAL bytes (non-zero):")
        print("    ", end="")
        for i in range(20):
            if cell_orig[i] != 0:
                print(f"[{i}:0x{cell_orig[i]:02X}]", end=" ")
        print()

        print("  NEW bytes (non-zero):")
        print("    ", end="")
        for i in range(20):
            if cell_new[i] != 0:
                marker = "*" if cell_orig[i] != cell_new[i] else ""
                print(f"[{i}:0x{cell_new[i]:02X}]{marker}", end=" ")
        print()

        print("  CHANGED bytes:")
        for byte_idx, old, new in by_cell[cell_idx]:
            xor = old ^ new
            print(f"    Byte {byte_idx:2d}: 0x{old:02X} -> 0x{new:02X} (XOR 0x{xor:02X})")

    # Check if this might be a different data structure
    print()
    print("="*80)
    print("HYPOTHESES:")
    print("="*80)
    print()

    print("Hypothesis 1: Each ODD byte represents a wall direction")
    print(f"  - Byte 3 changed in cell {cells[0]}")
    if len(cells) > 1:
        print(f"  - Bytes 15, 17 changed in cell {cells[1]}")
    print("  - Different bytes = different wall types or positions?")
    print()

    print("Hypothesis 2: Bit 7 and Bit 5 encode different wall properties")
    print("  - Bit 7: Set in 1 byte (0xA0)")
    print("  - Bit 5: Set in 3 bytes (0xA0, 0x20, 0x20)")
    print("  - Maybe: Bit 7 = vertical, Bit 5 = horizontal?")
    print()

    print("Hypothesis 3: Cells 30 and 39 are not game cells")
    print("  - They might be indices into a wall table")
    print("  - Or they represent something else entirely")
    print()

    print("User added: 2 horizontal + 2 vertical walls in a cross pattern")
    print("Data shows: 3 byte changes encoding these 4 walls")
    print("  - 1 byte with bits 5+7 (maybe 2 walls?)")
    print("  - 2 bytes with bit 5 only (maybe 1 wall each?)")

if __name__ == "__main__":
    main()
