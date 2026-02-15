"""Decode EGA files accounting for 768-byte palette header."""

from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def decode_ega_file(filename):
    """Decode an EGA file with 768-byte palette header."""
    path = Path("gamedata") / filename
    data = path.read_bytes()

    print(f"\n{filename}:")
    print(f"  File size: {len(data)} bytes")

    # Extract palette from first 768 bytes
    palette = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)  # VGA palette is 0-63, scale to 0-252
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette.append((r, g, b))

    print(f"  Custom palette extracted: {len(palette)} colors")

    decoder = EGADecoder(palette=palette)

    # Decode from byte 768 onward
    image_data = data[768:]
    width, height = 320, 200

    # Try row-interleaved
    sprite = decoder.decode_planar_row_interleaved(
        image_data,
        width=width,
        height=height
    )

    img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
    output_path = Path(f"output/{filename.lower()}_correct.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)

    print(f"  Saved: {output_path.name}")
    return sprite


def decode_mazedata():
    """Decode MAZEDATA.EGA with palette header."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print(f"\nMAZEDATA.EGA:")
    print(f"  File size: {len(data)} bytes")

    # Extract palette
    palette = []
    for i in range(16):
        r = data[i * 3] * 4
        g = data[i * 3 + 1] * 4
        b = data[i * 3 + 2] * 4
        palette.append((r, g, b))

    print(f"  Palette: {palette}")

    decoder = EGADecoder(palette=palette)

    # Try decoding from byte 768
    image_data = data[768:]
    print(f"  Image data size: {len(image_data)} bytes")

    # For 320x200, we need 32,000 bytes
    sprite = decoder.decode_planar_row_interleaved(
        image_data[:32000],
        width=320,
        height=200
    )

    img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
    output_path = Path("output/mazedata_with_palette.png")
    img.save(output_path)

    print(f"  Saved: {output_path.name}")

    # What about the remaining data?
    remaining = image_data[32000:]
    print(f"  Remaining after first image: {len(remaining)} bytes")


if __name__ == "__main__":
    # Test on known files first
    decode_ega_file("TITLEPAG.EGA")
    decode_ega_file("DRAGONSC.EGA")
    decode_ega_file("GRAVEYRD.EGA")

    # Now try MAZEDATA
    decode_mazedata()
