"""Test linear 4-bit decoding for MAZEDATA.EGA."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def test_linear():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    # Skip potential index
    image_data = data[767:]
    
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    
    # Try 320x200 linear
    print("Testing 320x200 linear 4-bit...")
    # 320*200 pixels = 64000 pixels = 32000 bytes
    sprite = decoder.decode_linear(image_data[:32000], 320, 200)
    
    img = Image.frombytes("RGB", (320, 200), sprite.to_rgb_bytes())
    output_path = Path("output/mazedata_linear_320x200.png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)
    
    # Count grays
    gray_indices = {0, 7, 8, 15}
    gray_count = sum(1 for p in sprite.pixels if p in gray_indices)
    print(f"  Grays (0,7,8,15): {gray_count} ({gray_count/(320*200)*100:.1f}%)")

if __name__ == "__main__":
    test_linear()
