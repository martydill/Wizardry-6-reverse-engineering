"""Try combining: Sequential planar WITH color palette, THEN transpose.

Maybe we had the right orientation (transposed) but wrong palette (grayscale)?
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


def sprite_to_image(sprite):
    """Convert sprite to image."""
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


def try_color_transposed():
    """Try sequential planar with DEFAULT_16_PALETTE, then transpose."""
    print("Sequential Planar + Color Palette + Transpose")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    # Load data
    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    output_dir = Path("color_transposed_tests")
    output_dir.mkdir(exist_ok=True)

    # Decode as sequential planar with DEFAULT COLOR PALETTE
    print("Decoding 320x200 with DEFAULT_16_PALETTE...")
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    atlas = decoder.decode_planar(data[:32000], width=320, height=200, msb_first=True)

    # Save original
    img = sprite_to_image(atlas)
    if HAS_PIL:
        img.save(output_dir / "1_original_320x200_color.png")
        scaled = img.resize((960, 600), Image.NEAREST)
        scaled.save(output_dir / "1_original_320x200_color_3x.png")
    else:
        pygame.image.save(img, str(output_dir / "1_original_320x200_color.png"))
        scaled = pygame.transform.scale(img, (960, 600))
        pygame.image.save(scaled, str(output_dir / "1_original_320x200_color_3x.png"))

    print(f"  Saved: 1_original_320x200_color.png")

    # Transpose
    print("Transposing to 200x320...")
    transposed = transpose_sprite(atlas)

    img_t = sprite_to_image(transposed)
    if HAS_PIL:
        img_t.save(output_dir / "2_transposed_200x320_color.png")
        scaled = img_t.resize((400, 640), Image.NEAREST)
        scaled.save(output_dir / "2_transposed_200x320_color_2x.png")
        scaled = img_t.resize((600, 960), Image.NEAREST)
        scaled.save(output_dir / "2_transposed_200x320_color_3x.png")
    else:
        pygame.image.save(img_t, str(output_dir / "2_transposed_200x320_color.png"))
        scaled = pygame.transform.scale(img_t, (600, 960))
        pygame.image.save(scaled, str(output_dir / "2_transposed_200x320_color_3x.png"))

    print(f"  Saved: 2_transposed_200x320_color.png")

    # Extract some vertical columns
    print("\nExtracting vertical texture columns (32 pixels wide)...")

    for col_idx in range(min(6, transposed.width // 32)):
        x_start = col_idx * 32
        x_end = x_start + 32

        col_pixels = []
        for y in range(transposed.height):
            for x in range(x_start, x_end):
                col_pixels.append(transposed.get_pixel(x, y))

        col_sprite = Sprite(
            width=32,
            height=transposed.height,
            pixels=col_pixels,
            palette=transposed.palette
        )

        col_img = sprite_to_image(col_sprite)
        if HAS_PIL:
            scaled = col_img.resize((128, transposed.height * 4), Image.NEAREST)
            scaled.save(output_dir / f"column_{col_idx}_color_4x.png")
        else:
            scaled = pygame.transform.scale(col_img, (128, transposed.height * 4))
            pygame.image.save(scaled, str(output_dir / f"column_{col_idx}_color_4x.png"))

        print(f"  Column {col_idx}: column_{col_idx}_color_4x.png")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("Tests complete! Check color_transposed_tests/")
    print("=" * 70)


if __name__ == "__main__":
    try_color_transposed()
