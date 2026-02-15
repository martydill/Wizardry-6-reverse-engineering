#!/usr/bin/env python3
"""
Focused analysis of the region around 0x009508 which shows structured data.
"""
import struct
from pathlib import Path

RACES = ["Human", "Elf", "Dwarf", "Gnome", "Hobbit", "Faerie", "Lizardman", "Dracon", "Felpurr", "Rawulf", "Mook"]
CLASSES = ["Fighter", "Mage", "Priest", "Thief", "Ranger", "Alchemist", "Bard", "Psionic", "Valkyrie", "Bishop", "Lord", "Ninja", "Monk", "Samurai"]
STATS = ["STR", "INT", "PIE", "VIT", "DEX", "SPD", "KAR"]

def analyze_as_table(data, offset, num_records, rec_size, labels):
    """Display data as a table with given structure."""
    print(f"\nInterpreting as {num_records} × {rec_size} byte table at 0x{offset:06X}:")
    print(f"{'Label':<15s}", end='')
    for i in range(rec_size):
        print(f" {i:02d}", end='')
    print()
    print("-" * (15 + rec_size * 3))

    for i in range(num_records):
        rec_offset = offset + i * rec_size
        record = data[rec_offset:rec_offset + rec_size]
        label = labels[i] if i < len(labels) else f"Record {i}"
        print(f"{label:<15s}", end='')
        for b in record:
            print(f" {b:02X}", end='')
        print(f"  | ", end='')
        # Show as decimal for stat-like interpretation
        for b in record:
            print(f"{b:3d}", end='')
        print()

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    print("=" * 80)
    print("ANALYSIS OF STRUCTURED REGION AROUND 0x009508")
    print("=" * 80)

    # The promising region starts around 0x009508
    # Let's try different interpretations

    # Try as 11 races × varying byte sizes
    print("\n" + "=" * 80)
    print("ATTEMPT 1: Race Table Interpretation")
    print("=" * 80)

    # The pattern at 009508 has some leading bytes, then the structured data
    # Let's try starting at different offsets and record sizes

    for start_offset in [0x009508, 0x009509, 0x00950A, 0x00950B]:
        for rec_size in [10, 11, 12, 13, 14, 15, 16]:
            total = 11 * rec_size
            if start_offset + total > len(data):
                continue

            # Check if this looks reasonable
            block = data[start_offset:start_offset + total]
            # Skip if too many zeros (first record shouldn't be all zero for races)
            first_rec = block[:rec_size]
            if first_rec.count(0) == rec_size:
                continue

            print(f"\n{'-'*80}")
            analyze_as_table(data, start_offset, 11, rec_size, RACES)

    # Try as 14 classes × varying byte sizes
    print("\n\n" + "=" * 80)
    print("ATTEMPT 2: Class Table Interpretation")
    print("=" * 80)

    for start_offset in [0x009508, 0x009509, 0x00950A, 0x00950B]:
        for rec_size in [10, 11, 12, 13, 14, 15, 16]:
            total = 14 * rec_size
            if start_offset + total > len(data):
                continue

            # Check if this looks reasonable
            block = data[start_offset:start_offset + total]
            first_rec = block[:rec_size]
            if first_rec.count(0) == rec_size:
                continue

            print(f"\n{'-'*80}")
            analyze_as_table(data, start_offset, 14, rec_size, CLASSES)

    # Also analyze the 224-byte block that's exactly 14 × 16
    print("\n\n" + "=" * 80)
    print("ANALYSIS OF 224-BYTE BLOCK AT 0x00A0B3 (14 × 16)")
    print("=" * 80)
    analyze_as_table(data, 0x00A0B3, 14, 16, CLASSES)

    # Show interpretation as bit flags
    print("\n\nBit-field interpretation (showing non-zero bytes only):")
    for i in range(14):
        rec_offset = 0x00A0B3 + i * 16
        record = data[rec_offset:rec_offset + 16]
        label = CLASSES[i]
        non_zero = [(j, record[j]) for j in range(16) if record[j] != 0]
        if non_zero:
            print(f"  {label:<15s}: ", end='')
            for pos, val in non_zero:
                print(f"[{pos}]=0x{val:02X} ", end='')
            print()

if __name__ == "__main__":
    main()
