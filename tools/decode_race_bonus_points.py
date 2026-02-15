#!/usr/bin/env python3
"""
Decode race/profession bonus point costs from SCENARIO.DBS.
The manual mentions a chart showing how many bonus points each race needs to enter each profession.
"""
from pathlib import Path

RACES = ["Human", "Elf", "Dwarf", "Gnome", "Hobbit", "Faerie",
         "Lizardman", "Dracon", "Felpurr", "Rawulf", "Mook"]

CLASSES = ["Fighter", "Mage", "Priest", "Thief", "Ranger", "Alchemist",
           "Bard", "Psionic", "Valkyrie", "Bishop", "Lord", "Ninja",
           "Monk", "Samurai"]

def main():
    dbs_path = Path("C:/Users/marty/Documents/code/bane/gamedata/SCENARIO.DBS")

    with open(dbs_path, 'rb') as f:
        data = f.read()

    print("=" * 120)
    print("RACE/PROFESSION BONUS POINT COST TABLE ANALYSIS")
    print("=" * 120)
    print("\nThe manual mentions bonus points needed for each race to enter each profession.")
    print("Looking for 11 races × 14 classes table...\n")

    # Try 11 races × 14 classes
    offset = 0x009508
    rec_size = 14  # 14 classes

    print(f"Table at 0x{offset:06X} - 11 races × 14 bytes\n")
    print(f"{'Race':<12s}", end='')
    for cls in CLASSES:
        print(f" {cls[:3]:>3s}", end='')
    print()
    print("-" * (12 + len(CLASSES) * 4))

    for i, race in enumerate(RACES):
        rec_offset = offset + (i * rec_size)
        record = data[rec_offset:rec_offset + rec_size]

        print(f"{race:<12s}", end='')
        for b in record:
            print(f" {b:3d}", end='')
        print()

    # Alternative: Try looking at it as raw hex for patterns
    print("\n" + "=" * 120)
    print("ALTERNATIVE: Look for patterns in the data")
    print("=" * 120)

    # The Elf row was all zeros - that's suspicious
    # Let me look at a broader region
    print("\nExamining region 0x009400 - 0x0095FF for patterns:\n")

    region_start = 0x009400
    region_end = 0x009600
    region = data[region_start:region_end]

    # Find runs of non-zero data
    print("Non-zero data blocks:")
    in_block = False
    block_start = 0

    for i in range(len(region)):
        if region[i] != 0 and not in_block:
            in_block = True
            block_start = i
        elif region[i] == 0 and in_block:
            # Check for end of block (multiple zeros)
            zeros = 0
            while i + zeros < len(region) and region[i + zeros] == 0:
                zeros += 1
            if zeros > 5:  # More than 5 zeros = end of block
                block_len = i - block_start
                print(f"  0x{region_start + block_start:06X} - 0x{region_start + i:06X}: {block_len} bytes")
                in_block = False

    # Look at the specific region from our earlier analysis
    print("\n" + "=" * 120)
    print("HEX DUMP: Region around 0x009508")
    print("=" * 120 + "\n")

    dump_start = 0x009500
    dump_end = 0x009600
    dump = data[dump_start:dump_end]

    for i in range(0, len(dump), 16):
        hex_str = ' '.join(f'{b:02X}' for b in dump[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dump[i:i+16])
        print(f"  {dump_start+i:06X}: {hex_str:<48s} {ascii_str}")

    # Look for the 23-byte index that had 11 unique values
    print("\n" + "=" * 120)
    print("RACE INDEX ANALYSIS (23 bytes at 0x009409)")
    print("=" * 120 + "\n")

    index = data[0x009409:0x009409 + 23]
    print(f"Raw: {' '.join(f'{b:2d}' for b in index)}")
    print(f"Unique values: {sorted(set(index))} (count: {len(set(index))})")

    # Count frequency
    from collections import Counter
    freq = Counter(index)
    print(f"\nFrequency:")
    for val in sorted(freq.keys()):
        print(f"  {val:2d}: appears {freq[val]} times {'*' * freq[val]}")

    # If this is a race index, values 0-10 should map to races 0-10
    print(f"\nIf this maps to race IDs (0-10):")
    for i, val in enumerate(index):
        if val < len(RACES):
            print(f"  Position {i:2d}: {val} -> {RACES[val]}")

if __name__ == "__main__":
    main()
