"""Visualize MAZEDATA.EGA with grid overlays to understand organization."""

from pathlib import Path
from PIL import Image, ImageDraw
import sys

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE


def create_gridded_atlas(cell_width, cell_height, output_name):
    """Create atlas visualization with grid overlay."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    # Convert to PIL Image
    img = Image.frombytes("RGB", (atlas.width, atlas.height), atlas.to_rgb_bytes())

    # Scale up for visibility
    scale = 2
    img = img.resize((atlas.width * scale, atlas.height * scale), Image.NEAREST)

    # Draw grid
    draw = ImageDraw.Draw(img)

    # Draw vertical lines
    for x in range(0, atlas.width + 1, cell_width):
        x_scaled = x * scale
        draw.line([(x_scaled, 0), (x_scaled, atlas.height * scale)], fill=(255, 255, 0), width=1)

    # Draw horizontal lines
    for y in range(0, atlas.height + 1, cell_height):
        y_scaled = y * scale
        draw.line([(0, y_scaled), (atlas.width * scale, y_scaled)], fill=(255, 255, 0), width=1)

    # Save
    output_dir = Path("output/grids")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    img.save(output_path)

    print(f"  {cell_width}x{cell_height} grid: {output_path.name}")
    return img


def analyze_column_patterns():
    """Analyze patterns in vertical columns to find texture boundaries."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print("\nAnalyzing column patterns (looking for texture boundaries):")
    print()

    # For each X position, calculate a "signature" of that column
    # by counting unique colors in the top 40 rows
    signatures = []
    for x in range(atlas.width):
        colors = set()
        for y in range(min(40, atlas.height)):
            colors.add(atlas.get_pixel(x, y))
        signatures.append(len(colors))

    # Look for significant changes in signature (potential boundaries)
    print("  Potential texture boundaries (X coordinates where pattern changes):")
    print("  ", end="")
    boundary_count = 0
    for x in range(1, len(signatures) - 1):
        # Look for drops or spikes in color count
        prev_avg = sum(signatures[max(0, x-4):x]) / min(4, x)
        curr = signatures[x]
        next_avg = sum(signatures[x+1:min(len(signatures), x+5)]) / 4

        if abs(curr - prev_avg) > 2 or abs(curr - next_avg) > 2:
            print(f"x={x:3d} ", end="")
            boundary_count += 1
            if boundary_count % 10 == 0:
                print("\n  ", end="")

    print(f"\n  Found {boundary_count} potential boundaries")


def extract_wall_perspective_samples():
    """Extract what might be wall sections at different perspectives."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print()
    print("Extracting potential wall/floor texture sections:")
    print()

    output_dir = Path("output/wall_sections")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Based on typical dungeon crawler layouts, textures might be arranged as:
    # - Different wall types in columns
    # - Different distances/perspectives in rows

    # Try extracting 32-pixel wide columns (common wall texture width)
    for col in range(10):  # First 10 columns
        x = col * 32
        if x >= atlas.width:
            break

        # Extract tall section (might span multiple texture types vertically)
        w, h = 32, 200
        pixels = []
        for dy in range(h):
            for dx in range(w):
                if x + dx < atlas.width and dy < atlas.height:
                    pixels.append(atlas.get_pixel(x + dx, dy))
                else:
                    pixels.append(0)

        from bane.data.sprite_decoder import Sprite
        section = Sprite(width=w, height=h, pixels=pixels, palette=atlas.palette)

        # Scale up width for visibility
        scaled = section.scale(4)

        img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
        output_path = output_dir / f"column_{col:02d}_x{x:03d}.png"
        img.save(output_path)

        if col == 0:
            print(f"  Saved 10 columns (32 pixels wide each)")


if __name__ == "__main__":
    print("MAZEDATA.EGA Atlas Grid Visualization")
    print("=" * 70)
    print("\nCreating grid overlays:")

    # Try different grid sizes
    create_gridded_atlas(32, 32, "grid_32x32.png")
    create_gridded_atlas(16, 16, "grid_16x16.png")
    create_gridded_atlas(40, 40, "grid_40x40.png")
    create_gridded_atlas(64, 32, "grid_64x32.png")

    analyze_column_patterns()
    extract_wall_perspective_samples()

    print()
    print("=" * 70)
    print("Check output/grids/ and output/wall_sections/")
