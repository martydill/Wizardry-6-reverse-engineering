"""Decode MAZEDATA.EGA as 4-bit grayscale textures.

BREAKTHROUGH: The 4-bit values represent grayscale intensities (0-15),
not color palette indices! This is how texture mapping worked in 1990.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, Sprite

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def create_grayscale_palette() -> list[tuple[int, int, int]]:
    """Create a 16-level grayscale palette.

    Maps 4-bit values (0-15) to grayscale RGB values.
    0 = black (0, 0, 0)
    15 = white (255, 255, 255)
    """
    palette = []
    for i in range(16):
        # Linear interpolation from 0 to 255
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_as_grayscale():
    """Decode MAZEDATA.EGA as grayscale textures."""
    print("MAZEDATA.EGA Grayscale Decoding")
    print("=" * 70)
    print("Treating 4-bit values as grayscale intensities (0-15)")
    print()

    if not HAS_PIL:
        pygame.init()

    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()

    # Create grayscale palette
    grayscale_palette = create_grayscale_palette()

    # Decode as sequential planar with grayscale palette
    decoder = EGADecoder(palette=grayscale_palette)
    atlas = decoder.decode_planar(
        data[:32000],
        width=320,
        height=200,
        msb_first=True
    )

    print(f"Decoded: {atlas.width}x{atlas.height}")
    print(f"Palette: 16-level grayscale (0=black, 15=white)")
    print()

    # Convert to image
    if HAS_PIL:
        img = Image.new('RGB', (atlas.width, atlas.height))
        pixels = []

        for y in range(atlas.height):
            for x in range(atlas.width):
                intensity = atlas.get_pixel(x, y)
                if 0 <= intensity < len(atlas.palette):
                    pixels.append(atlas.palette[intensity])
                else:
                    pixels.append((0, 0, 0))

        img.putdata(pixels)

        # Save at different scales
        output_dir = Path("grayscale_output")
        output_dir.mkdir(exist_ok=True)

        img.save(output_dir / "mazedata_grayscale_320x200.png")
        print(f"Saved: grayscale_output/mazedata_grayscale_320x200.png")

        # 2x scale
        scaled = img.resize((640, 400), Image.NEAREST)
        scaled.save(output_dir / "mazedata_grayscale_640x400.png")
        print(f"Saved: grayscale_output/mazedata_grayscale_640x400.png")

        # 3x scale
        scaled = img.resize((960, 600), Image.NEAREST)
        scaled.save(output_dir / "mazedata_grayscale_960x600.png")
        print(f"Saved: grayscale_output/mazedata_grayscale_960x600.png")

        # Extract individual bands
        print()
        print("Extracting texture bands:")
        print("-" * 70)

        band_configs = [
            (0, 32, "Band_0_Floor_Wall"),
            (32, 64, "Band_1_Wall_Patterns"),
            (64, 96, "Band_2_Complex"),
            (96, 128, "Band_3_Varied"),
            (128, 160, "Band_4_Clear_Tiles"),
            (160, 200, "Band_5_Ceiling"),
        ]

        for y_start, y_end, name in band_configs:
            band_img = img.crop((0, y_start, 320, y_end))

            # Scale up 4x for visibility
            band_scaled = band_img.resize((1280, (y_end - y_start) * 4), Image.NEAREST)

            filename = output_dir / f"{name}_y{y_start}-{y_end}.png"
            band_scaled.save(filename)
            print(f"  {name}: {filename.name}")

        # Create annotated overview
        print()
        print("Creating annotated overview...")

        overview = Image.new('RGB', (960 + 400, 600), (20, 20, 20))
        overview.paste(scaled, (0, 0))

        # Add annotations
        from PIL import ImageDraw

        draw = ImageDraw.Draw(overview)

        # Draw band separators
        for i, (y_start, y_end, name) in enumerate(band_configs):
            y_line = y_end * 3  # 3x scale
            draw.line([(0, y_line), (960, y_line)], fill=(255, 255, 0), width=2)
            draw.text((5, y_start * 3 + 5), str(i), fill=(255, 255, 255))

        # Add title and notes
        draw.text((10, 575), "MAZEDATA.EGA - GRAYSCALE TEXTURES", fill=(255, 255, 255))
        draw.text((970, 20), "GRAYSCALE DECODING:", fill=(100, 255, 100))
        draw.text((970, 45), "4-bit values = intensity (0-15)", fill=(220, 220, 220))
        draw.text((970, 65), "0 = Black, 15 = White", fill=(220, 220, 220))
        draw.text((970, 90), "", fill=(220, 220, 220))
        draw.text((970, 110), "This is the correct format!", fill=(100, 255, 100))
        draw.text((970, 135), "Game colorizes at runtime", fill=(220, 220, 220))

        overview.save(output_dir / "grayscale_overview_annotated.png")
        print(f"Saved: grayscale_output/grayscale_overview_annotated.png")

    else:
        # Pygame version
        surf = pygame.Surface((atlas.width, atlas.height))

        for y in range(atlas.height):
            for x in range(atlas.width):
                intensity = atlas.get_pixel(x, y)
                if 0 <= intensity < len(atlas.palette):
                    surf.set_at((x, y), atlas.palette[intensity])

        output_dir = Path("grayscale_output")
        output_dir.mkdir(exist_ok=True)

        pygame.image.save(surf, str(output_dir / "mazedata_grayscale_320x200.png"))
        print(f"Saved: grayscale_output/mazedata_grayscale_320x200.png")

        scaled = pygame.transform.scale(surf, (960, 600))
        pygame.image.save(scaled, str(output_dir / "mazedata_grayscale_960x600.png"))
        print(f"Saved: grayscale_output/mazedata_grayscale_960x600.png")

        pygame.quit()

    print()
    print("=" * 70)
    print("Grayscale decoding complete!")
    print("Check grayscale_output/ for results")
    print("=" * 70)


if __name__ == "__main__":
    decode_as_grayscale()
