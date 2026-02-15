"""Test tiled planar decoding for MAZEDATA.EGA."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, TITLEPAG_PALETTE, Sprite

def test_tiled():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    # Skip the potential index (767 bytes)
    image_data = data[767:]
    
    output_dir = Path("output/mazedata_tiled")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    decoder = EGADecoder(palette=TITLEPAG_PALETTE)
    
    # Try different widths for tiled decoding
    for width in [64, 128, 320]:
        height = 64
        try:
            print(f"Testing tiled planar {width}x{height}...")
            sprite = decoder.decode_tiled_planar(
                image_data,
                width=width,
                height=height
            )
            
            img = Image.frombytes("RGB", (sprite.width, sprite.height), sprite.to_rgb_bytes())
            img.save(output_dir / f"tiled_{width}x{height}.png")
        except Exception as e:
            print(f"Failed {width}x{height}: {e}")

if __name__ == "__main__":
    test_tiled()
