"""Try treating MAZEDATA as 4bpp tiled planar textures.

Instead of one big sequential planar image, maybe it's a collection
of small planar tiles (like MON*.PIC files use).
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


def decode_planar_tile(tile_data: bytes, width: int, height: int, palette: list) -> Sprite:
    """Decode a single tile in planar format.

    Tiled planar format (like MON*.PIC):
    - Each tile has 4 planes stored together
    - For 8x8 tile: 8 bytes per plane × 4 planes = 32 bytes
    - For 16x16 tile: 32 bytes per plane × 4 planes = 128 bytes
    - For 32x32 tile: 128 bytes per plane × 4 planes = 512 bytes

    Layout:
    - Bytes 0 to (width*height/8)-1: Plane 0 (bit 0)
    - Next (width*height/8) bytes: Plane 1 (bit 1)
    - Next (width*height/8) bytes: Plane 2 (bit 2)
    - Next (width*height/8) bytes: Plane 3 (bit 3)
    """
    pixels = [0] * (width * height)
    bytes_per_plane = (width * height) // 8

    if len(tile_data) < bytes_per_plane * 4:
        raise ValueError(f"Not enough data: need {bytes_per_plane * 4}, got {len(tile_data)}")

    for plane in range(4):
        plane_offset = plane * bytes_per_plane

        for row in range(height):
            for byte_idx in range(width // 8):
                data_offset = plane_offset + row * (width // 8) + byte_idx
                if data_offset >= len(tile_data):
                    break

                byte_val = tile_data[data_offset]

                # Extract 8 pixels from this byte (MSB first)
                for bit in range(8):
                    x = byte_idx * 8 + (7 - bit)
                    pixel_idx = row * width + x

                    if pixel_idx < len(pixels):
                        if byte_val & (1 << bit):
                            pixels[pixel_idx] |= (1 << plane)

    return Sprite(width=width, height=height, pixels=pixels, palette=palette)


def create_color_palette():
    """Create default 16-color EGA palette."""
    return [
        (0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170),
        (170, 0, 0), (170, 0, 170), (170, 85, 0), (170, 170, 170),
        (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255),
        (255, 85, 85), (255, 85, 255), (255, 255, 85), (255, 255, 255)
    ]


def create_grayscale_palette():
    """Create 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


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


def try_tiled_planar():
    """Try decoding MAZEDATA as tiled planar textures."""
    print("MAZEDATA.EGA Tiled Planar Decoding")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load data
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    output_dir = Path("tiled_planar_tests")
    output_dir.mkdir(exist_ok=True)

    # Try different tile sizes
    tile_configs = [
        (8, 8, 32, "8x8"),      # 8x8 = 64 pixels = 32 bytes planar
        (16, 16, 128, "16x16"),  # 16x16 = 256 pixels = 128 bytes planar
        (32, 32, 512, "32x32"),  # 32x32 = 1024 pixels = 512 bytes planar
        (64, 32, 1024, "64x32"), # 64x32 = 2048 pixels = 1024 bytes planar
        (32, 64, 1024, "32x64"), # 32x64 = 2048 pixels = 1024 bytes planar
    ]

    # Try both color and grayscale palettes
    palettes = [
        (create_color_palette(), "color"),
        (create_grayscale_palette(), "grayscale"),
    ]

    for palette, pal_name in palettes:
        print(f"\nTesting with {pal_name} palette:")
        print("-" * 70)

        for width, height, bytes_per_tile, size_name in tile_configs:
            print(f"\n  Tile size: {size_name} ({bytes_per_tile} bytes per tile)")

            # Calculate how many tiles we can extract
            num_tiles = len(data) // bytes_per_tile
            print(f"  Can extract: {num_tiles} tiles")

            # Extract first 64 tiles (or fewer)
            tiles_to_extract = min(64, num_tiles)
            tiles = []

            for i in range(tiles_to_extract):
                offset = i * bytes_per_tile
                tile_data = data[offset:offset + bytes_per_tile]

                try:
                    tile = decode_planar_tile(tile_data, width, height, palette)
                    tiles.append(tile)
                except Exception as e:
                    print(f"    Error decoding tile {i}: {e}")
                    break

            if not tiles:
                print(f"    No tiles decoded successfully")
                continue

            print(f"  Decoded: {len(tiles)} tiles")

            # Arrange tiles in a grid
            grid_cols = 8
            grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

            if HAS_PIL:
                # Create grid
                grid_img = Image.new('RGB', (width * grid_cols * 2, height * grid_rows * 2))

                for idx, tile in enumerate(tiles):
                    grid_x = (idx % grid_cols) * width * 2
                    grid_y = (idx // grid_cols) * height * 2

                    tile_img = sprite_to_image(tile, scale=2)
                    grid_img.paste(tile_img, (grid_x, grid_y))

                filename = output_dir / f"{pal_name}_{size_name}_grid.png"
                grid_img.save(filename)
                print(f"  Saved: {filename}")

                # Also save first tile at 4x
                if tiles:
                    first_tile = sprite_to_image(tiles[0], scale=4)
                    first_file = output_dir / f"{pal_name}_{size_name}_first_4x.png"
                    first_tile.save(first_file)
                    print(f"  First tile: {first_file}")

            else:
                # Pygame version
                grid_surf = pygame.Surface((width * grid_cols * 2, height * grid_rows * 2))
                grid_surf.fill((0, 0, 0))

                for idx, tile in enumerate(tiles):
                    grid_x = (idx % grid_cols) * width * 2
                    grid_y = (idx // grid_cols) * height * 2

                    tile_surf = sprite_to_image(tile, scale=2)
                    grid_surf.blit(tile_surf, (grid_x, grid_y))

                filename = output_dir / f"{pal_name}_{size_name}_grid.png"
                pygame.image.save(grid_surf, str(filename))
                print(f"  Saved: {filename}")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("Tiled planar tests complete!")
    print("Check tiled_planar_tests/ directory")
    print("Look for clear brick/stone patterns!")
    print("=" * 70)


if __name__ == "__main__":
    try_tiled_planar()
