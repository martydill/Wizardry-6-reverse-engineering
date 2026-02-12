"""Examine the good tiles (21, 25, 27) to find what makes them special."""

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


def examine_good_tiles():
    """Examine tiles 21, 25, 27 in detail."""
    print("Examining Good Tiles (21, 25, 27)")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    palette = create_grayscale_palette()

    width, height = 32, 32
    bytes_per_tile = 512

    good_tiles = [21, 25, 27]

    # Also check surrounding tiles
    all_tiles_to_check = list(range(15, 35))

    print(f"Checking tiles {all_tiles_to_check[0]} to {all_tiles_to_check[-1]}")
    print()

    if HAS_PIL:
        # Create comparison grid
        cols = 10
        rows = (len(all_tiles_to_check) + cols - 1) // cols

        comparison = Image.new('RGB', (width * cols * 4, height * rows * 4 + 40), (30, 30, 30))
        draw = ImageDraw.Draw(comparison)

        for idx, tile_num in enumerate(all_tiles_to_check):
            offset = tile_num * bytes_per_tile
            tile_data = data[offset:offset + bytes_per_tile]

            try:
                tile = decode_planar_tile(tile_data, width, height, palette)

                # Convert to image
                tile_img = Image.new('RGB', (width, height))
                tile_pixels = []

                for y in range(height):
                    for x in range(width):
                        color_idx = tile.get_pixel(x, y)
                        if 0 <= color_idx < len(palette):
                            tile_pixels.append(palette[color_idx])
                        else:
                            tile_pixels.append((0, 0, 0))

                tile_img.putdata(tile_pixels)
                tile_img = tile_img.resize((width * 4, height * 4), Image.NEAREST)

                grid_x = (idx % cols) * width * 4
                grid_y = (idx // cols) * height * 4 + 40

                comparison.paste(tile_img, (grid_x, grid_y))

                # Label
                label = str(tile_num)
                color = (0, 255, 0) if tile_num in good_tiles else (200, 200, 200)
                draw.text((grid_x + 2, grid_y + 2), label, fill=color)

                # Highlight good tiles with border
                if tile_num in good_tiles:
                    draw.rectangle([grid_x, grid_y, grid_x + width * 4, grid_y + height * 4],
                                 outline=(0, 255, 0), width=3)

            except Exception as e:
                print(f"Error on tile {tile_num}: {e}")

        # Add title
        draw.text((10, 10), "Tiles 15-34 (Good tiles 21, 25, 27 in green)", fill=(255, 255, 255))

        comparison.save("good_tiles_region.png")
        print(f"Saved: good_tiles_region.png")

        # Save individual good tiles at large scale
        for tile_num in good_tiles:
            offset = tile_num * bytes_per_tile
            tile_data = data[offset:offset + bytes_per_tile]

            tile = decode_planar_tile(tile_data, width, height, palette)

            tile_img = Image.new('RGB', (width, height))
            tile_pixels = []

            for y in range(height):
                for x in range(width):
                    color_idx = tile.get_pixel(x, y)
                    if 0 <= color_idx < len(palette):
                        tile_pixels.append(palette[color_idx])
                    else:
                        tile_pixels.append((0, 0, 0))

            tile_img.putdata(tile_pixels)
            tile_img = tile_img.resize((width * 8, height * 8), Image.NEAREST)

            # Add label
            labeled = Image.new('RGB', (width * 8, height * 8 + 40), (20, 20, 20))
            labeled.paste(tile_img, (0, 40))

            draw = ImageDraw.Draw(labeled)
            draw.text((10, 10), f"Tile #{tile_num} (GOOD)", fill=(0, 255, 0))

            labeled.save(f"tile_{tile_num}_good_8x.png")
            print(f"Saved: tile_{tile_num}_good_8x.png")

    else:
        pygame.quit()

    # Analyze data patterns
    print("\nAnalyzing data patterns of good tiles:")
    print("-" * 70)

    for tile_num in good_tiles:
        offset = tile_num * bytes_per_tile
        tile_data = data[offset:offset + bytes_per_tile]

        print(f"\nTile {tile_num}:")
        print(f"  Offset: 0x{offset:06X} ({offset} bytes)")
        print(f"  First 32 bytes: {' '.join(f'{b:02X}' for b in tile_data[:32])}")
        print(f"  Last 32 bytes:  {' '.join(f'{b:02X}' for b in tile_data[-32:])}")

        # Check for patterns
        unique_bytes = len(set(tile_data))
        zero_count = tile_data.count(0)
        ff_count = tile_data.count(0xFF)

        print(f"  Unique byte values: {unique_bytes}/256")
        print(f"  Zero bytes: {zero_count}/{len(tile_data)} ({zero_count*100/len(tile_data):.1f}%)")
        print(f"  0xFF bytes: {ff_count}/{len(tile_data)} ({ff_count*100/len(tile_data):.1f}%)")

    # Check tile positions
    print("\n" + "=" * 70)
    print("Tile position analysis:")
    print("-" * 70)
    print(f"Good tiles: {good_tiles}")
    print(f"Pattern: 21, 25, 27")
    print(f"Differences: 25-21=4, 27-25=2")
    print(f"Offsets in file: {[t*512 for t in good_tiles]}")
    print(f"Offsets in hex: {[f'0x{t*512:06X}' for t in good_tiles]}")

    print("\n" + "=" * 70)
    print("Examination complete!")
    print("Check good_tiles_region.png and individual tile images")
    print("=" * 70)


if __name__ == "__main__":
    examine_good_tiles()
