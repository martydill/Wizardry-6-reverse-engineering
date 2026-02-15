"""Analyze MAZEDATA.EGA metadata before tile data.

Looking for tile dimension info, animation frames, or other metadata.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def analyze_metadata():
    """Analyze the metadata region before tile data."""
    print("Analyzing MAZEDATA.EGA Metadata Region")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    print(f"Total file size: {len(data):,} bytes")
    print(f"Tile data starts at: 0x{TILE_DATA_OFFSET:06X} ({TILE_DATA_OFFSET:,} bytes)")
    print(f"Metadata region: 0x000000 - 0x{TILE_DATA_OFFSET-1:06X} ({TILE_DATA_OFFSET:,} bytes)")
    print()

    metadata = data[:TILE_DATA_OFFSET]

    # First, look at the beginning
    print("First 256 bytes (hex):")
    print("-" * 70)
    for i in range(0, min(256, len(metadata)), 16):
        hex_str = ' '.join(f'{b:02X}' for b in metadata[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in metadata[i:i+16])
        print(f"{i:06X}: {hex_str:<48} {ascii_str}")
    print()

    # Look for patterns of small numbers that could be dimensions
    print("Looking for potential dimension/metadata structures...")
    print("-" * 70)

    # Check for repeating patterns (might indicate a table)
    for record_size in [4, 6, 8, 10, 12, 16, 20, 24, 32]:
        if TILE_DATA_OFFSET % record_size == 0:
            num_records = TILE_DATA_OFFSET // record_size
            print(f"\n{record_size}-byte records ({num_records} records):")

            # Show first 10 records
            for i in range(min(10, num_records)):
                offset = i * record_size
                record = metadata[offset:offset + record_size]

                hex_str = ' '.join(f'{b:02X}' for b in record)

                # Try to interpret as LE16 values
                if record_size >= 2:
                    values_le16 = []
                    for j in range(0, record_size - 1, 2):
                        val = record[j] | (record[j+1] << 8)
                        values_le16.append(val)

                    print(f"  [{i:3d}] 0x{offset:06X}: {hex_str:<48} | LE16: {values_le16}")
                else:
                    print(f"  [{i:3d}] 0x{offset:06X}: {hex_str}")

            if num_records > 10:
                print(f"  ... ({num_records - 10} more records)")

    print()

    # Look for specific byte values that could be dimensions (16-64 range)
    print("Scanning for potential dimension values (16-64 range)...")
    print("-" * 70)

    dimension_candidates = []
    for i in range(len(metadata) - 1):
        # Check LE16 values
        val = metadata[i] | (metadata[i+1] << 8)
        if 16 <= val <= 64:
            dimension_candidates.append((i, val))

    # Group by value
    from collections import Counter
    value_counts = Counter(val for _, val in dimension_candidates)

    print("\nMost common values in 16-64 range:")
    for val, count in value_counts.most_common(20):
        print(f"  {val:3d} (0x{val:02X}): {count:4d} occurrences")

    # Show some examples of value 32 (expected tile dimension)
    if 32 in value_counts:
        print(f"\nFirst 10 occurrences of value 32 (expected tile size):")
        occurrences = [offset for offset, val in dimension_candidates if val == 32]
        for offset in occurrences[:10]:
            # Show context
            context = metadata[max(0, offset-8):offset+10]
            hex_str = ' '.join(f'{b:02X}' for b in context)
            print(f"  0x{offset:06X}: ...{hex_str}...")

    print()

    # Look at the end of metadata region (might have a table there)
    print("Last 256 bytes before tile data:")
    print("-" * 70)
    start = max(0, TILE_DATA_OFFSET - 256)
    for i in range(start, TILE_DATA_OFFSET, 16):
        hex_str = ' '.join(f'{b:02X}' for b in metadata[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in metadata[i:i+16])
        print(f"{i:06X}: {hex_str:<48} {ascii_str}")

    print()

    # Check for potential animation info (sequences of similar values)
    print("Looking for potential animation frame sequences...")
    print("-" * 70)

    # Look for patterns like: frame_count, frame_0, frame_1, frame_2...
    for i in range(0, len(metadata) - 8, 2):
        # Try reading as LE16 values
        vals = []
        for j in range(4):
            if i + j*2 + 1 < len(metadata):
                val = metadata[i + j*2] | (metadata[i + j*2 + 1] << 8)
                vals.append(val)

        # Check if first value could be a count (2-8) and others are sequential or similar
        if len(vals) >= 4:
            if 2 <= vals[0] <= 8:
                # Check if following values are in reasonable range (0-200 for tile indices)
                if all(0 <= v <= 200 for v in vals[1:]):
                    # Could be interesting
                    if i % 100 == 0:  # Sample every 100 bytes
                        print(f"  0x{i:06X}: count={vals[0]}, tiles={vals[1:]}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    analyze_metadata()
