"""Create a numbered grid so user can identify which tiles look correct.

This will help us find the pattern - which tiles are good vs scrambled.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import Sprite

try:
    from PIL import Image, ImageDraw, ImageFont
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


def create_numbered_grid():
    """Create a numbered grid for user to identify good tiles."""
    print("Creating Numbered Tile Grid")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    palette = create_grayscale_palette()

    # 32×32 tiles
    width, height = 32, 32
    bytes_per_tile = 512

    # Extract first 100 tiles
    num_tiles = min(100, len(data) // bytes_per_tile)

    tiles = []
    for i in range(num_tiles):
        offset = i * bytes_per_tile
        tile_data = data[offset:offset + bytes_per_tile]

        try:
            tile = decode_planar_tile(tile_data, width, height, palette)
            tiles.append((i, tile))
        except:
            pass

    print(f"Decoded {len(tiles)} tiles")

    # Create 10×10 grid with numbers
    grid_cols = 10
    grid_rows = (len(tiles) + grid_cols - 1) // grid_cols
    scale = 3  # 3× scale for visibility
    label_height = 20  # Space for tile number

    if HAS_PIL:
        grid_img = Image.new('RGB',
                             (width * grid_cols * scale,
                              (height + label_height) * grid_rows * scale),
                             (30, 30, 30))

        draw = ImageDraw.Draw(grid_img)

        for idx, (tile_num, tile) in enumerate(tiles):
            grid_x = (idx % grid_cols) * width * scale
            grid_y = (idx // grid_cols) * (height + label_height) * scale

            # Draw tile
            tile_img = Image.new('RGB', (width, height))
            tile_pixels = []

            for y in range(height):
                for x in range(width):
                    color_idx = tile.get_pixel(x, y)
                    if 0 <= color_idx < len(tile.palette):
                        tile_pixels.append(tile.palette[color_idx])
                    else:
                        tile_pixels.append((0, 0, 0))

            tile_img.putdata(tile_pixels)
            tile_img = tile_img.resize((width * scale, height * scale), Image.NEAREST)
            grid_img.paste(tile_img, (grid_x, grid_y + label_height * scale))

            # Draw tile number
            label_text = str(tile_num)
            draw.text((grid_x + 2, grid_y + 2), label_text, fill=(255, 255, 0))

            # Draw border
            draw.rectangle(
                [grid_x, grid_y, grid_x + width * scale, grid_y + (height + label_height) * scale],
                outline=(80, 80, 80),
                width=1
            )

        output_path = Path("numbered_tile_grid.png")
        grid_img.save(output_path)
        print(f"Saved: {output_path}")

        # Also create individual large tiles for closer inspection
        print("\nSaving individual tiles at 8× scale...")

        tiles_dir = Path("individual_tiles")
        tiles_dir.mkdir(exist_ok=True)

        for tile_num, tile in tiles[:50]:  # First 50
            tile_img = Image.new('RGB', (width, height))
            tile_pixels = []

            for y in range(height):
                for x in range(width):
                    color_idx = tile.get_pixel(x, y)
                    if 0 <= color_idx < len(tile.palette):
                        tile_pixels.append(tile.palette[color_idx])
                    else:
                        tile_pixels.append((0, 0, 0))

            tile_img.putdata(tile_pixels)
            tile_img = tile_img.resize((width * 8, height * 8), Image.NEAREST)

            # Add label
            labeled = Image.new('RGB', (width * 8, height * 8 + 30), (20, 20, 20))
            labeled.paste(tile_img, (0, 30))

            draw = ImageDraw.Draw(labeled)
            draw.text((5, 5), f"Tile #{tile_num}", fill=(255, 255, 0))

            labeled.save(tiles_dir / f"tile_{tile_num:03d}.png")

        print(f"Saved 50 individual tiles to {tiles_dir}/")

    else:
        # Pygame version
        grid_surf = pygame.Surface((width * grid_cols * scale,
                                    (height + label_height) * grid_rows * scale))
        grid_surf.fill((30, 30, 30))

        font = pygame.font.Font(None, 20)

        for idx, (tile_num, tile) in enumerate(tiles):
            grid_x = (idx % grid_cols) * width * scale
            grid_y = (idx // grid_cols) * (height + label_height) * scale

            # Draw tile
            tile_surf = pygame.Surface((width, height))
            for y in range(height):
                for x in range(width):
                    color_idx = tile.get_pixel(x, y)
                    if 0 <= color_idx < len(tile.palette):
                        tile_surf.set_at((x, y), tile.palette[color_idx])

            tile_surf = pygame.transform.scale(tile_surf, (width * scale, height * scale))
            grid_surf.blit(tile_surf, (grid_x, grid_y + label_height * scale))

            # Draw label
            label = font.render(str(tile_num), True, (255, 255, 0))
            grid_surf.blit(label, (grid_x + 2, grid_y + 2))

            # Border
            pygame.draw.rect(grid_surf, (80, 80, 80),
                           (grid_x, grid_y, width * scale, (height + label_height) * scale), 1)

        output_path = Path("numbered_tile_grid.png")
        pygame.image.save(grid_surf, str(output_path))
        print(f"Saved: {output_path}")

        pygame.quit()

    print("\n" + "=" * 70)
    print("Numbered grid created!")
    print()
    print("Please identify which tile numbers look CORRECT (like walls).")
    print("This will help us find the pattern!")
    print("=" * 70)


if __name__ == "__main__":
    create_numbered_grid()
