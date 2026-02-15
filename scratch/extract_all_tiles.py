"""Extract all tiles from MAZEDATA.EGA starting at correct offset.

Tiles start at offset 0x002A00 (10,752 bytes).
Generate individual PNGs for each tile.
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


TILE_DATA_OFFSET = 0x002A00  # 10,752 bytes - where tiles actually start


def create_grayscale_palette():
    """Create 16-level grayscale palette."""
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

                # MSB first
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


def extract_all_tiles():
    """Extract all tiles from MAZEDATA.EGA."""
    print("Extracting All Tiles from MAZEDATA.EGA")
    print("=" * 70)

    if not HAS_PIL:
        print("PIL required for this script")
        pygame.init()
        print("Using pygame instead...")

    # Load file
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    print(f"File size: {len(data):,} bytes")
    print(f"Tile data starts at: 0x{TILE_DATA_OFFSET:06X} ({TILE_DATA_OFFSET:,} bytes)")
    print()

    # Extract tile data
    tile_data = data[TILE_DATA_OFFSET:]
    print(f"Tile data size: {len(tile_data):,} bytes")

    palette = create_grayscale_palette()

    width, height = 32, 32
    bytes_per_tile = 512

    num_tiles = len(tile_data) // bytes_per_tile
    print(f"Number of tiles: {num_tiles}")
    print()

    # Create output directories
    tiles_dir = Path("tiles")
    tiles_dir.mkdir(exist_ok=True)

    tiles_2x_dir = Path("tiles_2x")
    tiles_2x_dir.mkdir(exist_ok=True)

    tiles_4x_dir = Path("tiles_4x")
    tiles_4x_dir.mkdir(exist_ok=True)

    # Extract all tiles
    print("Extracting tiles...")
    tiles = []

    for i in range(num_tiles):
        offset = i * bytes_per_tile
        tile_bytes = tile_data[offset:offset + bytes_per_tile]

        if len(tile_bytes) < bytes_per_tile:
            print(f"Warning: Tile {i} has incomplete data")
            break

        try:
            tile = decode_planar_tile(tile_bytes, width, height, palette)
            tiles.append((i, tile))

            if HAS_PIL:
                # Save original size
                tile_img = sprite_to_pil_image(tile)
                tile_img.save(tiles_dir / f"tile_{i:03d}.png")

                # Save 2x
                tile_2x = tile_img.resize((width * 2, height * 2), Image.NEAREST)
                tile_2x.save(tiles_2x_dir / f"tile_{i:03d}_2x.png")

                # Save 4x
                tile_4x = tile_img.resize((width * 4, height * 4), Image.NEAREST)
                tile_4x.save(tiles_4x_dir / f"tile_{i:03d}_4x.png")
            else:
                # Pygame version
                surf = pygame.Surface((width, height))
                for y in range(height):
                    for x in range(width):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(palette):
                            surf.set_at((x, y), palette[color_idx])

                pygame.image.save(surf, str(tiles_dir / f"tile_{i:03d}.png"))

                surf_2x = pygame.transform.scale(surf, (width * 2, height * 2))
                pygame.image.save(surf_2x, str(tiles_2x_dir / f"tile_{i:03d}_2x.png"))

                surf_4x = pygame.transform.scale(surf, (width * 4, height * 4))
                pygame.image.save(surf_4x, str(tiles_4x_dir / f"tile_{i:03d}_4x.png"))

            if (i + 1) % 10 == 0:
                print(f"  Extracted {i + 1}/{num_tiles} tiles...")

        except Exception as e:
            print(f"Error on tile {i}: {e}")
            break

    print(f"\nSuccessfully extracted {len(tiles)} tiles!")
    print()

    # Create master grids
    print("Creating master tile grids...")

    if HAS_PIL:
        # Full grid (all tiles)
        grid_cols = 10
        grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

        # 1x grid
        grid_1x = Image.new('RGB', (width * grid_cols, height * grid_rows), (20, 20, 20))
        for idx, (tile_num, tile) in enumerate(tiles):
            x = (idx % grid_cols) * width
            y = (idx // grid_cols) * height
            tile_img = sprite_to_pil_image(tile)
            grid_1x.paste(tile_img, (x, y))

        grid_1x.save("all_tiles_grid_1x.png")
        print(f"  Saved: all_tiles_grid_1x.png ({grid_cols}x{grid_rows} grid)")

        # 2x grid with numbers
        grid_2x = Image.new('RGB', (width * grid_cols * 2, height * grid_rows * 2), (20, 20, 20))
        draw = ImageDraw.Draw(grid_2x)

        for idx, (tile_num, tile) in enumerate(tiles):
            x = (idx % grid_cols) * width * 2
            y = (idx // grid_cols) * height * 2

            tile_img = sprite_to_pil_image(tile)
            tile_2x = tile_img.resize((width * 2, height * 2), Image.NEAREST)
            grid_2x.paste(tile_2x, (x, y))

            # Add tile number
            draw.text((x + 2, y + 2), str(tile_num), fill=(255, 255, 0))

        grid_2x.save("all_tiles_grid_2x_numbered.png")
        print(f"  Saved: all_tiles_grid_2x_numbered.png (with tile numbers)")

        # 3x grid (for better viewing)
        grid_3x = Image.new('RGB', (width * grid_cols * 3, height * grid_rows * 3), (20, 20, 20))
        for idx, (tile_num, tile) in enumerate(tiles):
            x = (idx % grid_cols) * width * 3
            y = (idx // grid_cols) * height * 3

            tile_img = sprite_to_pil_image(tile)
            tile_3x = tile_img.resize((width * 3, height * 3), Image.NEAREST)
            grid_3x.paste(tile_3x, (x, y))

        grid_3x.save("all_tiles_grid_3x.png")
        print(f"  Saved: all_tiles_grid_3x.png")

    else:
        # Pygame version
        grid_cols = 10
        grid_rows = (len(tiles) + grid_cols - 1) // grid_cols

        grid = pygame.Surface((width * grid_cols * 2, height * grid_rows * 2))
        grid.fill((20, 20, 20))

        for idx, (tile_num, tile) in enumerate(tiles):
            x = (idx % grid_cols) * width * 2
            y = (idx // grid_cols) * height * 2

            surf = pygame.Surface((width, height))
            for py in range(height):
                for px in range(width):
                    color_idx = tile.get_pixel(px, py)
                    if 0 <= color_idx < len(palette):
                        surf.set_at((px, py), palette[color_idx])

            surf_2x = pygame.transform.scale(surf, (width * 2, height * 2))
            grid.blit(surf_2x, (x, y))

        pygame.image.save(grid, "all_tiles_grid_2x.png")
        print(f"  Saved: all_tiles_grid_2x.png")

        pygame.quit()

    print()
    print("=" * 70)
    print("Tile extraction complete!")
    print()
    print(f"Individual tiles saved to:")
    print(f"  tiles/       - Original size (32x32)")
    print(f"  tiles_2x/    - 2x scale (64x64)")
    print(f"  tiles_4x/    - 4x scale (128x128)")
    print()
    print(f"Master grids:")
    print(f"  all_tiles_grid_1x.png          - All tiles at 1x")
    print(f"  all_tiles_grid_2x_numbered.png - All tiles at 2x with numbers")
    print(f"  all_tiles_grid_3x.png          - All tiles at 3x")
    print()
    print(f"Total tiles extracted: {len(tiles)}")
    print("=" * 70)


if __name__ == "__main__":
    extract_all_tiles()
