"""Extract wall textures from MAZEDATA.EGA using potential index and TitlePag palette (v4)."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, TITLEPAG_PALETTE, Sprite

def extract():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    image_data = data[767:]
    
    output_dir = Path("output/mazedata_v4")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    decoder = EGADecoder(palette=TITLEPAG_PALETTE)
    # Try order [0, 1, 2, 3] this time
    order = [0, 1, 2, 3]
    
    tile_size = 2048
    num_tiles = len(image_data) // tile_size
    
    print(f"Extracting {num_tiles} tiles of 64x64 (order 0123)...")
    for i in range(num_tiles):
        tile_data = image_data[i * tile_size : (i + 1) * tile_size]
        sprite = decoder.decode_planar(tile_data, 64, 64, plane_order=order)
        if any(p != 0 for p in sprite.pixels):
            img = Image.frombytes("RGB", (64, 64), sprite.to_rgb_bytes())
            img.save(output_dir / f"wall_64x64_{i:03d}.png")

if __name__ == "__main__":
    extract()
