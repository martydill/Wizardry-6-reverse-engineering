"""Batch analyze all texture decoding combinations and save comparison images.

This script tries every combination of:
- Plane orders
- Bit orders (MSB/LSB)
- Palettes
- Band heights
- Data sources (main 32KB vs extra 70KB)

Saves a grid of all combinations for visual comparison.
"""

import sys
from pathlib import Path
from typing import List, Tuple
import struct

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

# Try importing PIL for image creation
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("PIL not available, will use pygame")
    import pygame


def load_mazedata() -> bytes:
    """Load MAZEDATA.EGA file."""
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        sys.exit(1)
    return path.read_bytes()


def load_titlepag_palette() -> List[Tuple[int, int, int]]:
    """Load palette from TITLEPAG.EGA."""
    path = Path("gamedata") / "TITLEPAG.EGA"
    if not path.exists():
        return DEFAULT_16_PALETTE

    data = path.read_bytes()
    palette = []
    for i in range(256):
        r = data[i * 3] << 2
        g = data[i * 3 + 1] << 2
        b = data[i * 3 + 2] << 2
        palette.append((r, g, b))
    return palette[:16]


def decode_with_config(
    data: bytes,
    width: int,
    height: int,
    plane_order: List[int],
    msb_first: bool,
    palette: List[Tuple[int, int, int]]
) -> Sprite:
    """Decode data with specific configuration."""
    decoder = EGADecoder(palette=palette)
    return decoder.decode_planar(
        data,
        width=width,
        height=height,
        planes=4,
        msb_first=msb_first,
        plane_order=plane_order
    )


def extract_band(sprite: Sprite, y_start: int, band_height: int) -> Sprite:
    """Extract a horizontal band from the sprite."""
    y_end = min(y_start + band_height, sprite.height)
    actual_height = y_end - y_start

    pixels = []
    for y in range(y_start, y_end):
        for x in range(sprite.width):
            pixels.append(sprite.get_pixel(x, y))

    return Sprite(
        width=sprite.width,
        height=actual_height,
        pixels=pixels,
        palette=sprite.palette
    )


def sprite_to_pil_image(sprite: Sprite) -> Image.Image:
    """Convert Sprite to PIL Image."""
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


def sprite_to_pygame_surface(sprite: Sprite) -> 'pygame.Surface':
    """Convert Sprite to pygame Surface."""
    surf = pygame.Surface((sprite.width, sprite.height))

    for y in range(sprite.height):
        for x in range(sprite.width):
            color_idx = sprite.get_pixel(x, y)
            if 0 <= color_idx < len(sprite.palette):
                surf.set_at((x, y), sprite.palette[color_idx])

    return surf


def create_labeled_image(image, label: str, label_height: int = 20):
    """Add a text label above an image."""
    if HAS_PIL:
        from PIL import ImageDraw, ImageFont

        # Create new image with space for label
        new_img = Image.new('RGB', (image.width, image.height + label_height), (40, 40, 40))

        # Draw label
        draw = ImageDraw.Draw(new_img)
        # Use default font
        draw.text((5, 2), label, fill=(255, 255, 255))

        # Paste original image below label
        new_img.paste(image, (0, label_height))

        return new_img
    else:
        # pygame version
        new_surf = pygame.Surface((image.get_width(), image.get_height() + label_height))
        new_surf.fill((40, 40, 40))

        font = pygame.font.Font(None, 16)
        text = font.render(label, True, (255, 255, 255))
        new_surf.blit(text, (5, 2))
        new_surf.blit(image, (0, label_height))

        return new_surf


