"""Deep dive into MAZEDATA.EGA structure - it appears to be an index + texture tiles."""

import struct
from pathlib import Path

def analyze_index():
    """Analyze what appears to be an index/directory at the start."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print("MAZEDATA.EGA Structure Analysis")
    print("=" * 70)
    print()

    # First 2 bytes might be a count
    count = struct.unpack_from("<H", data, 0)[0]
    print(f"First word (LE16): {count} (0x{count:04X})")
    print(f"Could be entry count if this is an index table")
    print()

    # Let's try to parse entries
    # Looking at the hex, pattern seems to be repeating
    # Let me try different entry sizes

    print("Trying to parse as index entries:")
    print()

    # Try 4-byte entries: maybe 1 byte flags + 3 byte offset?
    print("Attempting 4-byte entries (byte + 3-byte offset):")
    offset = 2  # Skip count word
    for i in range(min(20, count)):
        if offset + 4 > len(data):
            break
        flags = data[offset]
        # Try 3-byte little-endian offset
        ptr = struct.unpack_from("<I", data + b"\x00", offset + 1)[0] & 0xFFFFFF
        print(f"  Entry {i:3d}: flags=0x{flags:02X}, offset=0x{ptr:06X} ({ptr})")
        offset += 4

    print()

    # Try 5-byte entries
    print("Attempting 5-byte entries:")
    offset = 2
    for i in range(min(20, count)):
        if offset + 5 > len(data):
            break
        b0, b1 = struct.unpack_from("<BB", data, offset)
        ptr = struct.unpack_from("<I", data + b"\x00", offset + 2)[0] & 0xFFFFFF
        print(f"  Entry {i:3d}: b0=0x{b0:02X}, b1=0x{b1:02X}, offset=0x{ptr:06X} ({ptr})")
        offset += 5

    print()

    # Try 6-byte entries
    print("Attempting 6-byte entries:")
    offset = 2
    for i in range(min(20, count)):
        if offset + 6 > len(data):
            break
        b0, b1, b2 = struct.unpack_from("<BBB", data, offset)
        ptr = struct.unpack_from("<I", data + b"\x00", offset + 3)[0] & 0xFFFFFF
        print(f"  Entry {i:3d}: [{b0:02X} {b1:02X} {b2:02X}] offset=0x{ptr:06X} ({ptr})")
        offset += 6

    print()

    # Let's check where the actual texture data might start
    # If first word is count, and entries are N bytes, then:
    for entry_size in range(4, 10):
        data_start = 2 + count * entry_size
        if data_start < len(data):
            print(f"Entry size {entry_size}: data starts at 0x{data_start:04X} ({data_start})")
            # Check if it aligns with tile sizes
            remaining = len(data) - data_start
            for tile_size in [32, 128, 512]:
                tile_count = remaining // tile_size
                remainder = remaining % tile_size
                if remainder == 0:
                    print(f"  -> {tile_count} tiles of {tile_size} bytes (EXACT FIT!)")
                elif remainder < 10:
                    print(f"  -> {tile_count} tiles of {tile_size} bytes + {remainder} remainder")

    print()
    print("=" * 70)

    # Let's look at what seems most promising
    # If count=153 and entry_size=6, data starts at 2 + 153*6 = 920
    print("\nMost likely structure:")
    count = 153
    entry_size = 6
    header_size = 2 + count * entry_size

    print(f"Header: 2 bytes (count={count})")
    print(f"Index: {count} entries × {entry_size} bytes = {count * entry_size} bytes")
    print(f"Data starts at: 0x{header_size:04X} ({header_size})")

    data_size = len(data) - header_size
    print(f"Data size: {data_size} bytes")

    # Check tile fits
    for tile_size, tile_name in [(32, "8x8"), (128, "16x16"), (512, "32x32")]:
        tile_count = data_size // tile_size
        remainder = data_size % tile_size
        print(f"  {tile_name} tiles: {tile_count} tiles, {remainder} bytes remainder")

    print()

    # Parse all entries with 6-byte structure
    print("All index entries (6-byte format):")
    offset = 2
    entries = []
    for i in range(count):
        if offset + 6 > len(data):
            break
        b0, b1, b2 = struct.unpack_from("<BBB", data, offset)
        ptr = struct.unpack_from("<I", data + b"\x00", offset + 3)[0] & 0xFFFFFF
        entries.append((b0, b1, b2, ptr))
        if i < 30 or i >= count - 5:
            print(f"  Entry {i:3d}: [{b0:02X} {b1:02X} {b2:02X}] -> offset 0x{ptr:06X}")
        elif i == 30:
            print("  ...")
        offset += 6

    print()

    # Analyze offset ranges
    if entries:
        offsets = [e[3] for e in entries]
        print(f"Offset range: 0x{min(offsets):06X} - 0x{max(offsets):06X}")
        print(f"First offset: 0x{offsets[0]:06X} ({offsets[0]})")
        print(f"Last offset: 0x{offsets[-1]:06X} ({offsets[-1]})")

        # Check if offsets point into the data region
        print()
        print("Checking if offsets are absolute or relative to data start...")
        abs_min = min(offsets)
        abs_max = max(offsets)

        if abs_min >= header_size:
            print(f"  Offsets appear to be ABSOLUTE (min={abs_min} >= header_size={header_size})")
        else:
            print(f"  Offsets appear to be RELATIVE to data start")

        # Try to extract first texture
        print()
        print("Attempting to extract first texture...")
        first_offset = offsets[0]

        # Try as absolute offset
        if first_offset < len(data):
            print(f"  At absolute offset 0x{first_offset:06X}:")
            chunk = data[first_offset:first_offset+64]
            print(f"    First 64 bytes: {' '.join(f'{b:02X}' for b in chunk[:32])}")

        # Try as relative to header_size
        rel_offset = header_size + first_offset
        if rel_offset < len(data):
            print(f"  At relative offset 0x{rel_offset:06X} (header_size + offset):")
            chunk = data[rel_offset:rel_offset+64]
            print(f"    First 64 bytes: {' '.join(f'{b:02X}' for b in chunk[:32])}")

if __name__ == "__main__":
    analyze_index()
