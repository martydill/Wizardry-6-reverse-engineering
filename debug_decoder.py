"""Debug the EGA decoder by testing with known patterns and TITLEPAG."""

from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def test_simple_pattern():
    """Test with a simple known pattern."""
    print("Testing with simple pattern...")
    print()

    # Create a simple 8x2 pattern (8 pixels wide, 2 pixels tall)
    # In row-interleaved planar:
    # Row 0: plane0 (1 byte), plane1 (1 byte), plane2 (1 byte), plane3 (1 byte)
    # Row 1: plane0 (1 byte), plane1 (1 byte), plane2 (1 byte), plane3 (1 byte)

    # Let's make a pattern: pixels 0-7 with values 0,1,2,3,4,5,6,7 on first row
    # For pixel value N, we need bits set in planes according to binary of N

    # Pixel 0 = 0b0000 → all planes 0
    # Pixel 1 = 0b0001 → plane0=1
    # Pixel 2 = 0b0010 → plane1=1
    # Pixel 3 = 0b0011 → plane0=1, plane1=1
    # Pixel 4 = 0b0100 → plane2=1
    # Pixel 5 = 0b0101 → plane0=1, plane2=1
    # Pixel 6 = 0b0110 → plane1=1, plane2=1
    # Pixel 7 = 0b0111 → plane0=1, plane1=1, plane2=1

    # For MSB-first, leftmost pixel is bit 7, rightmost is bit 0
    # So byte layout for each plane should have bits in reverse

    # Plane 0: pixels with bit 0 set: 1,3,5,7 → positions 1,3,5,7 → bits 6,4,2,0 → 0b01010101 = 0x55
    # Plane 1: pixels with bit 1 set: 2,3,6,7 → positions 2,3,6,7 → bits 5,4,1,0 → 0b00110011 = 0x33
    # Plane 2: pixels with bit 2 set: 4,5,6,7 → positions 4,5,6,7 → bits 3,2,1,0 → 0b00001111 = 0x0F
    # Plane 3: all 0

    # Row 0 data (4 bytes)
    row0 = bytes([0x55, 0x33, 0x0F, 0x00])
    # Row 1 data (4 bytes) - all white (15)
    row1 = bytes([0xFF, 0xFF, 0xFF, 0xFF])

    test_data = row0 + row1

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Try MSB-first
    print("Decoding with msb_first=True...")
    sprite = decoder.decode_planar_row_interleaved(test_data, width=8, height=2, msb_first=True)
    print(f"  Row 0: {sprite.pixels[:8]}")
    print(f"  Row 1: {sprite.pixels[8:16]}")
    print(f"  Expected row 0: [0, 1, 2, 3, 4, 5, 6, 7]")
    print(f"  Expected row 1: [15, 15, 15, 15, 15, 15, 15, 15]")
    print()

    # Try LSB-first
    print("Decoding with msb_first=False...")
    sprite = decoder.decode_planar_row_interleaved(test_data, width=8, height=2, msb_first=False)
    print(f"  Row 0: {sprite.pixels[:8]}")
    print(f"  Row 1: {sprite.pixels[8:16]}")
    print()


def try_titlepag_variations():
    """Try different decoder settings on TITLEPAG."""
    path = Path("gamedata/TITLEPAG.EGA")
    data = path.read_bytes()

    # Extract palette
    palette = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette.append((r, g, b))

    image_data = data[768:]

    decoder = EGADecoder(palette=palette)

    variations = [
        ("MSB-first, order [0,1,2,3]", True, [0, 1, 2, 3]),
        ("LSB-first, order [0,1,2,3]", False, [0, 1, 2, 3]),
        ("MSB-first, order [3,2,1,0]", True, [3, 2, 1, 0]),
        ("LSB-first, order [3,2,1,0]", False, [3, 2, 1, 0]),
    ]

    for name, msb, order in variations:
        print(f"\nTrying: {name}")
        sprite = decoder.decode_planar_row_interleaved(
            image_data,
            width=320,
            height=200,
            msb_first=msb,
            plane_order=order
        )

        img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
        safe_name = name.replace(" ", "_").replace(",", "").replace("[", "").replace("]", "")
        output_path = Path(f"output/titlepag_{safe_name}.png")
        img.save(output_path)
        print(f"  Saved: {output_path.name}")


if __name__ == "__main__":
    test_simple_pattern()
    print("="*70)
    try_titlepag_variations()
