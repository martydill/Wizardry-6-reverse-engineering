"""Decode MAZEDATA.EGA using tiled planar format.

Based on analysis, it appears that MAZEDATA.EGA contains 8x8 tiles
in planar format (like MON*.PIC), not a full sequential planar image.
"""

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def decode_planar_tile(tile_data: bytes, palette: List[Tuple[int, int, int]]) -> Sprite:
    """Decode an 8x8 tile in planar format.

    Each 32-byte tile contains:
    - Bytes 0-7: Plane 0 (bit 0 of color)
    - Bytes 8-15: Plane 1 (bit 1 of color)
    - Bytes 16-23: Plane 2 (bit 2 of color)
    - Bytes 24-31: Plane 3 (bit 3 of color)

    Each plane byte contains 8 pixels (MSB first).
    """
    if len(tile_data) < 32:
        raise ValueError(f"Tile data too small: {len(tile_data)} bytes")

    pixels = [0] * 64  # 8x8 = 64 pixels

    for plane in range(4):
        plane_offset = plane * 8

        for row in range(8):
            byte_val = tile_data[plane_offset + row]

            # Extract 8 pixels from this byte (MSB first)
            for bit in range(8):
                pixel_idx = row * 8 + (7 - bit)  # MSB first
                if byte_val & (1 << bit):
                    pixels[pixel_idx] |= (1 << plane)

    return Sprite(width=8, height=8, pixels=pixels, palette=palette)


