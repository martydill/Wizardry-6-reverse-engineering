"""Re-analyze MAZEDATA.EGA metadata structure.

If most tiles don't look right, maybe it's not simple 4-byte packed records.
Let's look for an offset table or other structure.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def reanalyze():
    """Re-analyze metadata structure."""
    print("Re-analyzing MAZEDATA.EGA Metadata Structure")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]

    # The one tile that looks correct was at offset 0x0C07 with dims 32x32
    # That descriptor was at metadata offset 0x00ED (occurrence 4)
    # Let's look at that specific location

    print("Analyzing the CORRECT tile descriptor (offset 0x0C07, 32x32):")
    print("-" * 70)

    # We found it at metadata position 0x00ED (where we saw "0C 07 0C 08 08")
    # Wait, that's "0C 07 0C 08 08" - but we interpreted it as:
    # - Byte before: 0C (12)
    # - Offset: 0x07 0C = 0x0C07
    # - Dims: 08 08

    # Let me look at all the 08 08 occurrences we found
    correct_offset = 0x00ED  # Metadata offset where we found 08 08 for the good tile

    print(f"Correct descriptor at metadata offset 0x{correct_offset:04X}:")
    context = metadata[correct_offset - 10:correct_offset + 10]
    hex_str = ' '.join(f'{b:02X}' for b in context)
    print(f"  {hex_str}")
    print()

    # Let's look at the pattern around it
    print("Looking at pattern around correct descriptor:")
    for i in range(correct_offset - 20, correct_offset + 20):
        if i < 0 or i >= len(metadata):
            continue

        byte_val = metadata[i]
        marker = " <-- 08 08 starts here" if i == correct_offset else ""

        # Try to see if this could be an offset
        if i + 1 < len(metadata):
            as_le16 = metadata[i] | (metadata[i+1] << 8)
            # Check if it's a reasonable offset
            if 0 <= as_le16 < len(data) - TILE_DATA_OFFSET:
                print(f"  0x{i:04X}: {byte_val:02X} (LE16=0x{as_le16:04X}){marker}")
            else:
                print(f"  0x{i:04X}: {byte_val:02X}{marker}")
        else:
            print(f"  0x{i:04X}: {byte_val:02X}{marker}")

    print()

    # Let's check: maybe the metadata starts with an offset table
    # pointing to descriptors elsewhere?
    print("Checking if first bytes are an offset table:")
    print("-" * 70)

    # Read first 20 LE16 values
    for i in range(0, 40, 2):
        offset = metadata[i] | (metadata[i+1] << 8)
        print(f"  Word {i//2:2d} @ 0x{i:04X}: 0x{offset:04X} ({offset})")

        # Check if this offset points to something interesting
        if 0 < offset < TILE_DATA_OFFSET:
            # It's pointing within metadata
            target = metadata[offset:offset + 10]
            target_hex = ' '.join(f'{b:02X}' for b in target)
            print(f"           -> Points to: {target_hex}")

    print()

    # Alternative hypothesis: maybe there are NULL-separated records?
    print("Looking for NULL-separated records:")
    print("-" * 70)

    # Find sequences of non-zero bytes separated by zeros
    in_record = False
    record_start = 0
    records = []

    for i in range(len(metadata)):
        if metadata[i] != 0:
            if not in_record:
                record_start = i
                in_record = True
        else:
            if in_record:
                record_len = i - record_start
                if record_len >= 4:  # At least 4 bytes
                    records.append((record_start, record_len))
                in_record = False

    print(f"Found {len(records)} non-zero sequences of 4+ bytes")
    print("\nFirst 20 sequences:")
    for idx, (start, length) in enumerate(records[:20]):
        seq = metadata[start:start + min(length, 16)]
        hex_str = ' '.join(f'{b:02X}' for b in seq)
        if length > 16:
            hex_str += f" ... ({length} bytes total)"
        print(f"  [{idx:3d}] @ 0x{start:04X} ({length:3d} bytes): {hex_str}")

    print()
    print("=" * 70)


if __name__ == "__main__":
    reanalyze()
