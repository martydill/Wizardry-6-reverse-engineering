"""Analyze all 08 08 (32x32) occurrences to find the pattern.

We found 6 occurrences. Let's examine each one in detail.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def analyze():
    """Analyze 08 08 occurrences."""
    print("Analyzing 08 08 Pattern Occurrences")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    # Find all 08 08 occurrences
    occurrences = []
    for i in range(TILE_DATA_OFFSET - 1):
        if data[i] == 0x08 and data[i+1] == 0x08:
            occurrences.append(i)

    print(f"Found {len(occurrences)} occurrences of 08 08 in metadata region\n")

    for idx, offset in enumerate(occurrences):
        print(f"Occurrence {idx + 1} at 0x{offset:04X}:")
        print("-" * 70)

        # Show 20 bytes before and 10 bytes after
        start = max(0, offset - 20)
        end = min(TILE_DATA_OFFSET, offset + 12)

        context = data[start:end]

        # Print in chunks of 8 bytes for readability
        for i in range(0, len(context), 8):
            chunk_start = start + i
            chunk = context[i:i+8]
            hex_str = ' '.join(f'{b:02X}' for b in chunk)

            # Mark the 08 08 position
            marker = ''
            if chunk_start <= offset < chunk_start + 8:
                marker_pos = (offset - chunk_start) * 3
                marker = ' ' * marker_pos + '^^  ^^'

            print(f"  0x{chunk_start:04X}: {hex_str:<24} {marker}")

        # Try to identify structure
        print("\n  Attempting to parse structure:")

        # Pattern A: [??][offset_le16][width][height]
        if offset >= 3:
            flags = data[offset-3]
            offset_le16 = data[offset-2] | (data[offset-1] << 8)
            width = data[offset]
            height = data[offset+1]

            print(f"    Pattern A [flags][offset_le16][W][H]:")
            print(f"      flags=0x{flags:02X}, offset=0x{offset_le16:04X} ({offset_le16}), dims={width}x{height}")

        # Pattern B: [offset_le16][width][height]
        if offset >= 2:
            offset_le16 = data[offset-2] | (data[offset-1] << 8)
            width = data[offset]
            height = data[offset+1]

            print(f"    Pattern B [offset_le16][W][H]:")
            print(f"      offset=0x{offset_le16:04X} ({offset_le16}), dims={width}x{height}")

        # Pattern C: [offset_le24][width][height]
        if offset >= 3:
            offset_le24 = data[offset-3] | (data[offset-2] << 8) | (data[offset-1] << 16)
            width = data[offset]
            height = data[offset+1]

            print(f"    Pattern C [offset_le24][W][H]:")
            print(f"      offset=0x{offset_le24:06X} ({offset_le24}), dims={width}x{height}")

        # Check what comes after
        if offset + 6 < TILE_DATA_OFFSET:
            after = data[offset+2:offset+6]
            after_hex = ' '.join(f'{b:02X}' for b in after)
            print(f"    Bytes after dims: {after_hex}")

            # Check if next bytes could be another record
            if offset + 5 < TILE_DATA_OFFSET:
                next_width = data[offset+4]
                next_height = data[offset+5]
                if 2 <= next_width <= 20 and 2 <= next_height <= 20:
                    print(f"      Possible next record dims: {next_width}x{next_height} (in 4px units = {next_width*4}x{next_height*4})")

        print()

    print("=" * 70)


if __name__ == "__main__":
    analyze()
