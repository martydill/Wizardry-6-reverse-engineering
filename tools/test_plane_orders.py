"""Test different plane orders to find the correct MAZEDATA.EGA format."""

import sys
from pathlib import Path
from PIL import Image
from itertools import permutations

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

def test_orders():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    image_data = data[767:]

    output_dir = Path("output/mazedata_plane_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)

    # Test common plane orders
    test_orders = [
        ([0, 1, 2, 3], "0123_normal"),
        ([3, 2, 1, 0], "3210_reversed"),
        ([3, 0, 2, 1], "3021_v3"),
        ([0, 2, 1, 3], "0213_swap12"),
        ([1, 0, 2, 3], "1023_swap01"),
        ([2, 1, 0, 3], "2103"),
    ]

    # Extract a 64x64 tile with each order
    tile_size = 2048
    tile_data = image_data[0:tile_size]

    for order, name in test_orders:
        try:
            sprite = decoder.decode_planar(
                tile_data,
                width=64,
                height=64,
                plane_order=order
            )

            img = Image.frombytes("RGB", (64, 64), sprite.to_rgb_bytes())
            img = img.resize((128, 128), Image.NEAREST)
            img.save(output_dir / f"tile_order_{name}.png")
            print(f"Created tile with order {order} -> {name}")
        except Exception as e:
            print(f"Failed with order {order}: {e}")

    # Also test with a smaller width for atlas
    print("\nTesting atlas with different widths...")
    for width in [160, 320, 640]:
        plane_size = len(image_data) // 4
        height = min((plane_size * 8) // width, 200)  # Cap at reasonable height
        bytes_needed = (width * height * 4) // 8

        if bytes_needed > len(image_data):
            continue

        for order, name in test_orders[:3]:  # Test top 3 orders
            try:
                atlas = decoder.decode_planar(
                    image_data[:bytes_needed],
                    width=width,
                    height=height,
                    plane_order=order
                )

                img = Image.frombytes("RGB", (width, height), atlas.to_rgb_bytes())
                img.save(output_dir / f"atlas_{width}x{height}_{name}.png")
                print(f"Created atlas {width}x{height} with order {name}")
            except Exception as e:
                print(f"Failed atlas {width}x{height} with {name}: {e}")

    print(f"\nSaved test images to {output_dir}")

if __name__ == "__main__":
    test_orders()
