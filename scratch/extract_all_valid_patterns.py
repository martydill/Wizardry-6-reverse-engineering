"""Extract ALL tiles by scanning for valid [offset][width][height] patterns.

Don't rely on NULL-separation or fixed alignment - just scan for valid patterns.
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


def extract_all_valid():
    """Scan for all valid dimension patterns and extract matching tiles."""
    print("Extracting All Valid Tile Patterns")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required")
        return

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]
    tile_data_region = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    # Scan for all dimension byte pairs
    # Common dimensions in 4px units: 02-40 (8px-256px)
    tiles = []
    seen_positions = set()  # Avoid duplicates

    for i in range(len(metadata) - 1):
        width_4px = metadata[i]
        height_4px = metadata[i + 1]

        # Check if this looks like a reasonable dimension pair
        if not (2 <= width_4px <= 64 and 2 <= height_4px <= 64):
            continue

        width_px = width_4px * 4
        height_px = height_4px * 4

        # Check if there's a valid offset 2 bytes before
        if i < 2:
            continue

        offset_le16 = metadata[i - 2] | (metadata[i - 1] << 8)

        # Validate offset
        required_bytes = (width_px * height_px) // 2
        if offset_le16 + required_bytes > len(tile_data_region):
            continue

        # Skip duplicates (same metadata position)
        if (i - 2) in seen_positions:
            continue

        seen_positions.add(i - 2)

        # Get flags byte (if exists)
        flags = metadata[i - 3] if i >= 3 else 0

        tiles.append({
            'meta_offset': i - 2,
            'flags': flags,
            'offset': offset_le16,
            'width': width_px,
            'height': height_px,
        })

    print(f"Found {len(tiles)} valid tile patterns")
    print()

    # Sort by metadata offset
    tiles.sort(key=lambda t: t['meta_offset'])

    # Show first 30
    for idx, tile in enumerate(tiles[:30]):
        print(f"  Tile {idx:3d} @ meta 0x{tile['meta_offset']:04X}: "
              f"flags=0x{tile['flags']:02X}, offset=0x{tile['offset']:04X}, "
              f"dims={tile['width']:3d}x{tile['height']:3d}")

    print()

    # Extract all tiles
    output_dir = Path("all_valid_tiles")
    output_dir.mkdir(exist_ok=True)

    print(f"Extracting all {len(tiles)} tiles to {output_dir}/...")
    print("-" * 70)

    for idx, tile in enumerate(tiles):
        try:
            offset = tile['offset']
            width = tile['width']
            height = tile['height']
            flags = tile['flags']

            required_bytes = (width * height) // 2
            tile_bytes = tile_data_region[offset:offset + required_bytes]

            # Decode
            sprite = decode_planar_tile(tile_bytes, width, height, palette)

            # Save
            img = sprite_to_pil_image(sprite)
            filename = f"tile_{idx:03d}_offset{offset:04X}_flags{flags:02X}_{width}x{height}.png"
            img.save(output_dir / filename)

            # Save 4x
            img_4x = img.resize((width * 4, height * 4), Image.NEAREST)
            filename_4x = f"tile_{idx:03d}_offset{offset:04X}_flags{flags:02X}_{width}x{height}_4x.png"
            img_4x.save(output_dir / filename_4x)

            unique_colors = len(set(sprite.pixels))

            if idx < 10 or idx % 50 == 0:
                print(f"  Tile {idx:3d}: offset=0x{offset:04X}, {width:3d}x{height:3d}, {unique_colors:2d} colors")

        except Exception as e:
            print(f"  Tile {idx:3d}: ERROR - {e}")

    print()
    print("=" * 70)
    print(f"Total tiles extracted: {len(tiles)}")
    print()
    print("The good 32x32 tile should be in there!")


if __name__ == "__main__":
    extract_all_valid()
