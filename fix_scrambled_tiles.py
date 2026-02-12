"""Fix scrambled tiles by trying different decoding parameters.

Some tiles look perfect, others are scrambled. They might need:
- Different bit order (MSB vs LSB)
- Different plane order
- Different starting offset
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
    import pygame


def create_grayscale_palette():
    """Create 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_planar_tile(tile_data: bytes, width: int, height: int,
                       palette: list, msb_first: bool = True,
                       plane_order: list = None) -> Sprite:
    """Decode a tile with configurable parameters."""
    if plane_order is None:
        plane_order = [0, 1, 2, 3]

    pixels = [0] * (width * height)
    bytes_per_plane = (width * height) // 8

    if len(tile_data) < bytes_per_plane * 4:
        raise ValueError(f"Not enough data")

    for plane_idx, plane in enumerate(plane_order):
        plane_offset = plane_idx * bytes_per_plane

        for row in range(height):
            for byte_idx in range(width // 8):
                data_offset = plane_offset + row * (width // 8) + byte_idx
                if data_offset >= len(tile_data):
                    break

                byte_val = tile_data[data_offset]

                for bit in range(8):
                    if msb_first:
                        x = byte_idx * 8 + (7 - bit)
                    else:
                        x = byte_idx * 8 + bit

                    pixel_idx = row * width + x

                    if pixel_idx < len(pixels):
                        if byte_val & (1 << bit):
                            pixels[pixel_idx] |= (1 << plane)

    return Sprite(width=width, height=height, pixels=pixels, palette=palette)


def sprite_to_image(sprite, scale=1):
    """Convert sprite to image."""
    if HAS_PIL:
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
        if scale > 1:
            img = img.resize((sprite.width * scale, sprite.height * scale), Image.NEAREST)
        return img
    else:
        surf = pygame.Surface((sprite.width, sprite.height))
        for y in range(sprite.height):
            for x in range(sprite.width):
                color_idx = sprite.get_pixel(x, y)
                if 0 <= color_idx < len(sprite.palette):
                    surf.set_at((x, y), sprite.palette[color_idx])
        if scale > 1:
            surf = pygame.transform.scale(surf, (sprite.width * scale, sprite.height * scale))
        return surf


def try_fix_scrambled():
    """Try different parameters to fix scrambled tiles."""
    print("Fixing Scrambled Tiles")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load data
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    palette = create_grayscale_palette()

    # 32×32 tiles
    width, height = 32, 32
    bytes_per_tile = 512

    output_dir = Path("tile_fixing")
    output_dir.mkdir(exist_ok=True)

    # Extract first 100 tiles with different parameters
    num_tiles = min(100, len(data) // bytes_per_tile)

    # Different decoding variations
    variations = [
        (True, [0, 1, 2, 3], "MSB_P0123"),
        (False, [0, 1, 2, 3], "LSB_P0123"),
        (True, [3, 2, 1, 0], "MSB_P3210"),
        (False, [3, 2, 1, 0], "LSB_P3210"),
        (True, [0, 2, 1, 3], "MSB_P0213"),
        (True, [1, 0, 2, 3], "MSB_P1023"),
    ]

    print(f"Testing {num_tiles} tiles with {len(variations)} variations each...")
    print()

    # For each variation, create a grid
    for msb_first, plane_order, var_name in variations:
        print(f"Variation: {var_name}")

        tiles = []
        for i in range(num_tiles):
            offset = i * bytes_per_tile
            tile_data = data[offset:offset + bytes_per_tile]

            try:
                tile = decode_planar_tile(
                    tile_data, width, height, palette,
                    msb_first=msb_first,
                    plane_order=plane_order
                )
                tiles.append(tile)
            except Exception as e:
                print(f"  Error on tile {i}: {e}")
                break

        if not tiles:
            continue

        # Create grid (10×10)
        grid_cols = 10
        grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

        if HAS_PIL:
            grid_img = Image.new('RGB', (width * grid_cols * 2, height * grid_rows * 2))

            for idx, tile in enumerate(tiles):
                grid_x = (idx % grid_cols) * width * 2
                grid_y = (idx // grid_cols) * height * 2

                tile_img = sprite_to_image(tile, scale=2)
                grid_img.paste(tile_img, (grid_x, grid_y))

            filename = output_dir / f"grid_{var_name}.png"
            grid_img.save(filename)
            print(f"  Saved: {filename}")

        else:
            grid_surf = pygame.Surface((width * grid_cols * 2, height * grid_rows * 2))
            grid_surf.fill((0, 0, 0))

            for idx, tile in enumerate(tiles):
                grid_x = (idx % grid_cols) * width * 2
                grid_y = (idx // grid_cols) * height * 2

                tile_surf = sprite_to_image(tile, scale=2)
                grid_surf.blit(tile_surf, (grid_x, grid_y))

            filename = output_dir / f"grid_{var_name}.png"
            pygame.image.save(grid_surf, str(filename))
            print(f"  Saved: {filename}")

    # Also create individual comparison images for first 20 tiles
    print("\nCreating individual tile comparisons...")

    for tile_idx in range(min(20, num_tiles)):
        offset = tile_idx * bytes_per_tile
        tile_data = data[offset:offset + bytes_per_tile]

        if HAS_PIL:
            # Create comparison image with all variations
            comparison = Image.new('RGB', (width * len(variations) * 4, height * 4))

            for var_idx, (msb_first, plane_order, var_name) in enumerate(variations):
                try:
                    tile = decode_planar_tile(
                        tile_data, width, height, palette,
                        msb_first=msb_first,
                        plane_order=plane_order
                    )
                    tile_img = sprite_to_image(tile, scale=4)
                    comparison.paste(tile_img, (var_idx * width * 4, 0))
                except:
                    pass

            filename = output_dir / f"tile_{tile_idx:03d}_comparison.png"
            comparison.save(filename)

        else:
            comparison = pygame.Surface((width * len(variations) * 4, height * 4))
            comparison.fill((0, 0, 0))

            for var_idx, (msb_first, plane_order, var_name) in enumerate(variations):
                try:
                    tile = decode_planar_tile(
                        tile_data, width, height, palette,
                        msb_first=msb_first,
                        plane_order=plane_order
                    )
                    tile_surf = sprite_to_image(tile, scale=4)
                    comparison.blit(tile_surf, (var_idx * width * 4, 0))
                except:
                    pass

            filename = output_dir / f"tile_{tile_idx:03d}_comparison.png"
            pygame.image.save(comparison, str(filename))

    print(f"  Saved first 20 tile comparisons")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("Tile fixing complete!")
    print(f"Check {output_dir}/ for results")
    print()
    print("Look for which variation has the MOST correct-looking tiles!")
    print("Some tiles might look good in one variation, others in another.")
    print("=" * 70)


if __name__ == "__main__":
    try_fix_scrambled()
