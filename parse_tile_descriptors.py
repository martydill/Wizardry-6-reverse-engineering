"""Parse MAZEDATA.EGA tile descriptor table.

The metadata region appears to contain tile descriptors with dimensions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def parse_descriptors():
    """Parse tile descriptor table."""
    print("Parsing MAZEDATA.EGA Tile Descriptors")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    # The first two bytes look like they could be an offset
    first_offset = data[0] | (data[1] << 8)
    print(f"First word: 0x{first_offset:04X} ({first_offset})")
    print()

    # Try to parse as a table of records
    # Looking at the pattern, it seems like variable-length records
    # Let me look at the first few bytes more carefully

    print("First 128 bytes with byte offsets:")
    print("-" * 70)
    for i in range(0, 128):
        if i % 16 == 0:
            print(f"\n{i:04X}: ", end="")
        print(f"{data[i]:02X} ", end="")
    print()
    print()

    # Try parsing as: offset(LE16), then descriptor data
    # The first offset is 153 (0x99), which is close to where we might expect data

    print("Attempting to parse as offset table...")
    print("-" * 70)

    # Parse initial offset to find where descriptors start
    descriptor_start = data[0] | (data[1] << 8)
    print(f"Descriptor data starts at: 0x{descriptor_start:04X} ({descriptor_start})")
    print()

    # The area between 0 and descriptor_start is likely an index/offset table
    # Let's count how many LE16 offsets we can find
    offset_table_size = descriptor_start
    num_offsets = offset_table_size // 2

    print(f"Offset table region: 0x0000 - 0x{descriptor_start-1:04X}")
    print(f"Potential number of tiles: {num_offsets}")
    print()

    # Parse offset table
    offsets = []
    for i in range(0, descriptor_start, 2):
        offset = data[i] | (data[i+1] << 8)
        offsets.append((i // 2, offset))

    # Show first 20 offsets
    print("First 20 tile offsets:")
    for idx, offset in offsets[:20]:
        print(f"  Tile {idx:3d}: 0x{offset:04X} ({offset:5d})")
    print()

    # Now try to parse descriptors
    print("Parsing tile descriptors...")
    print("-" * 70)

    tiles = []

    for tile_idx in range(len(offsets)):
        tile_num, desc_offset = offsets[tile_idx]

        # Get next offset to know descriptor size
        if tile_idx + 1 < len(offsets):
            next_offset = offsets[tile_idx + 1][1]
        else:
            # Last descriptor goes to start of tile data
            next_offset = TILE_DATA_OFFSET

        desc_size = next_offset - desc_offset

        if desc_size <= 0 or desc_size > 100:
            continue

        desc_data = data[desc_offset:next_offset]

        # Try to parse descriptor
        # Common pattern seems to be:
        # - Some flags/ID bytes
        # - Width/height
        # - Offset into tile data?

        if len(desc_data) >= 4:
            # Try different interpretations
            byte0 = desc_data[0]
            byte1 = desc_data[1]
            byte2 = desc_data[2]
            byte3 = desc_data[3]

            # Check if bytes 2-3 could be dimensions
            width_height_1 = (byte2, byte3)

            # Or bytes 0-1
            width_height_2 = (byte0, byte1)

            # Or bytes 1-2
            width_height_3 = (byte1, byte2)

            # Show first 20 descriptors
            if tile_idx < 20:
                hex_str = ' '.join(f'{b:02X}' for b in desc_data)
                print(f"Tile {tile_num:3d} @ 0x{desc_offset:04X} ({desc_size:2d} bytes): {hex_str}")
                print(f"         Possible dims: ({byte0},{byte1}) ({byte1},{byte2}) ({byte2},{byte3})")

                # Try to decode as multi-byte values
                if len(desc_data) >= 6:
                    val0 = desc_data[0] | (desc_data[1] << 8)
                    val1 = desc_data[2] | (desc_data[3] << 8)
                    val2 = desc_data[4] | (desc_data[5] << 8)
                    print(f"         LE16 values: {val0}, {val1}, {val2}")
                print()

    print()
    print("=" * 70)


if __name__ == "__main__":
    parse_descriptors()