def analyze_all_combinations():
    """Try all decoding combinations and save comparison grid."""
    print("Batch Texture Analysis")
    print("=" * 60)

    if not HAS_PIL:
        pygame.init()

    # Load data
    mazedata = load_mazedata()
    titlepag_palette = load_titlepag_palette()

    # Configuration options
    plane_orders = [
        ([0, 1, 2, 3], "0123"),
        ([3, 2, 1, 0], "3210"),
        ([0, 2, 1, 3], "0213"),
        ([1, 0, 2, 3], "1023"),
    ]

    bit_orders = [
        (True, "MSB"),
        (False, "LSB"),
    ]

    palettes = [
        (DEFAULT_16_PALETTE, "Default"),
        (titlepag_palette, "TitlePag"),
    ]

    data_sources = [
        (mazedata[:32000], "Main32K"),
        (mazedata[32000:32000+32000] if len(mazedata) > 64000 else mazedata[:32000], "Extra70K"),
    ]

    band_heights = [32]  # Focus on 32px bands for now

    print(f"\nTesting {len(plane_orders)} plane orders")
    print(f"Testing {len(bit_orders)} bit orders")
    print(f"Testing {len(palettes)} palettes")
    print(f"Testing {len(data_sources)} data sources")
    print(f"Band height: {band_heights[0]}px")
    print(f"\nTotal combinations: {len(plane_orders) * len(bit_orders) * len(palettes) * len(data_sources)}")

    # Extract first band (0-32px) with different configs
    results = []

    for data, data_name in data_sources:
        for palette, pal_name in palettes:
            for plane_order, plane_name in plane_orders:
                for msb_first, bit_name in bit_orders:
                    # Decode full image
                    try:
                        sprite = decode_with_config(
                            data,
                            width=320,
                            height=200,
                            plane_order=plane_order,
                            msb_first=msb_first,
                            palette=palette
                        )

                        # Extract first band
                        band = extract_band(sprite, 0, 32)

                        # Scale up for visibility
                        scaled_width = 320
                        scaled_height = 96  # 32 * 3

                        if HAS_PIL:
                            img = sprite_to_pil_image(band)
                            img = img.resize((scaled_width, scaled_height), Image.NEAREST)
                        else:
                            surf = sprite_to_pygame_surface(band)
                            img = pygame.transform.scale(surf, (scaled_width, scaled_height))

                        label = f"{data_name} {pal_name} P:{plane_name} {bit_name}"
                        labeled = create_labeled_image(img, label)

                        results.append((label, labeled))
                        print(f"[OK] {label}")

                    except Exception as e:
                        print(f"[FAIL] {data_name} {pal_name} {plane_name} {bit_name}: {e}")

    print(f"\nSuccessfully decoded {len(results)} combinations")

    # Create grid of results
    if len(results) > 0:
        cols = 4
        rows = (len(results) + cols - 1) // cols

        if HAS_PIL:
            # Calculate grid dimensions
            cell_width = results[0][1].width
            cell_height = results[0][1].height

            grid = Image.new('RGB', (cell_width * cols, cell_height * rows), (20, 20, 20))

            for idx, (label, img) in enumerate(results):
                x = (idx % cols) * cell_width
                y = (idx // cols) * cell_height
                grid.paste(img, (x, y))

            output_path = Path("texture_combinations_grid.png")
            grid.save(output_path)
            print(f"\nSaved grid to: {output_path}")

        else:
            # pygame version
            cell_width = results[0][1].get_width()
            cell_height = results[0][1].get_height()

            grid = pygame.Surface((cell_width * cols, cell_height * rows))
            grid.fill((20, 20, 20))

            for idx, (label, surf) in enumerate(results):
                x = (idx % cols) * cell_width
                y = (idx // cols) * cell_height
                grid.blit(surf, (x, y))

            output_path = Path("texture_combinations_grid.png")
            pygame.image.save(grid, str(output_path))
            print(f"\nSaved grid to: {output_path}")

    # Also save individual band images for closer inspection
    print("\nSaving individual band images...")
    output_dir = Path("texture_analysis")
    output_dir.mkdir(exist_ok=True)

    for label, img in results:
        safe_label = label.replace(" ", "_").replace(":", "")
        filename = output_dir / f"band_{safe_label}.png"

        if HAS_PIL:
            img.save(filename)
        else:
            pygame.image.save(img, str(filename))

    print(f"Saved {len(results)} individual images to {output_dir}/")

    if not HAS_PIL:
        pygame.quit()


def analyze_raw_data_patterns():
    """Analyze raw byte patterns in the data."""
    print("\n" + "=" * 60)
    print("Raw Data Pattern Analysis")
    print("=" * 60)

    mazedata = load_mazedata()

    # Analyze first 32KB (main atlas)
    main_data = mazedata[:32000]

    print(f"\nFirst 32KB Analysis:")
    print(f"  Total bytes: {len(main_data)}")
    print(f"  Expected for 320x200: {320 * 200 // 8 * 4} bytes (8000 per plane)")

    # Check for repeating patterns
    print(f"\nFirst 64 bytes (hex):")
    hex_lines = []
    for i in range(0, min(64, len(main_data)), 16):
        hex_bytes = " ".join(f"{b:02X}" for b in main_data[i:i+16])
        hex_lines.append(f"  {i:04X}: {hex_bytes}")
    print("\n".join(hex_lines))

    # Byte value distribution
    byte_counts = [0] * 256
    for b in main_data[:8000]:  # First plane
        byte_counts[b] += 1

    print(f"\nFirst plane byte distribution:")
    non_zero = [(i, count) for i, count in enumerate(byte_counts) if count > 0]
    print(f"  Unique byte values: {len(non_zero)}")
    print(f"  Most common bytes:")
    for val, count in sorted(non_zero, key=lambda x: x[1], reverse=True)[:10]:
        print(f"    0x{val:02X}: {count:5d} times ({count*100/8000:.1f}%)")

    # Check if data might be compressed or encoded differently
    print(f"\nData characteristics:")
    zeros = sum(1 for b in main_data[:8000] if b == 0)
    ones = sum(1 for b in main_data[:8000] if b == 0xFF)
    print(f"  Zeros: {zeros} ({zeros*100/8000:.1f}%)")
    print(f"  0xFF: {ones} ({ones*100/8000:.1f}%)")

    # Check plane boundaries
    print(f"\nPlane boundaries (if sequential planar):")
    for plane in range(4):
        offset = plane * 8000
        if offset < len(main_data):
            print(f"  Plane {plane} start (offset {offset}): {' '.join(f'{b:02X}' for b in main_data[offset:offset+16])}")


if __name__ == "__main__":
    analyze_all_combinations()
    analyze_raw_data_patterns()

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("Review the generated images to find which combination")
    print("produces textures that look like brick walls.")
    print("=" * 60)
