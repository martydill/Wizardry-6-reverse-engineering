"""Try sequential planar format (each plane stored consecutively)."""

from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def decode_sequential_planes(data, w, h, palette, msb_first=True):
    """Decode sequential planar data (plane0 all, plane1 all, plane2 all, plane3 all)."""
    pixels = [0] * (w * h)
    bytes_per_row = w // 8
    bytes_per_plane = bytes_per_row * h  # For 320x200: 40 * 200 = 8000

    for plane in range(4):
        plane_offset = plane * bytes_per_plane
        for y in range(h):
            row_offset = plane_offset + y * bytes_per_row
            for byte_idx in range(bytes_per_row):
                byte_val = data[row_offset + byte_idx]
                for bit in range(8):
                    if msb_first:
                        x = byte_idx * 8 + (7 - bit)
                    else:
                        x = byte_idx * 8 + bit
                    if byte_val & (1 << bit):
                        pixels[y * w + x] |= (1 << plane)

    return Sprite(w, h, pixels, palette)


def test_titlepag():
    """Test TITLEPAG.EGA with sequential planar decoding."""
    path = Path("gamedata/TITLEPAG.EGA")
    data = path.read_bytes()

    print(f"TITLEPAG.EGA: {len(data)} bytes")

    # Extract palette
    palette = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette.append((r, g, b))

    image_data = data[768:]  # Skip 768-byte palette
    print(f"Image data: {len(image_data)} bytes")
    print(f"Expected for 320x200: {320*200//8*4} bytes")

    # Try sequential planar
    sprite = decode_sequential_planes(image_data, 320, 200, palette, msb_first=True)

    img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
    output_path = Path("output/titlepag_sequential_correct.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)

    print(f"Saved: {output_path.name}")


def test_mazedata():
    """Test MAZEDATA.EGA - no palette header!"""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print(f"\nMAZEDATA.EGA: {len(data)} bytes")

    # No palette header for MAZEDATA - use default EGA palette
    palette = DEFAULT_16_PALETTE

    # Try from byte 0
    sprite = decode_sequential_planes(data, 320, 200, palette, msb_first=True)

    img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
    output_path = Path("output/mazedata_sequential_nopal.png")
    img.save(output_path)

    print(f"Saved: {output_path.name}")

    # What about the remaining data?
    used = 320 * 200 // 8 * 4
    remaining = len(data) - used
    print(f"Remaining data: {remaining} bytes")


if __name__ == "__main__":
    test_titlepag()
    test_mazedata()
