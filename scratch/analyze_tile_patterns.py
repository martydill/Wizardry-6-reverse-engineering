"""Analyze MAZEDATA.EGA to find repeating tile patterns."""

from pathlib import Path
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite


def find_horizontal_repetition(atlas, y, max_width=64):
    """Find repeating pattern width in a horizontal line."""
    width = atlas.width

    # Try different pattern widths
    for pattern_width in range(1, min(max_width, width // 2) + 1):
        # Check if pattern repeats
        repeats = True
        for x in range(pattern_width, width):
            if atlas.get_pixel(x, y) != atlas.get_pixel(x % pattern_width, y):
                repeats = False
                break

        if repeats:
            return pattern_width

    return None


def find_vertical_repetition(atlas, x, max_height=64):
    """Find repeating pattern height in a vertical line."""
    height = atlas.height

    # Try different pattern heights
    for pattern_height in range(1, min(max_height, height // 2) + 1):
        # Check if pattern repeats
        repeats = True
        for y in range(pattern_height, height):
            if atlas.get_pixel(x, y) != atlas.get_pixel(x, y % pattern_height):
                repeats = False
                break

        if repeats:
            return pattern_height

    return None


def analyze_patterns():
    """Analyze MAZEDATA for repeating patterns."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print("Analyzing MAZEDATA.EGA for repeating tile patterns")
    print("=" * 70)
    print()

    # Check horizontal repetition at various Y coordinates
    print("Horizontal repetition analysis:")
    for y in [0, 5, 10, 15, 20, 30, 40, 50, 60, 70, 80, 100, 120, 140, 160, 180]:
        if y >= atlas.height:
            break
        pattern_width = find_horizontal_repetition(atlas, y)
        if pattern_width:
            print(f"  Y={y:3d}: repeats every {pattern_width:3d} pixels")
        else:
            print(f"  Y={y:3d}: no repetition found (or > 64 pixels)")

    print()

    # Check vertical repetition at various X coordinates
    print("Vertical repetition analysis:")
    for x in [0, 16, 32, 48, 64, 80, 96, 128, 160, 192, 224, 256]:
        if x >= atlas.width:
            break
        pattern_height = find_vertical_repetition(atlas, x)
        if pattern_height:
            print(f"  X={x:3d}: repeats every {pattern_height:3d} pixels")
        else:
            print(f"  X={x:3d}: no repetition found (or > 64 pixels)")

    print()
    print("=" * 70)
    print("Extracting sample tiles based on common sizes:")
    print()

    # Extract tiles at common sizes
    output_dir = Path("output/tiles")
    output_dir.mkdir(parents=True, exist_ok=True)

    tile_sizes = [
        (8, 8, "8x8"),
        (16, 8, "16x8"),
        (32, 8, "32x8"),
        (16, 16, "16x16"),
        (32, 16, "32x16"),
        (32, 32, "32x32"),
        (64, 32, "64x32"),
    ]

    for tw, th, name in tile_sizes:
        # Extract a few tiles at this size
        for tile_x in range(0, min(5, atlas.width // tw)):
            for tile_y in range(0, min(3, atlas.height // th)):
                x = tile_x * tw
                y = tile_y * th

                # Extract tile
                pixels = []
                for dy in range(th):
                    for dx in range(tw):
                        pixels.append(atlas.get_pixel(x + dx, y + dy))

                tile = Sprite(width=tw, height=th, pixels=pixels, palette=atlas.palette)

                # Scale up for viewing
                scale = 8 if tw <= 16 else 4
                scaled = tile.scale(scale)

                img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
                output_path = output_dir / f"tile_{name}_x{tile_x}_y{tile_y}.png"
                img.save(output_path)

                if tile_x == 0 and tile_y == 0:
                    print(f"  {name}: extracted {min(5, atlas.width // tw)} x {min(3, atlas.height // th)} tiles")


def extract_specific_regions():
    """Extract specific interesting regions from the atlas."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    output_dir = Path("output/regions")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract various regions that might be walls, floors, etc.
    regions = [
        # First few rows (likely wall textures)
        ("top_strip_320x40", 0, 0, 320, 40),
        # Middle section
        ("middle_strip_320x40", 0, 80, 320, 40),
        # Bottom section
        ("bottom_strip_320x40", 0, 160, 320, 40),
        # Left column
        ("left_column_64x200", 0, 0, 64, 200),
        # Various sizes
        ("region_128x64_topleft", 0, 0, 128, 64),
    ]

    print()
    print("=" * 70)
    print("Extracting specific regions:")
    print()

    for name, x, y, w, h in regions:
        pixels = []
        for dy in range(h):
            for dx in range(w):
                pixels.append(atlas.get_pixel(x + dx, y + dy))

        region = Sprite(width=w, height=h, pixels=pixels, palette=atlas.palette)

        # Scale if small
        if w <= 128:
            region = region.scale(2)

        img = Image.frombytes("RGB", (region.width, region.height), region.to_rgb_bytes())
        output_path = output_dir / f"{name}.png"
        img.save(output_path)

        print(f"  {name}: {w}x{h} -> {output_path.name}")


if __name__ == "__main__":
    analyze_patterns()
    extract_specific_regions()
    print()
    print("Analysis complete! Check output/tiles/ and output/regions/")
