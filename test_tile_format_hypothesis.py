"""Test hypothesis: MAZEDATA has offset table + descriptors like .PIC format.

Hypothesis:
- First section is an offset table (LE16 offsets)
- Each offset points to a descriptor
- Descriptor format: [flags?][width][height][tile_data_offset?][...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def test_hypothesis():
    """Test offset table hypothesis."""
    print("Testing Offset Table + Descriptor Hypothesis")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    # First, look for the start of descriptors
    # The first 2 bytes are 0x99 0x00 = 153
    # This could be the offset to where descriptors start

    first_offset = data[0] | (data[1] << 8)
    print(f"First word (LE16): 0x{first_offset:04X} ({first_offset})")
    print()

    # What's at offset 153?
    print(f"Data at offset {first_offset} (0x{first_offset:02X}):")
    desc_data = data[first_offset:first_offset + 32]
    hex_str = ' '.join(f'{b:02X}' for b in desc_data)
    print(f"  {hex_str}")
    print()

    # Alternative hypothesis: records start immediately
    # Looking at pattern: `99 00 6E 01 00 00 00 0E 57 30 01 08 08 33`
    # Could be:
    # Record 0: 99 00 6E 01 00 00 (6 bytes?)
    # Record 1: 00 0E 57 30 01 08 (6 bytes?)
    # Record 2: 08 33 96 01 08 04 (6 bytes?)

    # Let me look for a pattern by searching for known dimension values
    # We know some tiles are 32x32 (08 08 in 4-pixel units)

    print("Searching for records with 08 08 (32x32) dimensions:")
    print("-" * 70)

    # Try different record formats
    formats = [
        ("Format A: [offset_le16][width][height]", 4, 2, 3),
        ("Format B: [flags][offset_le16][width][height]", 5, 3, 4),
        ("Format C: [offset_le24][width][height]", 5, 3, 4),
        ("Format D: [flags][offset_le24][width][height]", 6, 4, 5),
        ("Format E: [offset_le16][flags][width][height]", 5, 3, 4),
    ]

    for format_name, record_size, width_offset, height_offset in formats:
        print(f"\n{format_name} ({record_size} bytes/record):")

        matches = 0
        for rec_idx in range(0, min(2000, TILE_DATA_OFFSET) // record_size):
            pos = rec_idx * record_size

            if pos + record_size >= TILE_DATA_OFFSET:
                break

            record = data[pos:pos + record_size]

            width = record[width_offset]
            height = record[height_offset]

            # Check if it's 08 08 (32x32)
            if width == 0x08 and height == 0x08:
                matches += 1

                if matches <= 5:
                    hex_str = ' '.join(f'{b:02X}' for b in record)

                    # Try to parse offset
                    if width_offset >= 2:
                        offset_le16 = record[width_offset-2] | (record[width_offset-1] << 8)
                        print(f"  Rec {rec_idx:3d} @ 0x{pos:04X}: {hex_str} | offset=0x{offset_le16:04X}, dims={width}x{height}")
                    else:
                        print(f"  Rec {rec_idx:3d} @ 0x{pos:04X}: {hex_str} | dims={width}x{height}")

        print(f"  Total 32x32 matches: {matches}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    test_hypothesis()
