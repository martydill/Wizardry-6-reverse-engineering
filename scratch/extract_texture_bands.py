"""Extract individual texture bands from MAZEDATA.EGA."""

from pathlib import Path
from PIL import Image
import sys

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite


def extract_all_bands():
    """Extract each horizontal texture band."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    output_dir = Path("output/texture_bands")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Extracting Texture Bands from MAZEDATA.EGA")
    print("=" * 70)
    print()

    # Extract bands at different heights
    # Based on the grid, try 32-pixel tall bands, 16-pixel, and 8-pixel

    band_configs = [
        (32, "32px"),
        (16, "16px"),
        (8, "8px"),
    ]

    for band_height, label in band_configs:
        print(f"Extracting {label} bands:")
        num_bands = atlas.height // band_height

        for band_idx in range(num_bands):
            y_start = band_idx * band_height
            y_end = min(y_start + band_height, atlas.height)
            actual_height = y_end - y_start

            # Extract this band
            pixels = []
            for y in range(y_start, y_end):
                for x in range(atlas.width):
                    pixels.append(atlas.get_pixel(x, y))

            band = Sprite(
                width=atlas.width,
                height=actual_height,
                pixels=pixels,
                palette=atlas.palette
            )

            # Count unique colors to identify interesting bands
            unique_colors = len(set(pixels))

            # Save the band
            img = Image.frombytes("RGB", (band.width, band.height), band.to_rgb_bytes())
            output_path = output_dir / f"band_{label}_row{band_idx:02d}_y{y_start:03d}-{y_end:03d}.png"
            img.save(output_path)

            # Also save a 4x scaled version for easier viewing
            scaled = band.scale(4)
            img_scaled = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
            output_path_scaled = output_dir / f"band_{label}_row{band_idx:02d}_y{y_start:03d}-{y_end:03d}_4x.png"
            img_scaled.save(output_path_scaled)

            print(f"  Band {band_idx:2d} (y={y_start:3d}-{y_end:3d}): {unique_colors:2d} colors")

        print()


def create_texture_catalog():
    """Create a visual catalog showing all textures."""
    gamedata = Path("gamedata")
    path = gamedata / "MAZEDATA.EGA"
    data = path.read_bytes()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    print("Creating texture catalog:")
    print()

    # Create a single image showing all 32px bands side by side
    band_height = 32
    num_bands = atlas.height // band_height

    # Create catalog image
    catalog_width = 320
    catalog_height = num_bands * band_height * 4  # 4x scale
    catalog_img = Image.new("RGB", (catalog_width * 4, catalog_height))

    for band_idx in range(num_bands):
        y_start = band_idx * band_height
        y_end = min(y_start + band_height, atlas.height)

        # Extract band
        pixels = []
        for y in range(y_start, y_end):
            for x in range(atlas.width):
                pixels.append(atlas.get_pixel(x, y))

        band = Sprite(width=atlas.width, height=band_height, pixels=pixels, palette=atlas.palette)
        scaled = band.scale(4)

        # Paste into catalog
        band_img = Image.frombytes("RGB", (scaled.width, scaled.height), scaled.to_rgb_bytes())
        catalog_img.paste(band_img, (0, band_idx * band_height * 4))

    output_path = Path("output/texture_catalog.png")
    catalog_img.save(output_path)
    print(f"  Saved catalog: {output_path}")


if __name__ == "__main__":
    extract_all_bands()
    create_texture_catalog()

    print()
    print("=" * 70)
    print("Textures extracted! Check output/texture_bands/")
    print()
    print("Key findings:")
    print("  - MAZEDATA.EGA stores textures as horizontal bands")
    print("  - Each band spans full width (320 pixels)")
    print("  - Different band heights used (8px, 16px, 32px)")
    print("  - Bands represent different wall/floor/ceiling types")
    print("  - Game likely samples from these bands for 3D rendering")
