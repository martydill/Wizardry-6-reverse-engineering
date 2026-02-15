"""Decode MAZEDATA.EGA tile descriptor table.

Attempting to find the exact record format.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def decode_table():
    """Decode tile descriptor table."""
    print("Decoding MAZEDATA.EGA Tile Descriptor Table")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]

    # Looking at the 08 08 patterns, let's examine the full context
    # The pattern seems to be: ?? ?? ?? ?? 08 08 ?? ?? ?? ??
    # This suggests records might be longer than 6 bytes

    print("Analyzing 08 08 (32x32) pattern contexts:")
    print("-" * 70)

    occurrences_32x32 = []

    for i in range(len(metadata) - 1):
        if metadata[i] == 0x08 and metadata[i+1] == 0x08:
            occurrences_32x32.append(i)

    for i in occurrences_32x32[:10]:
        # Show wider context
        start = max(0, i - 8)
        end = min(len(metadata), i + 10)
        context = metadata[start:end]

        hex_str = ' '.join(f'{b:02X}' for b in context)
        print(f"0x{i:04X}: {hex_str}")

        # Try to interpret bytes before 08 08
        if i >= 3:
            # Try 3-byte LE offset
            offset_le24 = metadata[i-3] | (metadata[i-2] << 8) | (metadata[i-1] << 16)
            offset_le16 = metadata[i-2] | (metadata[i-1] << 8)

            print(f"        Possible offsets: LE16=0x{offset_le16:04X} ({offset_le16}), LE24=0x{offset_le24:06X} ({offset_le24})")

        # Bytes after 08 08
        if i + 5 < len(metadata):
            after = metadata[i+2:i+6]
            hex_after = ' '.join(f'{b:02X}' for b in after)
            print(f"        After dims: {hex_after}")

        print()

    # Now let's try to find a pattern
    # Hypothesis: record format is [offset_le24][width][height][...flags...]
    # or [offset_le16][width][height][...flags...]

    print("\nAttempting to parse as fixed-length records...")
    print("-" * 70)

    # Let's try assuming records are separated by looking for dimension patterns
    # Common dimensions (in 4-pixel units): 08 (32px), 0C (48px), 10 (64px), etc.

    # Try parsing variable-length records by looking for start markers
    # Pattern observation: many records start after 00 bytes or have distinctive starts

    # Let me try a different approach: calculate tile count from tile data size
    tile_data_size = len(data) - TILE_DATA_OFFSET
    bytes_per_32x32_tile = 512  # 32*32 / 2 (4-bit pixels)

    print(f"Tile data region size: {tile_data_size:,} bytes")
    print(f"If all 32x32: ~{tile_data_size // bytes_per_32x32_tile} tiles")
    print()

    # Let's examine potential record boundaries by looking for repeating patterns
    print("Looking for potential record structure by examining value distributions...")
    print("-" * 70)

    # Check if there's a pattern in byte positions
    # For example, if records are N bytes, then bytes at positions 0, N, 2N, 3N should have similar characteristics

    for record_size in [5, 6, 7, 8, 10, 12]:
        print(f"\nTesting {record_size}-byte records:")

        # Count how many records would have reasonable width/height values
        # assuming dims are at specific offsets within the record

        for dim_offset in range(record_size - 1):
            reasonable_count = 0
            total_records = 0

            for rec_start in range(0, len(metadata) - record_size, record_size):
                width_pos = rec_start + dim_offset
                height_pos = rec_start + dim_offset + 1

                if height_pos >= len(metadata):
                    break

                width = metadata[width_pos]
                height = metadata[height_pos]

                total_records += 1

                # Check if dimensions are reasonable (4-20 in 4-pixel units = 16-80 pixels)
                if 2 <= width <= 20 and 2 <= height <= 20:
                    reasonable_count += 1

            if total_records > 0:
                ratio = reasonable_count / total_records
                if ratio > 0.3:  # If >30% look reasonable
                    print(f"  Dims at offset {dim_offset}: {reasonable_count}/{total_records} ({ratio*100:.1f}%) reasonable")

    print()
    print("=" * 70)


if __name__ == "__main__":
    decode_table()
