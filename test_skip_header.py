"""Test if skipping the first N bytes gives us better tiles.

The good tiles (21, 25, 27) are at offsets 10752, 12800, 13824.
What if we skip ~10KB of header data?
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import Sprite

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def create_grayscale_palette():
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_planar_tile(tile_data: bytes, width: int, height: int, palette: list) -> Sprite:
    pixels = [0] * (width * height)
    bytes_per_plane = (width * height) // 8

    for plane in range(4):
        plane_offset = plane * bytes_per_plane

        for row in range(height):
            for byte_idx in range(width // 8):
                data_offset = plane_offset + row * (width // 8) + byte_idx
                byte_val = tile_data[data_offset]

                for bit in range(8):
                    x = byte_idx * 8 + (7 - bit)
                    pixel_idx = row * width + x

                    if byte_val & (1 << bit):
                        pixels[pixel_idx] |= (1 << plane)

    return Sprite(width, height, pixels, palette)


def test_different_offsets():
    """Try decoding tiles starting from different offsets."""
    print("Testing Different Starting Offsets")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    palette = create_grayscale_palette()

    width, height = 32, 32
    bytes_per_tile = 512

    # Test different starting offsets
    test_offsets = [
        0,      # Original (tile 0 at byte 0)
        5120,   # ~10KB / 2
        10240,  # ~10KB (20 tiles worth)
        10752,  # Exactly where tile 21 is
        11264,  # One tile after that
    ]

    for skip_bytes in test_offsets:
        print(f"\nStarting at offset 0x{skip_bytes:06X} ({skip_bytes} bytes)")
        print("-" * 70)

        # Extract first 64 tiles from this offset
        tiles = []
        for i in range(64):
            offset = skip_bytes + i * bytes_per_tile
            if offset + bytes_per_tile > len(data):
                break

            tile_data = data[offset:offset + bytes_per_tile]

            try:
                tile = decode_planar_tile(tile_data, width, height, palette)
                tiles.append((i, tile))
            except:
                break

        if not tiles:
            print(f"  Could not decode any tiles")
            continue

        print(f"  Decoded {len(tiles)} tiles")

        # Create grid
        if HAS_PIL:
            grid_cols = 8
            grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

            grid_img = Image.new('RGB', (width * grid_cols * 3, height * grid_rows * 3 + 40), (30, 30, 30))
            draw = ImageDraw.Draw(grid_img)

            draw.text((10, 10), f"Offset: 0x{skip_bytes:06X} ({skip_bytes} bytes)", fill=(255, 255, 255))

            for idx, (tile_num, tile) in enumerate(tiles):
                grid_x = (idx % grid_cols) * width * 3
                grid_y = (idx // grid_cols) * height * 3 + 40

                tile_img = Image.new('RGB', (width, height))
                tile_pixels = []

                for y in range(height):
                    for x in range(width):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(palette):
                            tile_pixels.append(palette[color_idx])
                        else:
                            tile_pixels.append((0, 0, 0))

                tile_img.putdata(tile_pixels)
                tile_img = tile_img.resize((width * 3, height * 3), Image.NEAREST)

                grid_img.paste(tile_img, (grid_x, grid_y))

                # Label
                draw.text((grid_x + 2, grid_y + 2), str(tile_num), fill=(255, 255, 0))

            filename = f"offset_{skip_bytes:06X}_grid.png"
            grid_img.save(filename)
            print(f"  Saved: {filename}")

        else:
            pygame.quit()

    print("\n" + "=" * 70)
    print("Offset testing complete!")
    print("Check which offset gives the most good-looking tiles!")
    print("=" * 70)


if __name__ == "__main__":
    test_different_offsets()
