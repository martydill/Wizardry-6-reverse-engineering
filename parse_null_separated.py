"""Parse MAZEDATA.EGA as NULL-separated variable-length records.

Looking at the data, there are many sequences separated by 0x00 bytes.
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


def parse_null_separated():
    """Parse as NULL-separated records."""
    print("Parsing MAZEDATA.EGA as NULL-Separated Records")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required")
        return

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]
    tile_data_region = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    # Find all non-zero sequences
    sequences = []
    in_record = False
    record_start = 0

    for i in range(len(metadata)):
        if metadata[i] != 0:
            if not in_record:
                record_start = i
                in_record = True
        else:
            if in_record:
                record_data = metadata[record_start:i]
                sequences.append((record_start, record_data))
                in_record = False

    print(f"Found {len(sequences)} NULL-separated sequences")
    print()

    # Try to parse each sequence as one or more tile descriptors
    # Format might be: multiple [offset_le16][width][height] records per sequence

    tiles = []
    tile_idx = 0

    for seq_idx, (seq_start, seq_data) in enumerate(sequences):
        # Try to parse as packed 4-byte records
        pos = 0
        while pos + 4 <= len(seq_data):
            offset_le16 = seq_data[pos] | (seq_data[pos + 1] << 8)
            width_4px = seq_data[pos + 2]
            height_4px = seq_data[pos + 3]

            width_px = width_4px * 4
            height_px = height_4px * 4

            # Validate
            if 4 <= width_px <= 256 and 4 <= height_px <= 256:
                required_bytes = (width_px * height_px) // 2
                if offset_le16 + required_bytes <= len(tile_data_region):
                    tiles.append({
                        'index': tile_idx,
                        'seq_index': seq_idx,
                        'meta_offset': seq_start + pos,
                        'tile_offset': offset_le16,
                        'width': width_px,
                        'height': height_px,
                    })

                    if tile_idx < 30:
                        print(f"  Tile {tile_idx:3d} @ meta 0x{seq_start + pos:04X}: offset=0x{offset_le16:04X}, dims={width_px:3d}x{height_px:3d}")

                    tile_idx += 1

            pos += 4

    print(f"\nFound {len(tiles)} valid tiles")
    print()

    # Extract tiles
    output_dir = Path("null_separated_tiles")
    output_dir.mkdir(exist_ok=True)

    print(f"Extracting first 50 tiles to {output_dir}/...")
    print("-" * 70)

    for tile in tiles[:50]:
        try:
            offset = tile['tile_offset']
            width = tile['width']
            height = tile['height']

            required_bytes = (width * height) // 2
            tile_bytes = tile_data_region[offset:offset + required_bytes]

            # Decode
            sprite = decode_planar_tile(tile_bytes, width, height, palette)

            # Save
            img = sprite_to_pil_image(sprite)
            filename = f"tile_{tile['index']:03d}_{width}x{height}.png"
            img.save(output_dir / filename)

            # Save 4x
            img_4x = img.resize((width * 4, height * 4), Image.NEAREST)
            filename_4x = f"tile_{tile['index']:03d}_{width}x{height}_4x.png"
            img_4x.save(output_dir / filename_4x)

            unique_colors = len(set(sprite.pixels))

            if tile['index'] < 10 or unique_colors > 2:
                print(f"  Tile {tile['index']:3d}: {width:3d}x{height:3d}, {unique_colors:2d} colors")

        except Exception as e:
            print(f"  Tile {tile['index']:3d}: ERROR - {e}")

    print()
    print("=" * 70)
    print(f"Total tiles found: {len(tiles)}")


if __name__ == "__main__":
    parse_null_separated()
