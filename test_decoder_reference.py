"""Test our EGA decoder on known-good files to verify it works."""

from pathlib import Path
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).parent / "bane"))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def test_reference_files():
    """Test decoder on TITLEPAG, DRAGONSC, GRAVEYRD - these should work."""

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    test_files = [
        ("TITLEPAG.EGA", 32768),
        ("DRAGONSC.EGA", 32768),
        ("GRAVEYRD.EGA", 32768),
    ]

    for filename, expected_size in test_files:
        path = Path("gamedata") / filename
        if not path.exists():
            print(f"Skipping {filename} (not found)")
            continue

        data = path.read_bytes()
        print(f"\n{filename}:")
        print(f"  File size: {len(data)} bytes (expected {expected_size})")

        # Try row-interleaved
        try:
            sprite = decoder.decode_planar_row_interleaved(
                data[:32000],
                width=320,
                height=200
            )

            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/{filename.lower()}_row_interleaved.png")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path)

            print(f"  Row-interleaved: SUCCESS -> {output_path.name}")
        except Exception as e:
            print(f"  Row-interleaved: FAILED - {e}")

        # Try sequential planar
        try:
            sprite = decoder.decode_planar(
                data[:32000],
                width=320,
                height=200
            )

            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/{filename.lower()}_sequential.png")
            img.save(output_path)

            print(f"  Sequential planar: SUCCESS -> {output_path.name}")
        except Exception as e:
            print(f"  Sequential planar: FAILED - {e}")

    print("\n" + "="*70)
    print("Now testing MAZEDATA.EGA with both methods...")
    print()

    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()

    print(f"MAZEDATA.EGA size: {len(data)} bytes")

    # Test different interpretations
    tests = [
        ("Row-interleaved, first 32KB", data[:32000], 320, 200, "row_interleaved"),
        ("Sequential planar, first 32KB", data[:32000], 320, 200, "sequential"),
        ("Row-interleaved, skip 2 bytes", data[2:32002], 320, 200, "row_skip2"),
        ("Sequential planar, skip 2 bytes", data[2:32002], 320, 200, "seq_skip2"),
    ]

    for name, test_data, width, height, suffix in tests:
        try:
            if "interleaved" in suffix:
                sprite = decoder.decode_planar_row_interleaved(test_data, width, height)
            else:
                sprite = decoder.decode_planar(test_data, width, height)

            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            output_path = Path(f"output/mazedata_test_{suffix}.png")
            img.save(output_path)

            print(f"  {name}: SUCCESS -> {output_path.name}")
        except Exception as e:
            print(f"  {name}: FAILED - {e}")

if __name__ == "__main__":
    test_reference_files()
