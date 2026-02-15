"""Extract individual tiles from MAZEDATA.EGA horizontal bands.

Theory: Each horizontal band contains multiple small tiles (8x8, 16x16, or 32x32)
arranged side-by-side, not one continuous 320-pixel-wide texture.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def extract_tiles_from_band(atlas: Sprite, band_y: int, band_height: int, tile_width: int):
    """Extract individual tiles from a horizontal band."""
    tiles = []

    num_tiles = atlas.width // tile_width

    for tile_idx in range(num_tiles):
        tile_x = tile_idx * tile_width

        # Extract tile pixels
        tile_pixels = []
        for y in range(band_y, band_y + band_height):
            for x in range(tile_x, tile_x + tile_width):
                if x < atlas.width and y < atlas.height:
                    tile_pixels.append(atlas.get_pixel(x, y))
                else:
                    tile_pixels.append(0)

        tile = Sprite(
            width=tile_width,
            height=band_height,
            pixels=tile_pixels,
            palette=atlas.palette
        )

        tiles.append(tile)

    return tiles


def sprite_to_image(sprite: Sprite):
    """Convert sprite to PIL image or pygame surface."""
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
        return img
    else:
        surf = pygame.Surface((sprite.width, sprite.height))
        for y in range(sprite.height):
            for x in range(sprite.width):
                color_idx = sprite.get_pixel(x, y)
                if 0 <= color_idx < len(sprite.palette):
                    surf.set_at((x, y), sprite.palette[color_idx])
        return surf


def main():
    print("Extracting Individual Tiles from MAZEDATA.EGA")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load and decode MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print(f"Decoded atlas: {atlas.width}x{atlas.height}")
    print()

    # Try different tile widths
    tile_widths = [8, 16, 32, 40, 64]
    band_height = 32  # Each band is 32 pixels tall

    for tile_width in tile_widths:
        print(f"Extracting {tile_width}x{band_height} tiles...")

        output_dir = Path(f"tiles_{tile_width}x{band_height}")
        output_dir.mkdir(exist_ok=True)

        # Extract from first 6 bands
        for band_idx in range(6):
            band_y = band_idx * band_height

            tiles = extract_tiles_from_band(atlas, band_y, band_height, tile_width)

            print(f"  Band {band_idx} (y={band_y}): {len(tiles)} tiles")

            # Save each tile
            for tile_idx, tile in enumerate(tiles):
                img = sprite_to_image(tile)

                # Scale up 4x for visibility
                if HAS_PIL:
                    scaled = img.resize((tile_width * 4, band_height * 4), Image.NEAREST)
                    filename = output_dir / f"band{band_idx}_tile{tile_idx:02d}.png"
                    scaled.save(filename)
                else:
                    scaled = pygame.transform.scale(img, (tile_width * 4, band_height * 4))
                    filename = output_dir / f"band{band_idx}_tile{tile_idx:02d}.png"
                    pygame.image.save(scaled, str(filename))

        # Also create a grid view of all tiles from band 0
        band_0_tiles = extract_tiles_from_band(atlas, 0, band_height, tile_width)

        # Arrange in grid
        grid_cols = 10
        grid_rows = (len(band_0_tiles) + grid_cols - 1) // grid_cols

        if HAS_PIL:
            grid_img = Image.new('RGB', (tile_width * grid_cols * 2, band_height * grid_rows * 2))

            for idx, tile in enumerate(band_0_tiles):
                grid_x = (idx % grid_cols) * tile_width * 2
                grid_y = (idx // grid_cols) * band_height * 2

                tile_img = sprite_to_image(tile)
                scaled_tile = tile_img.resize((tile_width * 2, band_height * 2), Image.NEAREST)
                grid_img.paste(scaled_tile, (grid_x, grid_y))

            grid_filename = output_dir / f"band0_grid.png"
            grid_img.save(grid_filename)
            print(f"  Saved grid: {grid_filename}")

        else:
            grid_surf = pygame.Surface((tile_width * grid_cols * 2, band_height * grid_rows * 2))
            grid_surf.fill((0, 0, 0))

            for idx, tile in enumerate(band_0_tiles):
                grid_x = (idx % grid_cols) * tile_width * 2
                grid_y = (idx // grid_cols) * band_height * 2

                tile_surf = sprite_to_image(tile)
                scaled_tile = pygame.transform.scale(tile_surf, (tile_width * 2, band_height * 2))
                grid_surf.blit(scaled_tile, (grid_x, grid_y))

            grid_filename = output_dir / f"band0_grid.png"
            pygame.image.save(grid_surf, str(grid_filename))
            print(f"  Saved grid: {grid_filename}")

        print()

    if not HAS_PIL:
        pygame.quit()

    print("=" * 70)
    print("Extraction complete!")
    print("Check the tiles_* directories to see individual textures.")
    print("=" * 70)


if __name__ == "__main__":
    main()
