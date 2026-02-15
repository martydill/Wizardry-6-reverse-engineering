"""Try different orientations of the MAZEDATA texture data.

The data might be stored column-major, transposed, or rotated.
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


def create_grayscale_palette():
    """Create 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def sprite_to_image(sprite):
    """Convert sprite to image."""
    if HAS_PIL:
        img = Image.new('RGB', (sprite.width, sprite.height))
        pixels = []
        for y in range(sprite.height):
            for x in range(sprite.width):
                intensity = sprite.get_pixel(x, y)
                if 0 <= intensity < len(sprite.palette):
                    pixels.append(sprite.palette[intensity])
                else:
                    pixels.append((0, 0, 0))
        img.putdata(pixels)
        return img
    else:
        surf = pygame.Surface((sprite.width, sprite.height))
        for y in range(sprite.height):
            for x in range(sprite.width):
                intensity = sprite.get_pixel(x, y)
                if 0 <= intensity < len(sprite.palette):
                    surf.set_at((x, y), sprite.palette[intensity])
        return surf


def transpose_sprite(sprite: Sprite) -> Sprite:
    """Transpose sprite (swap rows and columns)."""
    new_pixels = []
    for x in range(sprite.width):
        for y in range(sprite.height):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.height,
        height=sprite.width,
        pixels=new_pixels,
        palette=sprite.palette
    )


def flip_horizontal(sprite: Sprite) -> Sprite:
    """Flip sprite horizontally."""
    new_pixels = []
    for y in range(sprite.height):
        for x in range(sprite.width - 1, -1, -1):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.width,
        height=sprite.height,
        pixels=new_pixels,
        palette=sprite.palette
    )


def flip_vertical(sprite: Sprite) -> Sprite:
    """Flip sprite vertically."""
    new_pixels = []
    for y in range(sprite.height - 1, -1, -1):
        for x in range(sprite.width):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.width,
        height=sprite.height,
        pixels=new_pixels,
        palette=sprite.palette
    )


def rotate_90_cw(sprite: Sprite) -> Sprite:
    """Rotate sprite 90 degrees clockwise."""
    new_pixels = []
    for x in range(sprite.width - 1, -1, -1):
        for y in range(sprite.height):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.height,
        height=sprite.width,
        pixels=new_pixels,
        palette=sprite.palette
    )


def rotate_90_ccw(sprite: Sprite) -> Sprite:
    """Rotate sprite 90 degrees counter-clockwise."""
    new_pixels = []
    for x in range(sprite.width):
        for y in range(sprite.height - 1, -1, -1):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.height,
        height=sprite.width,
        pixels=new_pixels,
        palette=sprite.palette
    )


def rotate_180(sprite: Sprite) -> Sprite:
    """Rotate sprite 180 degrees."""
    new_pixels = []
    for y in range(sprite.height - 1, -1, -1):
        for x in range(sprite.width - 1, -1, -1):
            new_pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.width,
        height=sprite.height,
        pixels=new_pixels,
        palette=sprite.palette
    )


def try_all_orientations():
    """Try all possible orientations of the texture data."""
    print("Trying Different Texture Orientations")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    # Decode as grayscale
    grayscale_palette = create_grayscale_palette()
    decoder = EGADecoder(palette=grayscale_palette)

    # Original 320x200
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    output_dir = Path("orientation_tests")
    output_dir.mkdir(exist_ok=True)

    # Test different orientations
    tests = [
        (atlas, "1_Original_320x200"),
        (transpose_sprite(atlas), "2_Transposed_200x320"),
        (flip_horizontal(atlas), "3_FlipHorizontal_320x200"),
        (flip_vertical(atlas), "4_FlipVertical_320x200"),
        (rotate_90_cw(atlas), "5_Rotate90CW_200x320"),
        (rotate_90_ccw(atlas), "6_Rotate90CCW_200x320"),
        (rotate_180(atlas), "7_Rotate180_320x200"),
    ]

    # Also try decoding with swapped dimensions
    atlas_swapped = decoder.decode_planar(data[:32000], width=200, height=320, msb_first=True)
    tests.append((atlas_swapped, "8_Swapped_Dimensions_200x320"))

    for sprite, name in tests:
        print(f"\nTesting: {name}")
        print(f"  Dimensions: {sprite.width}x{sprite.height}")

        img = sprite_to_image(sprite)

        # Save original size
        filename = output_dir / f"{name}.png"
        if HAS_PIL:
            img.save(filename)
        else:
            pygame.image.save(img, str(filename))
        print(f"  Saved: {filename}")

        # Save 2x scaled
        if HAS_PIL:
            scaled = img.resize((sprite.width * 2, sprite.height * 2), Image.NEAREST)
            scaled.save(output_dir / f"{name}_2x.png")
        else:
            scaled = pygame.transform.scale(img, (sprite.width * 2, sprite.height * 2))
            pygame.image.save(scaled, str(output_dir / f"{name}_2x.png"))
        print(f"  Saved 2x: {name}_2x.png")

    # Also try extracting a texture band from each orientation
    print("\n" + "=" * 70)
    print("Extracting Band 4 (y=128-160) from each orientation:")
    print("-" * 70)

    for sprite, name in tests[:7]:  # Skip swapped dimensions for bands
        # Extract band 4 region
        if sprite.height >= 160:
            y_start, y_end = 128, 160
        else:
            # For transposed/rotated, adjust
            y_start, y_end = sprite.height // 2, min(sprite.height, sprite.height // 2 + 32)

        band_pixels = []
        for y in range(y_start, min(y_end, sprite.height)):
            for x in range(sprite.width):
                band_pixels.append(sprite.get_pixel(x, y))

        band = Sprite(
            width=sprite.width,
            height=min(y_end - y_start, sprite.height - y_start),
            pixels=band_pixels,
            palette=sprite.palette
        )

        band_img = sprite_to_image(band)

        # Scale up 4x for visibility
        if HAS_PIL:
            scaled = band_img.resize((band.width * 4, band.height * 4), Image.NEAREST)
            band_file = output_dir / f"{name}_band4_4x.png"
            scaled.save(band_file)
        else:
            scaled = pygame.transform.scale(band_img, (band.width * 4, band.height * 4))
            band_file = output_dir / f"{name}_band4_4x.png"
            pygame.image.save(scaled, str(band_file))

        print(f"  {name}: {band_file.name}")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("Orientation tests complete!")
    print("Check orientation_tests/ directory")
    print("Look for the version that shows clear brick/stone patterns!")
    print("=" * 70)


if __name__ == "__main__":
    try_all_orientations()
