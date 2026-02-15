"""Extract wall textures from MAZEDATA.EGA - CORRECTED VERSION.

The file structure is:
- Bytes 0-766: Unknown header/metadata (767 bytes)
- Bytes 767+: Sequential planar image data (320 width)
- Format: Sequential planar (NOT tiled planar)
- Palette: DEFAULT_16_PALETTE (EGA default colors)
"""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def extract():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    print(f"File size: {len(data)} bytes")

    # Skip 767-byte header
    image_data = data[767:]
    print(f"Image data: {len(image_data)} bytes")

    output_dir = Path("output/mazedata_corrected")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use DEFAULT_16_PALETTE (EGA default colors)
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Wizardry 6 uses plane order [3, 0, 2, 1]
    plane_order = [3, 0, 2, 1]

    # Extract as 64x64 tiles (walls)
    tile_size_64 = 2048  # (64*64*4)/8 bytes
    num_tiles_64 = len(image_data) // tile_size_64

    print(f"Extracting {num_tiles_64} tiles of 64x64...")
    for i in range(num_tiles_64):
        tile_data = image_data[i * tile_size_64 : (i + 1) * tile_size_64]
        sprite = decoder.decode_planar(
            tile_data,
            width=64,
            height=64,
            plane_order=plane_order
        )

        # Skip empty tiles
        if all(p == 0 for p in sprite.pixels):
            continue

        img = Image.frombytes("RGB", (64, 64), sprite.to_rgb_bytes())
        # Scale 2x for visibility
        img = img.resize((128, 128), Image.NEAREST)
        img.save(output_dir / f"wall_64x64_{i:03d}.png")

    # Extract as 32x32 tiles (smaller elements)
    tile_size_32 = 512  # (32*32*4)/8 bytes
    num_tiles_32 = len(image_data) // tile_size_32

    print(f"Extracting {num_tiles_32} tiles of 32x32...")
    saved_32 = 0
    for i in range(num_tiles_32):
        tile_data = image_data[i * tile_size_32 : (i + 1) * tile_size_32]
        sprite = decoder.decode_planar(
            tile_data,
            width=32,
            height=32,
            plane_order=plane_order
        )

        # Skip empty tiles
        if all(p == 0 for p in sprite.pixels):
            continue

        img = Image.frombytes("RGB", (32, 32), sprite.to_rgb_bytes())
        # Scale 2x for visibility
        img = img.resize((64, 64), Image.NEAREST)
        img.save(output_dir / f"tile_32x32_{i:03d}.png")
        saved_32 += 1

    # Also extract as a full atlas to see the overall layout
    # Try 320 width (standard EGA width)
    plane_size = len(image_data) // 4
    width = 320
    height = (plane_size * 8) // width

    print(f"Extracting full atlas as {width}x{height}...")
    try:
        atlas = decoder.decode_planar(
            image_data[:plane_size * 4],
            width=width,
            height=height,
            plane_order=plane_order
        )
        img = Image.frombytes("RGB", (width, height), atlas.to_rgb_bytes())
        img.save(output_dir / f"atlas_full_{width}x{height}.png")
    except Exception as e:
        print(f"Failed to extract atlas: {e}")

    print(f"Saved tiles to {output_dir}")

if __name__ == "__main__":
    extract()
