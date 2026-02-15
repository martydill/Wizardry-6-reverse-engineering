#!/usr/bin/env python3
"""
Complete diff of the entire NEWGAME.DBS file to find ALL changes.
"""

def full_diff():
    """Compare entire files byte by byte."""
    with open('gamedata/NEWGAME0.DBS', 'rb') as f:
        orig = f.read()
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        modi = f.read()

    print(f"File sizes: Original={len(orig)}, Modified={len(modi)}")

    if len(orig) != len(modi):
        print("ERROR: File sizes differ!")
        return

    differences = []
    for i in range(len(orig)):
        if orig[i] != modi[i]:
            differences.append(i)

    print(f"\nTotal differences: {len(differences)} bytes")
    print()

    if len(differences) == 0:
        print("No differences found!")
        return

    # Group consecutive ranges
    ranges = []
    start = differences[0]
    end = differences[0]

    for offset in differences[1:]:
        if offset == end + 1:
            end = offset
        else:
            ranges.append((start, end))
            start = offset
            end = offset
    ranges.append((start, end))

    print(f"Changed regions: {len(ranges)}")
    print()

    for start, end in ranges:
        size = end - start + 1
        print(f"Region 0x{start:08X} to 0x{end:08X} ({size} bytes)")

        # Show the changes
        for offset in range(start, end + 1):
            print(f"  0x{offset:08X}: 0x{orig[offset]:02X} -> 0x{modi[offset]:02X} "
                  f"({orig[offset]:3d} -> {modi[offset]:3d})")

    # Check if we missed anything
    known_changes = {0x7D22, 0x7D45, 0x7D7E, 0x7DA1}
    found_changes = set(differences)

    if found_changes != known_changes:
        print(f"\n{'='*80}")
        print("UNEXPECTED CHANGES FOUND!")
        print(f"{'='*80}\n")

        unexpected = found_changes - known_changes
        if unexpected:
            print(f"Additional changes not in known set ({len(unexpected)}):")
            for offset in sorted(unexpected):
                print(f"  0x{offset:08X}: 0x{orig[offset]:02X} -> 0x{modi[offset]:02X}")

        missing = known_changes - found_changes
        if missing:
            print(f"\nExpected changes not found ({len(missing)}):")
            for offset in sorted(missing):
                print(f"  0x{offset:08X}")
    else:
        print(f"\n{'='*80}")
        print("ALL CHANGES ACCOUNTED FOR!")
        print(f"{'='*80}")
        print("\nOnly the 4 bytes in the feature table changed:")
        print("  - Entry #0: Byte 0 and Byte 35")
        print("  - Entry #1: Byte 0 and Byte 35")

def main():
    full_diff()

if __name__ == '__main__':
    main()
