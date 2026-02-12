"""Verify that offsets point to tile data.

If offset 0x0130 with dims 32x32 points to a tile, we should be able to decode it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import Sprite

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def create_grayscale_palette():
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_planar_tile(tile_data: bytes, width: int, height: int, palette: list) -> Sprite:
    """Decode tiled planar tile."""
    pixels = [0] * (width * height)
    bytes_per_plane = (width * height) // 8

    for plane in range(4):
        plane_offset = plane * bytes_per_plane

        for row in range(height):
            for byte_idx in range(width // 8):
                data_offset = plane_offset + row * (width // 8) + byte_idx
                if data_offset >= len(tile_data):
                    break
                byte_val = tile_data[data_offset]

                for bit in range(8):
                    x = byte_idx * 8 + (7 - bit)
                    pixel_idx = row * width + x

                    if byte_val & (1 << bit):
                        pixels[pixel_idx] |= (1 << plane)

    return Sprite(width, height, pixels, palette)


def sprite_to_pil_image(sprite: Sprite) -> Image.Image:
    """Convert sprite to PIL image."""
    img = Image.new('RGB', (sprite.width, sprite.height))
    pixels = []

    for y in range(sprite.height):
        for x in range(sprite.width):
            color_idx = sprite.get_pixel(x, y)
            if 0 <= color_idx < len(sprite.palette):
                pixels.append(sprite.palette[color_idx])
            else:
                pixels.append((0, 0, 0))

    img.putdata(pixels)
    return img


def verify():
    """Verify tile offsets."""
    print("Verifying Tile Offsets")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required")
        return

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    tile_data_region = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    # Test the 6 offsets we found
    test_cases = [
        (0x0130, 32, 32),  # 08 x 08 in 4px units
        (0x0385, 32, 32),
        (0x03B8, 32, 32),
        (0x0C07, 32, 32),
        (0x160A, 32, 32),
        (0x176B, 32, 32),
    ]

    output_dir = Path("verified_tiles")
    output_dir.mkdir(exist_ok=True)

    for idx, (offset, width, height) in enumerate(test_cases):
        print(f"\nTest case {idx + 1}:")
        print(f"  Offset: 0x{offset:04X} ({offset})")
        print(f"  Expected dims: {width}x{height}")

        # Calculate required bytes
        required_bytes = (width * height) // 2  # 4-bit pixels
        print(f"  Required bytes: {required_bytes}")

        # Check if we have enough data
        if offset + required_bytes > len(tile_data_region):
            print(f"  ERROR: Not enough data! (have {len(tile_data_region) - offset} bytes)")
            continue

        # Extract tile data
        tile_bytes = tile_data_region[offset:offset + required_bytes]

        try:
            # Decode tile
            tile = decode_planar_tile(tile_bytes, width, height, palette)

            # Convert to image
            img = sprite_to_pil_image(tile)

            # Save
            filename = f"tile_offset_0x{offset:04X}_{width}x{height}.png"
            img.save(output_dir / filename)

            # Save 4x scaled version
            img_4x = img.resize((width * 4, height * 4), Image.NEAREST)
            filename_4x = f"tile_offset_0x{offset:04X}_{width}x{height}_4x.png"
            img_4x.save(output_dir / filename_4x)

            print(f"  SUCCESS: Saved {filename}")

            # Check if it looks like valid data (not all zeros or all same color)
            unique_colors = len(set(tile.pixels))
            print(f"  Unique colors: {unique_colors}/16")

        except Exception as e:
            print(f"  ERROR: {e}")

    print()
    print("=" * 70)
    print(f"Verified tiles saved to {output_dir}/")


if __name__ == "__main__":
    verify()
