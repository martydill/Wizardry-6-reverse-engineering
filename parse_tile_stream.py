"""Parse MAZEDATA.EGA as a stream of tile descriptors.

Looking for patterns like: offset, width, height, flags...
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def parse_stream():
    """Parse as stream of variable-length records."""
    print("Parsing MAZEDATA.EGA Tile Descriptor Stream")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]

    # Looking at the patterns, I notice byte pairs like:
    # 08 04, 08 08, 0C 02, 08 03, 08 02, etc.
    # These could be dimensions in 4-pixel units:
    # 08 04 = 8*4 x 4*4 = 32 x 16
    # 08 08 = 8*4 x 8*4 = 32 x 32
    # 0C 02 = 12*4 x 2*4 = 48 x 8
    # etc.

    # Let's scan for patterns that look like dimension pairs
    print("Scanning for dimension-like byte pairs (multiples of 4 expected)...")
    print("-" * 70)

    # Try to identify record structure
    # Common pattern seems to be: XX XX YY ZZ WW HH ...
    # where WW HH might be width/height

    # Let's try parsing assuming 6-byte records initially
    print("\nTrying 6-byte record interpretation:")
    print("-" * 70)

    for i in range(0, min(240, len(metadata)), 6):
        if i >= len(metadata) - 5:
            break

        rec = metadata[i:i+6]

        # Try different interpretations
        offset_le24 = rec[0] | (rec[1] << 8) | (rec[2] << 16)
        offset_le16 = rec[0] | (rec[1] << 8)

        width1, height1 = rec[2], rec[3]
        width2, height2 = rec[3], rec[4]
        width3, height3 = rec[4], rec[5]

        hex_str = ' '.join(f'{b:02X}' for b in rec)

        # Check if any width/height pair looks reasonable (4-64 range, multiples of 4)
        candidates = []

        # Try as pixel counts
        if 4 <= width1 <= 64 and 4 <= height1 <= 64:
            candidates.append(f"({width1}x{height1})")

        if 4 <= width2 <= 64 and 4 <= height2 <= 64:
            candidates.append(f"({width2}x{height2})")

        if 4 <= width3 <= 64 and 4 <= height3 <= 64:
            candidates.append(f"({width3}x{height3})")

        # Try as 4-pixel unit counts (multiply by 4)
        w1_px, h1_px = width1 * 4, height1 * 4
        w2_px, h2_px = width2 * 4, height2 * 4

        if 16 <= w1_px <= 256 and 16 <= h1_px <= 256:
            candidates.append(f"4x: ({w1_px}x{h1_px})")

        if 16 <= w2_px <= 256 and 16 <= h2_px <= 256:
            candidates.append(f"4x: ({w2_px}x{h2_px})")

        tile_idx = i // 6

        if candidates:
            print(f"Tile {tile_idx:3d} @ 0x{i:04X}: {hex_str} | {', '.join(candidates)}")

    print()

    # Try looking for specific patterns
    print("\nLooking for 0x08 0x08 pattern (32x32 tiles):")
    print("-" * 70)

    for i in range(len(metadata) - 1):
        if metadata[i] == 0x08 and metadata[i+1] == 0x08:
            # Show context
            start = max(0, i - 4)
            end = min(len(metadata), i + 6)
            context = metadata[start:end]
            hex_str = ' '.join(f'{b:02X}' for b in context)

            # Highlight the 08 08
            marker = ' ' * (3 * (i - start)) + '^^  ^^'

            print(f"  0x{i:04X}: {hex_str}")
            print(f"         {marker}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    parse_stream()
