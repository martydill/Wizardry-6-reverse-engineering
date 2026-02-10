"""Analyze the decoded MAZEDATA atlas to see if it looks right."""

from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def analyze_atlas():
    """Load and analyze the texture atlas."""

    # Decode MAZEDATA.EGA
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Try the first 32KB as row-interleaved
    print("Decoding first 32KB as 320x200 row-interleaved...")
    atlas = decoder.decode_planar_row_interleaved(data[:32000], width=320, height=200)

    # Sample some regions
    print("\nSampling different regions:")
    regions = [
        ("Top-left 32x32", 0, 0, 32, 32),
        ("Top-right 32x32", 288, 0, 32, 32),
        ("Center 64x64", 128, 68, 64, 64),
        ("Bottom-left 32x32", 0, 168, 32, 32),
    ]

    for name, x, y, w, h in regions:
        # Count unique colors in region
        colors = set()
        for dy in range(h):
            for dx in range(w):
                if x + dx < atlas.width and y + dy < atlas.height:
                    colors.add(atlas.get_pixel(x + dx, y + dy))

        print(f"  {name} at ({x},{y}): {len(colors)} unique colors")

        # Extract and save this region
        region_pixels = []
        for dy in range(h):
            for dx in range(w):
                if x + dx < atlas.width and y + dy < atlas.height:
                    region_pixels.append(atlas.get_pixel(x + dx, y + dy))
                else:
                    region_pixels.append(0)

        from bane.data.sprite_decoder import Sprite
        region_sprite = Sprite(width=w, height=h, pixels=region_pixels, palette=atlas.palette)

        # Scale up 4x for viewing
        scaled = region_sprite.scale(4)
        img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
        output_path = Path(f"output/region_{name.replace(' ', '_')}.png")
        img.save(output_path)
        print(f"    Saved to {output_path.name}")

    print("\n" + "="*70)
    print("Now let's try the REMAINING data (after first 32KB)...")
    print()

    # What if the actual textures are in the remaining 70KB?
    remaining = data[32000:]
    print(f"Remaining data: {len(remaining)} bytes")

    # Try to decode it as sequential tiles
    tile_size = 32  # 8x8 planar tile
    num_tiles = len(remaining) // tile_size
    print(f"Could contain {num_tiles} tiles of 8x8 (32 bytes each)")

    # Try decoding first few tiles
    print("\nExtracting first 10 tiles from remaining data:")
    for i in range(min(10, num_tiles)):
        tile_data = remaining[i * tile_size:(i + 1) * tile_size]

        try:
            tile = decoder.decode_planar(tile_data, width=8, height=8)

            # Count colors
            colors = set(tile.pixels)

            # Scale up for viewing
            scaled = tile.scale(8)
            img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
            output_path = Path(f"output/tile_remaining_{i:03d}.png")
            img.save(output_path)

            print(f"  Tile {i}: {len(colors)} colors -> {output_path.name}")
        except Exception as e:
            print(f"  Tile {i}: ERROR - {e}")

    print("\n" + "="*70)
    print("Checking if remaining data might be row-interleaved...")

    # Try different dimensions for the remaining data
    for width in [320, 256, 160, 128, 64, 40]:
        bytes_per_row = (width // 8) * 4
        height = len(remaining) // bytes_per_row

        if height > 0 and height * bytes_per_row <= len(remaining):
            print(f"\n  Trying {width}x{height}...")
            try:
                sprite = decoder.decode_planar_row_interleaved(
                    remaining[:height * bytes_per_row],
                    width=width,
                    height=height
                )
                img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
                output_path = Path(f"output/remaining_{width}x{height}.png")
                img.save(output_path)
                print(f"    SUCCESS -> {output_path.name}")
            except:
                print(f"    Failed")

if __name__ == "__main__":
    analyze_atlas()
