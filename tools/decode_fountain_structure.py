#!/usr/bin/env python3
"""
Decode the fountain structure based on observed changes.
Pattern: entries are spaced 92 bytes apart (0x5C)
"""

def analyze_structure(filepath):
    """Analyze the complete fountain/feature structure."""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Changed offsets
    changed = {
        0x7D22: 0x04,
        0x7D45: 0x40,
        0x7D7E: 0x04,
        0x7DA1: 0x40
    }

    # Calculate entry spacing
    print("="*80)
    print("ENTRY SPACING ANALYSIS:")
    print("="*80)
    print()

    offsets_04 = [0x7D22, 0x7D7E]
    offsets_40 = [0x7D45, 0x7DA1]

    print("Offsets with value 0x04:")
    for i, offset in enumerate(offsets_04):
        print(f"  Entry {i}: 0x{offset:08X}")
        if i > 0:
            spacing = offset - offsets_04[i-1]
            print(f"    Spacing from previous: {spacing} bytes (0x{spacing:02X})")

    print("\nOffsets with value 0x40:")
    for i, offset in enumerate(offsets_40):
        print(f"  Entry {i}: 0x{offset:08X}")
        if i > 0:
            spacing = offset - offsets_40[i-1]
            print(f"    Spacing from previous: {spacing} bytes (0x{spacing:02X})")

    print(f"\nEntry size: 92 bytes (0x5C)")
    print(f"Within each entry:")
    print(f"  Byte 0: 0x04")
    print(f"  Byte {0x7D45 - 0x7D22}: 0x40")

    # Now scan the entire structure
    entry_size = 92
    byte_0_offset = 0x7D22
    byte_35_offset = 0x7D45

    # Find the start of this table - scan backwards
    print(f"\n{'='*80}")
    print("FINDING TABLE START:")
    print(f"{'='*80}\n")

    # Look for first non-zero region before our entries
    table_start = None
    for offset in range(0x7D22 - 500, 0x7D22):
        if data[offset] != 0:
            # Check if this is sustained (not just a random byte)
            if any(data[offset + i] != 0 for i in range(1, min(20, 0x7D22 - offset))):
                table_start = offset
                break

    if table_start is None:
        # If no non-zero found, scan for end of previous zero block
        for offset in range(0x7D22 - 1, 0x7D22 - 500, -1):
            if data[offset] == 0 and (offset == 0 or data[offset - 1] != 0):
                table_start = offset
                break

    if table_start:
        print(f"Table likely starts at: 0x{table_start:08X}")
        print(f"Distance to first 0x04 entry: {0x7D22 - table_start} bytes")

        # Calculate which entry number our changes are
        entry_index_0 = (0x7D22 - table_start) // entry_size
        print(f"First changed entry is entry #{entry_index_0}")

    # Dump all entries in the suspected range
    print(f"\n{'='*80}")
    print("FULL STRUCTURE DUMP:")
    print(f"{'='*80}\n")

    # Assume the table might have many entries
    # Start from first changed entry and work backwards/forwards
    base_offset = 0x7D22  # First 0x04

    print("Scanning backwards for start of table...")
    for i in range(20):  # Check up to 20 entries back
        offset = base_offset - (i * entry_size)
        if offset < 0:
            break

        # Check if this entry has any data
        entry_data = data[offset:offset + entry_size]
        if any(b != 0 for b in entry_data):
            print(f"Entry #{-i} at 0x{offset:08X}: Has non-zero data")
        elif i > 2:
            # If we've seen 2+ empty entries, assume we've gone past the start
            print(f"Found {i} empty entries backwards, stopping")
            break

    print("\nScanning forwards for end of table...")
    for i in range(40):  # Check many entries forward
        offset = base_offset + (i * entry_size)
        if offset + entry_size > len(data):
            break

        entry_data = data[offset:offset + entry_size]
        non_zero_count = sum(1 for b in entry_data if b != 0)

        if non_zero_count > 0:
            print(f"Entry #{i} at 0x{offset:08X}: {non_zero_count} non-zero bytes")

            # Show a few bytes of this entry
            sample = ' '.join(f'{b:02X}' for b in entry_data[:16])
            print(f"  First 16 bytes: {sample}")

            # Highlight changed bytes
            for changed_offset, changed_val in changed.items():
                if offset <= changed_offset < offset + entry_size:
                    byte_pos = changed_offset - offset
                    print(f"  ** Byte {byte_pos} = 0x{changed_val:02X} (CHANGED)")

    # Now compare with original to find ALL differences
    print(f"\n{'='*80}")
    print("COMPLETE DIFF IN SUSPECTED TABLE REGION:")
    print(f"{'='*80}\n")

    with open('gamedata/NEWGAME0.DBS', 'rb') as f:
        orig_data = f.read()

    # Scan the region around the changes
    scan_start = 0x7D22 - 500
    scan_end = 0x7DA1 + 500

    diffs = []
    for offset in range(scan_start, scan_end):
        if data[offset] != orig_data[offset]:
            diffs.append((offset, orig_data[offset], data[offset]))

    print(f"Found {len(diffs)} differences in region 0x{scan_start:08X} to 0x{scan_end:08X}")
    for offset, old_val, new_val in diffs:
        print(f"  0x{offset:08X}: 0x{old_val:02X} -> 0x{new_val:02X}")

def main():
    analyze_structure('gamedata/NEWGAME.DBS')

if __name__ == '__main__':
    main()