def extract_and_render_tiles():
    """Extract tiles from MAZEDATA.EGA and render them."""
    print("MAZEDATA.EGA Tiled Planar Decoder")
    print("=" * 70)

    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()

    # Based on analysis, tiles start after the big null sequence
    # First big null sequence is at 0x0EE9 with 2436 bytes
    # Data after that (starting around 0x18F8 or 0x1931) looks like tiles

    # Let's try different starting offsets
    possible_starts = [
        (0x0AF9, "After first small null seq"),
        (0x1931, "After big null seq"),
        (0x0000, "File start"),
        (0x0099, "After first word"),
    ]

    for start_offset, description in possible_starts:
        print(f"\n{description} (offset 0x{start_offset:04X}):")
        print("-" * 70)

        if start_offset >= len(data):
            print(f"  Offset beyond file end")
            continue

        # Calculate how many tiles we can extract
        available_bytes = len(data) - start_offset
        num_tiles = available_bytes // 32

        print(f"  Available bytes: {available_bytes}")
        print(f"  Potential tiles: {num_tiles}")

        if num_tiles == 0:
            continue

        # Extract first 64 tiles (8x8 grid) for visualization
        tiles_to_extract = min(64, num_tiles)
        tiles = []

        for i in range(tiles_to_extract):
            offset = start_offset + i * 32
            tile_data = data[offset:offset + 32]

            try:
                tile = decode_planar_tile(tile_data, DEFAULT_16_PALETTE)
                tiles.append(tile)
            except Exception as e:
                print(f"  Error decoding tile {i}: {e}")
                break

        if not tiles:
            print(f"  No tiles successfully decoded")
            continue

        print(f"  Successfully decoded {len(tiles)} tiles")

        # Arrange tiles in an 8x8 grid
        grid_size = 8
        tile_size = 8

        if HAS_PIL:
            # Create grid image
            grid_img = Image.new('RGB', (grid_size * tile_size, grid_size * tile_size))

            for idx, tile in enumerate(tiles[:grid_size * grid_size]):
                grid_x = (idx % grid_size) * tile_size
                grid_y = (idx // grid_size) * tile_size

                # Convert tile to PIL image
                tile_img = Image.new('RGB', (tile_size, tile_size))
                tile_pixels = []

                for y in range(tile_size):
                    for x in range(tile_size):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(tile.palette):
                            tile_pixels.append(tile.palette[color_idx])
                        else:
                            tile_pixels.append((0, 0, 0))

                tile_img.putdata(tile_pixels)
                grid_img.paste(tile_img, (grid_x, grid_y))

            # Scale up for visibility
            scaled_img = grid_img.resize((grid_size * tile_size * 4, grid_size * tile_size * 4), Image.NEAREST)

            # Save
            safe_name = description.replace(" ", "_").replace("(", "").replace(")", "")
            filename = f"mazedata_tiles_{safe_name}.png"
            scaled_img.save(filename)
            print(f"  Saved to: {filename}")

        else:
            # Pygame version
            pygame.init()

            grid_surf = pygame.Surface((grid_size * tile_size, grid_size * tile_size))

            for idx, tile in enumerate(tiles[:grid_size * grid_size]):
                grid_x = (idx % grid_size) * tile_size
                grid_y = (idx // grid_size) * tile_size

                for y in range(tile_size):
                    for x in range(tile_size):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(tile.palette):
                            color = tile.palette[color_idx]
                            grid_surf.set_at((grid_x + x, grid_y + y), color)

            # Scale up
            scaled_surf = pygame.transform.scale(
                grid_surf,
                (grid_size * tile_size * 4, grid_size * tile_size * 4)
            )

            safe_name = description.replace(" ", "_").replace("(", "").replace(")", "")
            filename = f"mazedata_tiles_{safe_name}.png"
            pygame.image.save(scaled_surf, filename)
            print(f"  Saved to: {filename}")

            pygame.quit()

    # Also try extracting ALL tiles and arranging them in a texture atlas
    print(f"\n{'=' * 70}")
    print("Creating full tile atlas...")
    print("-" * 70)

    # Use the most promising offset
    best_offset = 0x0AF9
    available_bytes = len(data) - best_offset
    num_tiles = available_bytes // 32

    print(f"Extracting all {num_tiles} tiles from offset 0x{best_offset:04X}")

    all_tiles = []
    for i in range(num_tiles):
        offset = best_offset + i * 32
        tile_data = data[offset:offset + 32]

        try:
            tile = decode_planar_tile(tile_data, DEFAULT_16_PALETTE)
            all_tiles.append(tile)
        except:
            break

    print(f"Successfully decoded {len(all_tiles)} tiles")

    if len(all_tiles) > 0:
        # Arrange in a grid (40 tiles wide for approximately square atlas)
        atlas_width = 40
        atlas_height = (len(all_tiles) + atlas_width - 1) // atlas_width

        print(f"Creating atlas: {atlas_width} x {atlas_height} tiles")
        print(f"Atlas size: {atlas_width * 8} x {atlas_height * 8} pixels")

        if HAS_PIL:
            atlas_img = Image.new('RGB', (atlas_width * 8, atlas_height * 8), (0, 0, 0))

            for idx, tile in enumerate(all_tiles):
                atlas_x = (idx % atlas_width) * 8
                atlas_y = (idx // atlas_width) * 8

                tile_img = Image.new('RGB', (8, 8))
                tile_pixels = []

                for y in range(8):
                    for x in range(8):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(tile.palette):
                            tile_pixels.append(tile.palette[color_idx])
                        else:
                            tile_pixels.append((0, 0, 0))

                tile_img.putdata(tile_pixels)
                atlas_img.paste(tile_img, (atlas_x, atlas_y))

            atlas_img.save("mazedata_full_atlas.png")
            print(f"Saved full atlas to: mazedata_full_atlas.png")

            # Also save a 2x scaled version
            scaled_atlas = atlas_img.resize((atlas_width * 16, atlas_height * 16), Image.NEAREST)
            scaled_atlas.save("mazedata_full_atlas_2x.png")
            print(f"Saved 2x atlas to: mazedata_full_atlas_2x.png")

        else:
            pygame.init()

            atlas_surf = pygame.Surface((atlas_width * 8, atlas_height * 8))
            atlas_surf.fill((0, 0, 0))

            for idx, tile in enumerate(all_tiles):
                atlas_x = (idx % atlas_width) * 8
                atlas_y = (idx // atlas_width) * 8

                for y in range(8):
                    for x in range(8):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(tile.palette):
                            color = tile.palette[color_idx]
                            atlas_surf.set_at((atlas_x + x, atlas_y + y), color)

            pygame.image.save(atlas_surf, "mazedata_full_atlas.png")
            print(f"Saved full atlas to: mazedata_full_atlas.png")

            scaled_atlas = pygame.transform.scale(atlas_surf, (atlas_width * 16, atlas_height * 16))
            pygame.image.save(scaled_atlas, "mazedata_full_atlas_2x.png")
            print(f"Saved 2x atlas to: mazedata_full_atlas_2x.png")

            pygame.quit()


if __name__ == "__main__":
    extract_and_render_tiles()

    print("\n" + "=" * 70)
    print("Tile extraction complete!")
    print("Check the generated PNG files to see if textures look correct.")
    print("=" * 70)
