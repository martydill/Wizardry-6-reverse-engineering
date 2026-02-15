"""Try nibble-swapping and tiling on the first large tile."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def test_swapped():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    sample = data[767 : 767 + 2048]
    
    gray_ramp = [(int(i * 255 / 15), int(i * 255 / 15), int(i * 255 / 15)) for i in range(16)]
    
    output_dir = Path("output/mazedata_test_swapped")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Nibble Swap (Low nibble first)
    pixels1 = []
    for b in sample:
        pixels1.append(b & 0x0F)
        pixels1.append(b >> 4)
    s1 = Sprite(64, 64, pixels1, gray_ramp)
    img1 = Image.frombytes("RGB", (64, 64), s1.to_rgb_bytes())
    img1.save(output_dir / "nibble_swap.png")
    
    # 2. Tiled Linear (8x8 tiles)
    pixels2 = [0] * (64 * 64)
    for ty in range(8):
        for tx in range(8):
            tile_idx = ty * 8 + tx
            tile_base = tile_idx * 32
            tile_data = sample[tile_base : tile_base + 32]
            tp = []
            for b in tile_data:
                tp.append(b >> 4)
                tp.append(b & 0x0F)
            for y in range(8):
                for x in range(8):
                    pixels2[(ty*8 + y)*64 + (tx*8 + x)] = tp[y*8 + x]
    s2 = Sprite(64, 64, pixels2, gray_ramp)
    img2 = Image.frombytes("RGB", (64, 64), s2.to_rgb_bytes())
    img2.save(output_dir / "tiled_8x8.png")

    # 3. Tiled Linear (8x8 tiles) + Column Major tiles
    pixels3 = [0] * (64 * 64)
    for tx in range(8): # swap order
        for ty in range(8):
            tile_idx = tx * 8 + ty
            tile_base = tile_idx * 32
            tile_data = sample[tile_base : tile_base + 32]
            tp = []
            for b in tile_data:
                tp.append(b >> 4)
                tp.append(b & 0x0F)
            for y in range(8):
                for x in range(8):
                    pixels3[(ty*8 + y)*64 + (tx*8 + x)] = tp[y*8 + x]
    s3 = Sprite(64, 64, pixels3, gray_ramp)
    img3 = Image.frombytes("RGB", (64, 64), s3.to_rgb_bytes())
    img3.save(output_dir / "tiled_8x8_col_major.png")

    print(f"Saved more swapped tests to {output_dir}")

if __name__ == "__main__":
    test_swapped()
