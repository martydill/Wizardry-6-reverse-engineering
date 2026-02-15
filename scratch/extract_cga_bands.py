"""Extract and analyze individual texture bands from MAZEDATA.CGA.

The CGA version shows clearer horizontal banding than EGA.
Let's extract these bands and see what they contain.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


CGA_PALETTE_1_LOW = [
    (0, 0, 0),       # 0: Black
    (0, 170, 0),     # 1: Green
    (170, 0, 0),     # 2: Red
    (170, 170, 0),   # 3: Brown/Yellow
]


def decode_cga_linear(data: bytes, width: int, height: int, palette: list):
    """Decode CGA data as linear format."""
    if HAS_PIL:
        img = Image.new('RGB', (width, height))
        pixels = []

        byte_idx = 0
        for y in range(height):
            for x in range(0, width, 4):
                if byte_idx >= len(data):
                    pixels.extend([palette[0]] * 4)
                    continue

                byte_val = data[byte_idx]
                byte_idx += 1

                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    pixels.append(palette[pixel])

        img.putdata(pixels)
        return img
    else:
        surf = pygame.Surface((width, height))

        byte_idx = 0
        for y in range(height):
            for x in range(0, width, 4):
                if byte_idx >= len(data):
                    break

                byte_val = data[byte_idx]
                byte_idx += 1

                for i in range(4):
                    shift = 6 - (i * 2)
                    pixel = (byte_val >> shift) & 0x03
                    surf.set_at((x + i, y), palette[pixel])

        return surf


def extract_band(img, y_start: int, band_height: int):
    """Extract a horizontal band from the image."""
    width = img.width if HAS_PIL else img.get_width()

    if HAS_PIL:
        return img.crop((0, y_start, width, y_start + band_height))
    else:
        band = pygame.Surface((width, band_height))
        band.blit(img, (0, -y_start))
        return band


def analyze_bands():
    """Extract and save texture bands from MAZEDATA.CGA."""
    print("Extracting Texture Bands from MAZEDATA.CGA")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    path = Path("gamedata") / "MAZEDATA.CGA"
    data = path.read_bytes()

    # Decode full image
    print("Decoding 320x200 linear CGA image...")
    img = decode_cga_linear(data, 320, 200, CGA_PALETTE_1_LOW)

    output_dir = Path("cga_bands")
    output_dir.mkdir(exist_ok=True)

    # Try different band heights
    for band_height in [16, 20, 25, 32, 40, 50]:
        print(f"\nExtracting {band_height}-pixel bands:")
        print("-" * 70)

        num_bands = 200 // band_height
        band_dir = output_dir / f"bands_{band_height}px"
        band_dir.mkdir(exist_ok=True)

        for band_idx in range(num_bands):
            y_start = band_idx * band_height

            band_img = extract_band(img, y_start, band_height)

            # Scale up 4x for visibility
            if HAS_PIL:
                scaled = band_img.resize((320 * 2, band_height * 4), Image.NEAREST)
                filename = band_dir / f"band_{band_idx:02d}_y{y_start:03d}.png"
                scaled.save(filename)
            else:
                scaled = pygame.transform.scale(band_img, (320 * 2, band_height * 4))
                filename = band_dir / f"band_{band_idx:02d}_y{y_start:03d}.png"
                pygame.image.save(scaled, str(filename))

            print(f"  Band {band_idx} (y={y_start:3d}-{y_start+band_height:3d}): {filename.name}")

        # Create overview showing all bands
        if HAS_PIL:
            overview = Image.new('RGB', (320 * 2, num_bands * band_height * 2))

            for band_idx in range(num_bands):
                y_start = band_idx * band_height
                band_img = extract_band(img, y_start, band_height)
                scaled = band_img.resize((320 * 2, band_height * 2), Image.NEAREST)
                overview.paste(scaled, (0, band_idx * band_height * 2))

                # Add label
                draw = ImageDraw.Draw(overview)
                label = f"Band {band_idx}"
                draw.text((5, band_idx * band_height * 2 + 2), label, fill=(255, 255, 255))

            overview_file = band_dir / "overview.png"
            overview.save(overview_file)
            print(f"  Overview: {overview_file}")

        else:
            overview = pygame.Surface((320 * 2, num_bands * band_height * 2))

            for band_idx in range(num_bands):
                y_start = band_idx * band_height
                band_img = extract_band(img, y_start, band_height)
                scaled = pygame.transform.scale(band_img, (320 * 2, band_height * 2))
                overview.blit(scaled, (0, band_idx * band_height * 2))

                # Add label
                font = pygame.font.Font(None, 20)
                label = font.render(f"Band {band_idx}", True, (255, 255, 255))
                overview.blit(label, (5, band_idx * band_height * 2 + 2))

            overview_file = band_dir / "overview.png"
            pygame.image.save(overview, str(overview_file))
            print(f"  Overview: {overview_file}")

    # Also save the full decoded image at different scales
    print("\n" + "=" * 70)
    print("Saving full decoded image:")
    print("-" * 70)

    if HAS_PIL:
        img.save(output_dir / "full_320x200.png")
        scaled = img.resize((640, 400), Image.NEAREST)
        scaled.save(output_dir / "full_640x400.png")
        scaled = img.resize((960, 600), Image.NEAREST)
        scaled.save(output_dir / "full_960x600.png")
    else:
        pygame.image.save(img, str(output_dir / "full_320x200.png"))
        scaled = pygame.transform.scale(img, (640, 400))
        pygame.image.save(scaled, str(output_dir / "full_640x400.png"))
        scaled = pygame.transform.scale(img, (960, 600))
        pygame.image.save(scaled, str(output_dir / "full_960x600.png"))

    print(f"  full_320x200.png (original)")
    print(f"  full_640x400.png (2x)")
    print(f"  full_960x600.png (3x)")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print(f"All bands saved to: {output_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    analyze_bands()
