"""Extract wall textures from MAZEDATA.EGA using the correct format.

Based on reverse engineering findings:
- Offset 0x000000: Tile descriptor table (10,752 bytes)
- Offset 0x002A00: Tile pixel data
- Descriptor format: 4-byte records [offset_le16][width_4px][height_4px]
- Pixel format: Tiled planar (8x8 tiles, 32 bytes each)
- Palette: DEFAULT_16_PALETTE
"""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

# Constants from reverse engineering
DESCRIPTOR_TABLE_SIZE = 10752  # 0x2A00 bytes
TILE_DATA_OFFSET = 0x2A00
DESCRIPTOR_SIZE = 4  # bytes per descriptor
PIXEL_UNIT_SIZE = 4  # width/height are in units of 4 pixels

def parse_descriptors(data: bytes) -> list[tuple[int, int, int, int]]:
    """Parse tile descriptors.

    Returns list of (index, data_offset, width, height) tuples.
    """
    descriptors = []
    descriptor_count = DESCRIPTOR_TABLE_SIZE // DESCRIPTOR_SIZE

    for i in range(descriptor_count):
        offset = i * DESCRIPTOR_SIZE

        # Parse 4-byte descriptor: [offset_le16][width_unit][height_unit]
        tile_offset_rel = data[offset] | (data[offset + 1] << 8)
        width_units = data[offset + 2]
        height_units = data[offset + 3]

        # Skip invalid descriptors
        if width_units == 0 or height_units == 0:
            continue

        # Convert units to pixels
        width = width_units * PIXEL_UNIT_SIZE
        height = height_units * PIXEL_UNIT_SIZE

        # Skip if not 8-pixel aligned (required for tiled planar)
        if width % 8 != 0 or height % 8 != 0:
            continue

        # Calculate absolute file offset
        data_offset = TILE_DATA_OFFSET + tile_offset_rel

        # Skip if out of bounds
        bytes_needed = (width * height) // 2  # 4 bits per pixel
        if data_offset + bytes_needed > len(data):
            continue

        descriptors.append((i, data_offset, width, height))

    return descriptors

def extract():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    print(f"File size: {len(data)} bytes")

    # Parse descriptor table
    descriptors = parse_descriptors(data)
    print(f"Found {len(descriptors)} valid tile descriptors")

    # Create output directory
    output_dir = Path("output/mazedata_fixed")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use correct palette
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Extract each tile
    saved_count = 0
    for idx, data_offset, width, height in descriptors:
        # Calculate bytes needed for tiled planar format
        tiles_x = width // 8
        tiles_y = height // 8
        tile_count = tiles_x * tiles_y
        bytes_needed = tile_count * 32  # 32 bytes per 8x8 tile

        # Extract tile data
        tile_data = data[data_offset : data_offset + bytes_needed]

        try:
            # Decode using tiled planar format (like monster .PIC files)
            sprite = decoder.decode_tiled_planar(
                tile_data,
                width=width,
                height=height,
                msb_first=True,
                row_major=True,
            )

            # Check if tile has any content
            if all(p == 0 for p in sprite.pixels):
                continue

            # Save tile
            img = Image.frombytes("RGB", (width, height), sprite.to_rgb_bytes())
            # Scale 2x for easier viewing
            img = img.resize((width * 2, height * 2), Image.NEAREST)
            img.save(output_dir / f"tile_{idx:04d}_{width}x{height}_off{data_offset:05X}.png")
            saved_count += 1

        except Exception as e:
            print(f"Failed to decode tile {idx} ({width}x{height}): {e}")
            continue

    print(f"Saved {saved_count} tiles to {output_dir}")

if __name__ == "__main__":
    extract()
