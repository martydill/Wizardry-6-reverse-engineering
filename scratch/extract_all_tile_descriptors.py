"""Extract all tile descriptors from MAZEDATA.EGA metadata.

Format confirmed: [offset_le16][width_4px][height_4px] (4 bytes/record)
But records might be variable-length or have additional data.
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


def extract_all():
    """Extract all tile descriptors."""
    print("Extracting All Tile Descriptors from MAZEDATA.EGA")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required")
        return

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]
    tile_data_region = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    # Try parsing as 4-byte records
    print("Attempting to parse metadata as 4-byte records...")
    print("-" * 70)

    descriptors = []
    num_records = len(metadata) // 4

    print(f"Metadata size: {len(metadata)} bytes")
    print(f"Potential records (4 bytes each): {num_records}")
    print()

    # Parse all records
    for i in range(num_records):
        offset_in_metadata = i * 4
        record = metadata[offset_in_metadata:offset_in_metadata + 4]

        if len(record) < 4:
            break

        offset_le16 = record[0] | (record[1] << 8)
        width_4px = record[2]
        height_4px = record[3]

        width_px = width_4px * 4
        height_px = height_4px * 4

        # Sanity check: dimensions should be reasonable
        if 4 <= width_px <= 256 and 4 <= height_px <= 256:
            # Check if offset is within tile data region
            required_bytes = (width_px * height_px) // 2
            if offset_le16 + required_bytes <= len(tile_data_region):
                descriptors.append({
                    'index': i,
                    'offset': offset_le16,
                    'width': width_px,
                    'height': height_px,
                    'meta_offset': offset_in_metadata,
                })

    print(f"Found {len(descriptors)} potentially valid descriptors")
    print()

    # Show first 20
    print("First 20 descriptors:")
    for desc in descriptors[:20]:
        print(f"  [{desc['index']:3d}] @ meta 0x{desc['meta_offset']:04X}: "
              f"offset=0x{desc['offset']:04X}, dims={desc['width']:3d}x{desc['height']:3d}")

    print()

    # Extract and save first 50 tiles
    output_dir = Path("all_extracted_tiles")
    output_dir.mkdir(exist_ok=True)

    print(f"Extracting first 50 tiles to {output_dir}/...")
    print("-" * 70)

    for desc in descriptors[:50]:
        try:
            offset = desc['offset']
            width = desc['width']
            height = desc['height']

            required_bytes = (width * height) // 2
            tile_bytes = tile_data_region[offset:offset + required_bytes]

            # Decode
            tile = decode_planar_tile(tile_bytes, width, height, palette)

            # Save
            img = sprite_to_pil_image(tile)
            filename = f"tile_{desc['index']:03d}_{width}x{height}.png"
            img.save(output_dir / filename)

            # Save 4x
            img_4x = img.resize((width * 4, height * 4), Image.NEAREST)
            filename_4x = f"tile_{desc['index']:03d}_{width}x{height}_4x.png"
            img_4x.save(output_dir / filename_4x)

            unique_colors = len(set(tile.pixels))

            if desc['index'] < 10 or unique_colors > 2:
                print(f"  Tile {desc['index']:3d}: {width:3d}x{height:3d}, {unique_colors:2d} colors - {filename}")

        except Exception as e:
            print(f"  Tile {desc['index']:3d}: ERROR - {e}")

    print()
    print("=" * 70)
    print(f"Total descriptors: {len(descriptors)}")
    print(f"Tiles extracted to {output_dir}/")


if __name__ == "__main__":
    extract_all()
