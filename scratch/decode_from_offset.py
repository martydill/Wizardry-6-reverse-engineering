"""Try decoding MAZEDATA.EGA from different offsets.

Based on structure analysis, the file might have:
- Header/index section (0x0000-0x0EE9)
- Null padding (0x0EE9-0x1931)
- Actual texture data (0x1931+)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    import pygame


def decode_from_offset(data: bytes, offset: int, width: int, height: int, palette):
    """Decode planar data starting from offset."""
    decoder = EGADecoder(palette=palette)

    # Calculate required bytes for sequential planar
    required_bytes = width * height // 8 * 4

    if offset + required_bytes > len(data):
        print(f"  Warning: Not enough data from offset {offset}")
        print(f"  Required: {required_bytes}, Available: {len(data) - offset}")
        return None

    sprite = decoder.decode_planar(
        data[offset:offset + required_bytes],
        width=width,
        height=height,
        msb_first=True
    )

    return sprite


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


def main():
    print("Decoding MAZEDATA.EGA from Different Offsets")
    print("=" * 70)

    if not HAS_PIL:
        pygame.init()

    path = Path("gamedata") / "MAZEDATA.EGA"
    data = path.read_bytes()

    print(f"File size: {len(data):,} bytes")
    print()

    # Try different starting offsets
    test_offsets = [
        (0x0000, "File start"),
        (0x0099, "After first word (153 bytes)"),
        (0x0AF9, "After first small null seq"),
        (0x0EE9, "Start of big null seq"),
        (0x18F8, "End of big null seq"),
        (0x1931, "After big null seq (next data)"),
        (0x7D00, "32KB mark"),
        (0x9000, "36KB mark"),
    ]

    output_dir = Path("offset_tests")
    output_dir.mkdir(exist_ok=True)

    for offset, description in test_offsets:
        print(f"\nTesting offset 0x{offset:04X} ({offset}) - {description}")
        print("-" * 70)

        # Try 320x200 (standard)
        sprite = decode_from_offset(data, offset, 320, 200, DEFAULT_16_PALETTE)

        if sprite:
            print(f"  Decoded 320x200 successfully")

            img = sprite_to_image(sprite)

            safe_name = description.replace(" ", "_").replace("(", "").replace(")", "")
            filename = output_dir / f"offset_{offset:04X}_{safe_name}.png"

            if HAS_PIL:
                img.save(filename)
            else:
                pygame.image.save(img, str(filename))

            print(f"  Saved: {filename}")

        # Also try smaller dimensions that might fit
        for width, height in [(320, 100), (160, 200), (256, 128)]:
            required = width * height // 8 * 4
            if offset + required <= len(data):
                sprite = decode_from_offset(data, offset, width, height, DEFAULT_16_PALETTE)
                if sprite:
                    img = sprite_to_image(sprite)
                    safe_name = description.replace(" ", "_").replace("(", "").replace(")", "")
                    filename = output_dir / f"offset_{offset:04X}_{safe_name}_{width}x{height}.png"

                    if HAS_PIL:
                        img.save(filename)
                    else:
                        pygame.image.save(img, str(filename))

                    print(f"  Also saved {width}x{height}: {filename.name}")

    if not HAS_PIL:
        pygame.quit()

    print("\n" + "=" * 70)
    print("Offset testing complete!")
    print(f"Check {output_dir}/ for results")
    print("=" * 70)


if __name__ == "__main__":
    main()
