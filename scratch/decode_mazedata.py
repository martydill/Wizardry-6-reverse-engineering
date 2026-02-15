"""Decode MAZEDATA.EGA - wall textures stored as indexed 8x8 tiles."""

import struct
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def decode_mazedata():
    """Decode MAZEDATA.EGA structure."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print("MAZEDATA.EGA Decoder")
    print("=" * 70)
    print()

    # Parse header
    count = struct.unpack_from("<H", data, 0)[0]
    print(f"Texture count: {count}")
    print()

    # Parse index (5-byte entries: 2 bytes flags/params + 3 bytes offset)
    ENTRY_SIZE = 5
    HEADER_SIZE = 2
    INDEX_SIZE = count * ENTRY_SIZE
    DATA_START = HEADER_SIZE + INDEX_SIZE

    print(f"Header size: {HEADER_SIZE} bytes")
    print(f"Index size: {INDEX_SIZE} bytes ({count} entries x {ENTRY_SIZE} bytes)")
    print(f"Data starts at: 0x{DATA_START:04X} ({DATA_START} bytes)")
    print()

    # Parse all entries
    entries = []
    offset = HEADER_SIZE
    for i in range(count):
        b0, b1 = struct.unpack_from("<BB", data, offset)
        ptr = struct.unpack_from("<I", data + b"\x00", offset + 2)[0] & 0xFFFFFF
        entries.append((b0, b1, ptr))
        offset += ENTRY_SIZE

    # Show first and last few entries
    print("Index entries (5-byte format: [b0 b1] + 3-byte offset):")
    for i, (b0, b1, ptr) in enumerate(entries):
        if i < 20 or i >= count - 5:
            print(f"  {i:3d}: [{b0:02X} {b1:02X}] offset=0x{ptr:06X} ({ptr})")
        elif i == 20:
            print("  ...")

    print()

    # Analyze offsets
    offsets = [e[2] for e in entries]
    print(f"Offset range: 0x{min(offsets):06X} - 0x{max(offsets):06X}")
    print()

    # Check if offsets are absolute or relative
    if min(offsets) < DATA_START:
        print("Offsets appear to be RELATIVE to data start")
        base = DATA_START
    else:
        print("Offsets appear to be ABSOLUTE")
        base = 0

    print()

    # Calculate texture sizes
    print("Calculating texture sizes from offsets:")
    for i in range(len(entries)):
        b0, b1, ptr = entries[i]
        abs_offset = base + ptr

        # Get next offset to calculate size
        if i + 1 < len(entries):
            next_ptr = entries[i + 1][2]
            next_abs_offset = base + next_ptr
            size = next_abs_offset - abs_offset
        else:
            size = len(data) - abs_offset

        # 8x8 tile in planar format = 64 pixels / 8 * 4 planes = 32 bytes
        tiles_count = size // 32
        remainder = size % 32

        if i < 20 or i >= len(entries) - 5:
            if tiles_count > 0:
                print(f"  {i:3d}: size={size:5d} bytes = {tiles_count} tiles (8x8) + {remainder} remainder")
            else:
                print(f"  {i:3d}: size={size:5d} bytes (less than 1 tile)")
        elif i == 20:
            print("  ...")

    print()
    print("=" * 70)

    # Try to decode first few textures
    print("\nDecoding first few textures...")
    print()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    output_dir = Path("output/mazedata_textures")
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(min(10, len(entries))):
        b0, b1, ptr = entries[i]
        abs_offset = base + ptr

        # Calculate size
        if i + 1 < len(entries):
            next_ptr = entries[i + 1][2]
            next_abs_offset = base + next_ptr
            size = next_abs_offset - abs_offset
        else:
            size = len(data) - abs_offset

        tiles_count = size // 32

        if tiles_count == 0:
            print(f"Texture {i}: skipping (too small: {size} bytes)")
            continue

        # Extract texture data
        texture_data = data[abs_offset:abs_offset + size]

        # Decode as 8x8 tiles
        # If it's multiple tiles, they might be arranged in a grid
        # Let's try a square arrangement first
        import math
        side = int(math.sqrt(tiles_count))
        if side * side == tiles_count:
            # Square arrangement
            width = side * 8
            height = side * 8
        else:
            # Try rectangular
            # Common arrangements: 1x1, 2x1, 2x2, 3x2, 4x4, etc.
            if tiles_count == 1:
                width, height = 8, 8
            elif tiles_count == 2:
                width, height = 16, 8
            elif tiles_count <= 4:
                width, height = 16, 16
            elif tiles_count <= 6:
                width, height = 24, 16
            elif tiles_count <= 8:
                width, height = 32, 16
            elif tiles_count <= 16:
                width, height = 32, 32
            else:
                # Just go with width=8*tiles
                width = tiles_count * 8
                height = 8

        try:
            # Try planar decoding
            sprite = decoder.decode_planar(texture_data, width, height)

            # Save as PNG
            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = output_dir / f"texture_{i:03d}_b0{b0:02X}_b1{b1:02X}_{width}x{height}.png"
            img.save(output_path)
            print(f"Texture {i:3d}: {tiles_count:2d} tiles -> {width:3d}x{height:3d} saved to {output_path.name}")

        except Exception as e:
            print(f"Texture {i:3d}: ERROR - {e}")

if __name__ == "__main__":
    decode_mazedata()
