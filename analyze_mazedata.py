"""Analyze MAZEDATA.EGA file structure to understand wall texture storage."""

import struct
from pathlib import Path

def hex_dump(data: bytes, offset: int = 0, length: int = 256) -> None:
    """Print a hex dump of data."""
    for i in range(0, min(len(data), length), 16):
        hex_part = " ".join(f"{b:02x}" for b in data[i:i+16])
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in data[i:i+16])
        print(f"{offset+i:08x}  {hex_part:<48}  {ascii_part}")

def analyze_mazedata():
    """Analyze the MAZEDATA.EGA file."""
    path = Path("gamedata/MAZEDATA.EGA")

    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    file_size = len(data)

    print(f"MAZEDATA.EGA Analysis")
    print(f"=" * 60)
    print(f"File size: {file_size} bytes (0x{file_size:X})")
    print()

    # Show first 512 bytes
    print("First 512 bytes:")
    hex_dump(data, 0, 512)
    print()

    # Try to detect structure
    # Full-screen EGA image is 320x200 = 64,000 pixels
    # In planar format: 64,000 / 8 bits = 8,000 bytes per plane
    # 4 planes = 32,000 bytes for full screen

    fullscreen_size = 32000
    print(f"Full screen EGA size: {fullscreen_size} bytes")
    print(f"File contains: {file_size / fullscreen_size:.2f} full screens")
    print()

    # Check if it's exactly 3 full screens (TITLEPAG, DRAGONSC, GRAVEYRD are 32768 = 32KB)
    # But MAZEDATA is 102,303 bytes

    # Let's check for patterns
    print("Checking for potential texture tile sizes:")
    print()

    # Wall textures might be stored as smaller tiles
    # Common tile sizes: 8x8, 16x16, 32x32, 64x64

    # For planar 4-bit format:
    # - 8x8 tile = 64 pixels = 64/8 * 4 planes = 32 bytes
    # - 16x16 tile = 256 pixels = 256/8 * 4 planes = 128 bytes
    # - 32x32 tile = 1024 pixels = 1024/8 * 4 planes = 512 bytes
    # - 64x64 tile = 4096 pixels = 4096/8 * 4 planes = 2048 bytes

    tile_sizes = {
        "8x8": 32,
        "16x16": 128,
        "32x32": 512,
        "64x64": 2048,
    }

    for name, size in tile_sizes.items():
        count = file_size // size
        remainder = file_size % size
        print(f"  {name} tiles ({size} bytes): {count} tiles, {remainder} bytes remainder")

    print()

    # Check first few bytes as potential header
    print("First 32 bytes as various interpretations:")
    print(f"  Hex: {' '.join(f'{b:02x}' for b in data[:32])}")
    print(f"  LE16 words: {[struct.unpack_from('<H', data, i)[0] for i in range(0, 32, 2)]}")
    print(f"  LE32 dwords: {[struct.unpack_from('<I', data, i)[0] for i in range(0, 32, 4)]}")
    print()

    # Try to find repeating patterns or structure
    # Check if there's a header followed by tile data

    # Check for common patterns at specific offsets
    print("Checking for potential offsets:")
    for offset in [0, 2, 4, 8, 16, 32, 64, 128, 256, 512]:
        if offset < len(data):
            segment = data[offset:offset+32]
            print(f"  Offset 0x{offset:04x}: {' '.join(f'{b:02x}' for b in segment[:16])}")

    print()

    # Check for row-interleaved planar format (like TITLEPAG.EGA)
    # TITLEPAG is 32768 bytes = 320x200 row-interleaved planar
    # Each row: 320/8 = 40 bytes per plane * 4 planes = 160 bytes per scanline
    # 200 scanlines * 160 = 32000 bytes

    print("Checking if it might be row-interleaved planar:")
    # For full width (320 pixels):
    bytes_per_plane_row = 320 // 8  # 40 bytes
    bytes_per_scanline = bytes_per_plane_row * 4  # 160 bytes

    # For different widths:
    for width in [320, 256, 128, 64, 56, 48, 40, 32]:
        bpr = width // 8
        bps = bpr * 4
        height = file_size // bps
        remainder = file_size % bps
        if remainder == 0 or remainder < bps:
            print(f"  {width}x{height} image: {bps} bytes/line, remainder={remainder}")

    print()

    # Check if there might be a tile array with a header
    # Maybe first N bytes are an index, then tile data
    print("Checking for potential header + tile data patterns:")

    # If it's a collection of 32x32 tiles (512 bytes each):
    tile_size_32 = 512
    # Maybe first part is a lookup table?
    for header_size in [0, 16, 32, 64, 128, 256, 512]:
        body_size = file_size - header_size
        tile_count = body_size // tile_size_32
        remainder = body_size % tile_size_32
        if remainder == 0:
            print(f"  Header={header_size}, Body={body_size}: {tile_count} tiles of 512 bytes each (32x32)")

    # Try smaller tiles too
    tile_size_16 = 128
    for header_size in [0, 16, 32, 64, 128, 256, 512, 1024, 2048]:
        body_size = file_size - header_size
        tile_count = body_size // tile_size_16
        remainder = body_size % tile_size_16
        if remainder == 0:
            print(f"  Header={header_size}, Body={body_size}: {tile_count} tiles of 128 bytes each (16x16)")

if __name__ == "__main__":
    analyze_mazedata()
