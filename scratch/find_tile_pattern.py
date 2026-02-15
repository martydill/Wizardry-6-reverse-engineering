"""Find the actual tile descriptor pattern by analyzing known good tiles.

We know tile at offset 0x0C07 with dims 32x32 (08 08) is correct.
Let's find all similar patterns and figure out the structure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def find_pattern():
    """Find tile descriptor pattern."""
    print("Finding Tile Descriptor Pattern")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]

    # Find all occurrences of common dimension patterns
    # 08 08 = 32x32
    # 08 04 = 32x16
    # 04 08 = 16x32
    # 0C 0C = 48x48

    patterns = [
        (0x08, 0x08, "32x32"),
        (0x08, 0x04, "32x16"),
        (0x04, 0x08, "16x32"),
        (0x0C, 0x0C, "48x48"),
        (0x08, 0x0C, "32x48"),
        (0x0C, 0x08, "48x32"),
    ]

    for width_byte, height_byte, dims_str in patterns:
        print(f"\nSearching for {dims_str} ({width_byte:02X} {height_byte:02X}) patterns:")
        print("-" * 70)

        occurrences = []

        for i in range(len(metadata) - 1):
            if metadata[i] == width_byte and metadata[i+1] == height_byte:
                occurrences.append(i)

        print(f"Found {len(occurrences)} occurrences")

        for occ_idx, pos in enumerate(occurrences[:10]):
            # Show context (10 bytes before, 5 bytes after)
            start = max(0, pos - 10)
            end = min(len(metadata), pos + 5)
            context = metadata[start:end]

            hex_str = ' '.join(f'{b:02X}' for b in context)
            print(f"\n  Occurrence {occ_idx + 1} at 0x{pos:04X}:")
            print(f"    Context: {hex_str}")

            # Try to extract offset (should be 2 bytes before dims)
            if pos >= 2:
                offset_le16 = metadata[pos-2] | (metadata[pos-1] << 8)
                print(f"    LE16 at pos-2: 0x{offset_le16:04X} ({offset_le16})")

                # Check if offset is valid (points to tile data region)
                width_px = width_byte * 4
                height_px = height_byte * 4
                required_bytes = (width_px * height_px) // 2

                tile_data_region = data[TILE_DATA_OFFSET:]

                if offset_le16 < len(tile_data_region) and offset_le16 + required_bytes <= len(tile_data_region):
                    print(f"    [OK] VALID tile offset! Would decode {width_px}x{height_px} tile from offset 0x{offset_le16:04X}")

                    # Check byte before offset (might be flags/count)
                    if pos >= 3:
                        possible_flags = metadata[pos-3]
                        print(f"    Possible flags/count byte: 0x{possible_flags:02X} ({possible_flags})")
                else:
                    print(f"    [X] Invalid offset (out of bounds)")

    print()
    print("=" * 70)


if __name__ == "__main__":
    find_pattern()
