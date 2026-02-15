#!/usr/bin/env python3
"""Compare newgame.dbs and newgameold.dbs to find wall data encoding."""

import sys
from pathlib import Path

def compare_files(file1_path, file2_path):
    """Compare two binary files and show differences."""
    with open(file1_path, 'rb') as f1, open(file2_path, 'rb') as f2:
        data1 = f1.read()
        data2 = f2.read()

    if len(data1) != len(data2):
        print(f"Files have different sizes:")
        print(f"  {file1_path.name}: {len(data1)} bytes")
        print(f"  {file2_path.name}: {len(data2)} bytes")
        print()

    # Find all differing bytes
    differences = []
    min_len = min(len(data1), len(data2))

    for offset in range(min_len):
        if data1[offset] != data2[offset]:
            differences.append((offset, data1[offset], data2[offset]))

    print(f"Found {len(differences)} byte differences:\n")

    if len(differences) == 0:
        print("Files are identical!")
        return

    # Show differences in groups
    print(f"{'Offset':<10} | {'newgame.dbs':<15} | {'newgameold.dbs':<15} | Difference")
    print("-" * 70)

    for offset, byte1, byte2 in differences:
        diff = byte2 - byte1 if byte2 >= byte1 else f"-{byte1 - byte2}"
        print(f"0x{offset:08X} | 0x{byte1:02X} ({byte1:3d})   | 0x{byte2:02X} ({byte2:3d})   | {diff}")

    # Show context around differences
    print("\n" + "="*70)
    print("Byte differences with context (16 bytes before/after):")
    print("="*70 + "\n")

    for offset, byte1, byte2 in differences[:10]:  # Show first 10 for brevity
        start = max(0, offset - 16)
        end = min(len(data1), offset + 17)

        print(f"Offset 0x{offset:08X}:")
        print(f"  newgame.dbs:    ", end="")
        for i in range(start, end):
            if i == offset:
                print(f"[{data1[i]:02X}]", end=" ")
            else:
                print(f"{data1[i]:02X}", end=" ")
        print()

        print(f"  newgameold.dbs: ", end="")
        for i in range(start, end):
            if i == offset:
                print(f"[{data2[i]:02X}]", end=" ")
            else:
                print(f"{data2[i]:02X}", end=" ")
        print()
        print()

    # Group consecutive differences (might indicate bitfields)
    print("\n" + "="*70)
    print("Grouping consecutive differences:")
    print("="*70 + "\n")

    groups = []
    current_group = [differences[0]]

    for i in range(1, len(differences)):
        if differences[i][0] - differences[i-1][0] <= 16:  # Within 16 bytes
            current_group.append(differences[i])
        else:
            groups.append(current_group)
            current_group = [differences[i]]
    groups.append(current_group)

    for i, group in enumerate(groups):
        start_offset = group[0][0]
        end_offset = group[-1][0]
        print(f"Group {i+1}: Offsets 0x{start_offset:08X} - 0x{end_offset:08X} ({len(group)} bytes)")
        print(f"  Range: {end_offset - start_offset + 1} bytes span")

        # Show the changed bytes
        for offset, byte1, byte2 in group:
            xor = byte1 ^ byte2
            print(f"    0x{offset:08X}: {byte1:02X} -> {byte2:02X} (XOR: {xor:02X} = {xor:08b})")
        print()

if __name__ == "__main__":
    if len(sys.argv) == 3:
        file1 = Path(sys.argv[1])
        file2 = Path(sys.argv[2])
    else:
        file1 = Path("gamedata/newgame.dbs")
        file2 = Path("gamedata/newgameold.dbs")

    if not file1.exists():
        print(f"Error: {file1} not found")
        sys.exit(1)

    if not file2.exists():
        print(f"Error: {file2} not found")
        sys.exit(1)

    print(f"Comparing {file1.name} vs {file2.name}")
    print(f"(newgameold.dbs has walls on all 4 sides in top-right corner of map 1)\n")
    print("="*70 + "\n")

    compare_files(file1, file2)
