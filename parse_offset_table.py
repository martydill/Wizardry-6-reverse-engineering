"""Parse MAZEDATA.EGA using offset table structure.

The first bytes appear to be offsets pointing to descriptors within metadata.
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


def parse_with_offset_table():
    """Parse using offset table structure."""
    print("Parsing MAZEDATA.EGA with Offset Table Structure")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required")
        return

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    metadata = data[:TILE_DATA_OFFSET]
    tile_data_region = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    # Read offset table until we find an offset that seems to mark the end
    # or until offsets stop making sense
    print("Reading offset table from start of file:")
    print("-" * 70)

    offsets = []
    pos = 0

    while pos < TILE_DATA_OFFSET - 1:
        offset = metadata[pos] | (metadata[pos + 1] << 8)

        # Check if this is a valid offset within metadata region
        if offset == 0 or offset >= TILE_DATA_OFFSET:
            # Might be end of offset table
            if len(offsets) > 0:
                print(f"\nOffset table ends at position 0x{pos:04X}")
                print(f"Found {len(offsets)} entries")
                break

        offsets.append(offset)
        pos += 2

        if len(offsets) <= 20:
            print(f"  Tile {len(offsets)-1:3d}: offset 0x{offset:04X} ({offset})")

    print()

    # Now parse descriptors at each offset
    print(f"Parsing {len(offsets)} tile descriptors:")
    print("-" * 70)

    tiles = []

    for tile_idx, desc_offset in enumerate(offsets):
        if desc_offset == 0:
            continue

        if desc_offset >= TILE_DATA_OFFSET:
            continue

        # Read descriptor - try different formats
        # Format guess: [flags?][tile_offset_le16][width][height][...]

        if desc_offset + 5 >= TILE_DATA_OFFSET:
            continue

        desc = metadata[desc_offset:desc_offset + 20]

        # Try format: [offset_le16][width_4px][height_4px]
        tile_offset_le16 = desc[0] | (desc[1] << 8)
        width_4px = desc[2]
        height_4px = desc[3]

        width_px = width_4px * 4
        height_px = height_4px * 4

        # Validate
        if not (4 <= width_px <= 256 and 4 <= height_px <= 256):
            # Try alternative: first byte is flags
            tile_offset_le16 = desc[1] | (desc[2] << 8)
            width_4px = desc[3]
            height_4px = desc[4]
            width_px = width_4px * 4
            height_px = height_4px * 4

        if not (4 <= width_px <= 256 and 4 <= height_px <= 256):
            if tile_idx < 20:
                hex_str = ' '.join(f'{b:02X}' for b in desc[:8])
                print(f"  Tile {tile_idx:3d} @ meta 0x{desc_offset:04X}: INVALID - {hex_str}")
            continue

        # Check if tile offset is valid
        required_bytes = (width_px * height_px) // 2
        if tile_offset_le16 + required_bytes > len(tile_data_region):
            if tile_idx < 20:
                print(f"  Tile {tile_idx:3d} @ meta 0x{desc_offset:04X}: OUT OF BOUNDS - offset=0x{tile_offset_le16:04X}, dims={width_px}x{height_px}")
            continue

        tiles.append({
            'index': tile_idx,
            'meta_offset': desc_offset,
            'tile_offset': tile_offset_le16,
            'width': width_px,
            'height': height_px,
        })

        if tile_idx < 20:
            print(f"  Tile {tile_idx:3d} @ meta 0x{desc_offset:04X}: offset=0x{tile_offset_le16:04X}, dims={width_px:3d}x{height_px:3d}")

    print(f"\nFound {len(tiles)} valid tiles")
    print()

    # Extract tiles
    output_dir = Path("offset_table_tiles")
    output_dir.mkdir(exist_ok=True)

    print(f"Extracting tiles to {output_dir}/...")
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
    print(f"Total tiles extracted: {len(tiles)}")


if __name__ == "__main__":
    parse_with_offset_table()
