"""Try decoding MAZEDATA.EGA as a full-screen texture atlas."""

import struct
from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def decode_as_fullscreen():
    """Try decoding as a 320x200 row-interleaved planar image (texture atlas)."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print("Attempting to decode MAZEDATA.EGA as texture atlas")
    print("=" * 70)
    print()

    # Try different starting offsets
    for skip in [0, 1, 2, 4, 8, 16, 31, 32, 64, 128, 256, 512, 767, 920]:
        print(f"\nTrying with {skip}-byte header...")

        payload = data[skip:]

        # Full EGA screen: 320x200, row-interleaved planar
        # 320/8 = 40 bytes per plane per row
        # 40 * 4 planes = 160 bytes per scanline
        # 160 * 200 = 32000 bytes total

        width = 320
        height = 200
        expected_size = 32000

        if len(payload) < expected_size:
            print(f"  Payload too small: {len(payload)} bytes (need {expected_size})")
            continue

        decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

        try:
            sprite = decoder.decode_planar_row_interleaved(
                payload[:expected_size],
                width,
                height
            )

            # Save output
            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/mazedata_atlas_skip{skip}.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            print(f"  SUCCESS! Saved to {output_path}")

        except Exception as e:
            print(f"  Failed: {e}")


def try_different_dimensions():
    """Try other common dimensions."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print("\n" + "=" * 70)
    print("Trying different dimensions...")
    print()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # The file is 102,303 bytes
    # After subtracting potential headers, what dimensions work?

    test_cases = [
        (0, 320, 200),    # Full screen
        (2, 320, 200),    # 2-byte header
        (767, 320, 200),  # After 5-byte * 153 index
        (0, 256, 200),    # Narrower
        (0, 320, 160),    # Shorter
        (0, 256, 256),    # Square-ish
    ]

    for skip, width, height in test_cases:
        bytes_per_row = width // 8
        row_size = bytes_per_row * 4  # 4 planes
        expected_size = row_size * height
        payload = data[skip:]

        if len(payload) < expected_size:
            continue

        try:
            sprite = decoder.decode_planar_row_interleaved(
                payload[:expected_size],
                width,
                height
            )

            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/mazedata_{width}x{height}_skip{skip}.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            print(f"  {width}x{height} skip={skip}: SUCCESS! -> {output_path.name}")

        except:
            pass


def check_if_planar_sequential():
    """Try as sequential planar (plane0 all, plane1 all, plane2 all, plane3 all)."""
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print("\n" + "=" * 70)
    print("Trying sequential planar format...")
    print()

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    for skip in [0, 2, 767]:
        payload = data[skip:]

        # For 320x200: each plane is 320*200/8 = 8000 bytes
        # Total: 32000 bytes
        width = 320
        height = 200
        expected_size = 32000

        if len(payload) < expected_size:
            continue

        try:
            sprite = decoder.decode_planar(
                payload[:expected_size],
                width,
                height
            )

            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/mazedata_sequential_planar_skip{skip}.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            print(f"  Skip={skip}: SUCCESS! -> {output_path.name}")

        except Exception as e:
            print(f"  Skip={skip}: Failed - {e}")


if __name__ == "__main__":
    decode_as_fullscreen()
    try_different_dimensions()
    check_if_planar_sequential()
