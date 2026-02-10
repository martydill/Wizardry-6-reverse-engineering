"""Try different interpretations of MAZEDATA.EGA index structure."""

import struct
from pathlib import Path

def try_format_1():
    """Try: 2-byte count, then 4-byte entries (1 byte param + 3 byte offset)."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    count = struct.unpack_from("<H", data, 0)[0]
    print(f"\nFormat 1: Count={count}, 4-byte entries (byte + 3-byte LE offset)")
    print("=" * 70)

    ENTRY_SIZE = 4
    HEADER_SIZE = 2
    DATA_START = HEADER_SIZE + count * ENTRY_SIZE

    entries = []
    offset = HEADER_SIZE
    for i in range(count):
        param = data[offset]
        # 3-byte little-endian offset
        ptr = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
        entries.append((param, ptr))
        offset += ENTRY_SIZE

    print(f"Data starts at: 0x{DATA_START:04X} ({DATA_START})")
    print()

    # Show entries
    for i, (param, ptr) in enumerate(entries[:15]):
        abs_ptr = DATA_START + ptr
        print(f"  {i:3d}: param=0x{param:02X}, offset=0x{ptr:06X}, abs=0x{abs_ptr:06X}")

    # Check sizes
    print("\nTexture sizes:")
    for i in range(min(15, len(entries))):
        ptr1 = entries[i][1]
        if i + 1 < len(entries):
            ptr2 = entries[i + 1][1]
            size = ptr2 - ptr1
        else:
            size = len(data) - DATA_START - ptr1

        tiles = size // 32
        print(f"  {i:3d}: size={size:5d} bytes = {tiles} tiles")


def try_format_2():
    """Try: 2-byte count, then 5-byte entries (2 bytes params + 3 byte offset)."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    count = struct.unpack_from("<H", data, 0)[0]
    print(f"\nFormat 2: Count={count}, 5-byte entries (word + 3-byte LE offset)")
    print("=" * 70)

    ENTRY_SIZE = 5
    HEADER_SIZE = 2
    DATA_START = HEADER_SIZE + count * ENTRY_SIZE

    entries = []
    offset = HEADER_SIZE
    for i in range(count):
        params = struct.unpack_from("<H", data, offset)[0]
        # 3-byte little-endian offset
        ptr = data[offset + 2] | (data[offset + 3] << 8) | (data[offset + 4] << 16)
        entries.append((params, ptr))
        offset += ENTRY_SIZE

    print(f"Data starts at: 0x{DATA_START:04X} ({DATA_START})")
    print()

    # Show entries
    for i, (params, ptr) in enumerate(entries[:15]):
        abs_ptr = DATA_START + ptr
        print(f"  {i:3d}: params=0x{params:04X}, offset=0x{ptr:06X}, abs=0x{abs_ptr:06X}")

    # Check sizes
    print("\nTexture sizes:")
    for i in range(min(15, len(entries))):
        ptr1 = entries[i][1]
        if i + 1 < len(entries):
            ptr2 = entries[i + 1][1]
            size = ptr2 - ptr1
        else:
            size = len(data) - DATA_START - ptr1

        tiles = size // 32
        print(f"  {i:3d}: size={size:5d} bytes = {tiles} tiles")


def try_format_3():
    """Try: What if there's NO index, just sequential tiles?"""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print(f"\nFormat 3: No index, just sequential 8x8 tiles from start")
    print("=" * 70)

    # Skip first 2 bytes (might be palette or something)
    DATA_START = 2
    data_region = data[DATA_START:]

    tiles_count = len(data_region) // 32
    print(f"Total tiles: {tiles_count} (8x8 planar)")
    print(f"Remaining bytes: {len(data_region) % 32}")


def try_format_4():
    """Try: 1-byte count, then 5-byte entries."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    count = data[0]
    print(f"\nFormat 4: Count={count}, 5-byte entries (word + 3-byte LE offset)")
    print("=" * 70)

    ENTRY_SIZE = 5
    HEADER_SIZE = 1
    DATA_START = HEADER_SIZE + count * ENTRY_SIZE

    if count > 200:
        print(f"Count seems too high: {count}, probably not this format")
        return

    entries = []
    offset = HEADER_SIZE
    for i in range(count):
        params = struct.unpack_from("<H", data, offset)[0]
        ptr = data[offset + 2] | (data[offset + 3] << 8) | (data[offset + 4] << 16)
        entries.append((params, ptr))
        offset += ENTRY_SIZE

    print(f"Data starts at: 0x{DATA_START:04X} ({DATA_START})")
    print()

    # Show entries
    for i, (params, ptr) in enumerate(entries[:15]):
        abs_ptr = DATA_START + ptr
        print(f"  {i:3d}: params=0x{params:04X}, offset=0x{ptr:06X}, abs=0x{abs_ptr:06X}")


if __name__ == "__main__":
    try_format_1()
    try_format_2()
    try_format_3()
    try_format_4()
