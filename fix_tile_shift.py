"""Fix tile shift - rotate each row 24 pixels to the left.

The tiles appear to be shifted right by 24px and wrapped around.
This fixes it by rotating each row left.
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


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes


def create_grayscale_palette():
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_planar_tile(tile_data: bytes, width: int, height: int, palette: list) -> Sprite:
    """Decode a 32×32 tiled planar tile."""
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


def shift_tile_right(tile: Sprite, shift_amount: int) -> Sprite:
    """Shift each row of the tile to the left by shift_amount pixels (with wrap)."""
    new_pixels = []

    for y in range(tile.height):
        row_pixels = []
        for x in range(tile.width):
            row_pixels.append(tile.get_pixel(x, y))

        # Rotate left by shift_amount
        shifted_row = row_pixels[shift_amount:] + row_pixels[:shift_amount]
        new_pixels.extend(shifted_row)

    return Sprite(
        width=tile.width,
        height=tile.height,
        pixels=new_pixels,
        palette=tile.palette
    )


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


def fix_all_tiles():
    """Extract and fix all tiles with 24-pixel shift correction."""
    print("Extracting and Fixing Tiles (24-pixel shift correction)")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required for this script")
        return

    # Load file
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    tile_data = data[TILE_DATA_OFFSET:]
    palette = create_grayscale_palette()

    width, height = 32, 32
    bytes_per_tile = 512
    shift_amount = 24  # Shift left by 24 pixels

    num_tiles = len(tile_data) // bytes_per_tile
    print(f"Number of tiles: {num_tiles}")
    print(f"Shift correction: {shift_amount} pixels left")
    print()

    # Create output directories
    tiles_fixed_dir = Path("tiles_fixed")
    tiles_fixed_dir.mkdir(exist_ok=True)

    tiles_fixed_2x_dir = Path("tiles_fixed_2x")
    tiles_fixed_2x_dir.mkdir(exist_ok=True)

    tiles_fixed_4x_dir = Path("tiles_fixed_4x")
    tiles_fixed_4x_dir.mkdir(exist_ok=True)

    # Extract and fix all tiles
    print("Extracting and fixing tiles...")
    tiles = []

    for i in range(num_tiles):
        offset = i * bytes_per_tile
        tile_bytes = tile_data[offset:offset + bytes_per_tile]

        if len(tile_bytes) < bytes_per_tile:
            break

        try:
            # Decode tile
            tile = decode_planar_tile(tile_bytes, width, height, palette)

            # Fix shift
            tile_fixed = shift_tile_right(tile, shift_amount)

            tiles.append((i, tile_fixed))

            # Save original size
            tile_img = sprite_to_pil_image(tile_fixed)
            tile_img.save(tiles_fixed_dir / f"tile_{i:03d}.png")

            # Save 2x
            tile_2x = tile_img.resize((width * 2, height * 2), Image.NEAREST)
            tile_2x.save(tiles_fixed_2x_dir / f"tile_{i:03d}_2x.png")

            # Save 4x
            tile_4x = tile_img.resize((width * 4, height * 4), Image.NEAREST)
            tile_4x.save(tiles_fixed_4x_dir / f"tile_{i:03d}_4x.png")

            if (i + 1) % 10 == 0:
                print(f"  Fixed {i + 1}/{num_tiles} tiles...")

        except Exception as e:
            print(f"Error on tile {i}: {e}")
            break

    print(f"\nSuccessfully fixed {len(tiles)} tiles!")
    print()

    # Create comparison grid (before/after for first 20 tiles)
    print("Creating before/after comparison...")

    comparison_grid = Image.new('RGB', (width * 20 * 4, height * 2 * 4 + 50), (30, 30, 30))
    draw = ImageDraw.Draw(comparison_grid)

    draw.text((10, 10), "Top row: ORIGINAL | Bottom row: FIXED (shifted 24px left)",
              fill=(255, 255, 255))

    for i in range(min(20, num_tiles)):
        offset = i * bytes_per_tile
        tile_bytes = tile_data[offset:offset + bytes_per_tile]

        # Original
        tile_original = decode_planar_tile(tile_bytes, width, height, palette)
        img_original = sprite_to_pil_image(tile_original)
        img_original = img_original.resize((width * 4, height * 4), Image.NEAREST)

        # Fixed
        tile_fixed = shift_tile_right(tile_original, shift_amount)
        img_fixed = sprite_to_pil_image(tile_fixed)
        img_fixed = img_fixed.resize((width * 4, height * 4), Image.NEAREST)

        x = i * width * 4
        comparison_grid.paste(img_original, (x, 50))
        comparison_grid.paste(img_fixed, (x, 50 + height * 4))

        # Label
        draw.text((x + 2, 52), str(i), fill=(255, 255, 0))

    comparison_grid.save("tile_shift_comparison.png")
    print("  Saved: tile_shift_comparison.png")

    # Create master grids
    print("Creating master tile grids...")

    grid_cols = 10
    grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

    # 2x grid with numbers
    grid_2x = Image.new('RGB', (width * grid_cols * 2, height * grid_rows * 2), (20, 20, 20))
    draw = ImageDraw.Draw(grid_2x)

    for idx, (tile_num, tile) in enumerate(tiles):
        x = (idx % grid_cols) * width * 2
        y = (idx // grid_cols) * height * 2

        tile_img = sprite_to_pil_image(tile)
        tile_2x = tile_img.resize((width * 2, height * 2), Image.NEAREST)
        grid_2x.paste(tile_2x, (x, y))

        draw.text((x + 2, y + 2), str(tile_num), fill=(255, 255, 0))

    grid_2x.save("all_tiles_fixed_grid_2x.png")
    print("  Saved: all_tiles_fixed_grid_2x.png")

    # 3x grid
    grid_3x = Image.new('RGB', (width * grid_cols * 3, height * grid_rows * 3), (20, 20, 20))

    for idx, (tile_num, tile) in enumerate(tiles):
        x = (idx % grid_cols) * width * 3
        y = (idx // grid_cols) * height * 3

        tile_img = sprite_to_pil_image(tile)
        tile_3x = tile_img.resize((width * 3, height * 3), Image.NEAREST)
        grid_3x.paste(tile_3x, (x, y))

    grid_3x.save("all_tiles_fixed_grid_3x.png")
    print("  Saved: all_tiles_fixed_grid_3x.png")

    print()
    print("=" * 70)
    print("Tile shift correction complete!")
    print()
    print("Fixed tiles saved to:")
    print("  tiles_fixed/    - Original size (32x32)")
    print("  tiles_fixed_2x/ - 2x scale (64x64)")
    print("  tiles_fixed_4x/ - 4x scale (128x128)")
    print()
    print("Comparison and grids:")
    print("  tile_shift_comparison.png      - Before/after comparison")
    print("  all_tiles_fixed_grid_2x.png    - All fixed tiles at 2x")
    print("  all_tiles_fixed_grid_3x.png    - All fixed tiles at 3x")
    print()
    print(f"Total tiles fixed: {len(tiles)}")
    print("=" * 70)


if __name__ == "__main__":
    fix_all_tiles()
