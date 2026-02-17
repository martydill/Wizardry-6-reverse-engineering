"""Extract wall textures from MAZEDATA.EGA using potential index and TitlePag palette."""

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
    
    # Try skipping the index
    image_data = data[767:]
    
    output_dir = Path("output/mazedata_v3")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use TITLEPAG_PALETTE with standard plane order (confirmed correct for Wiz6 EGA)
    decoder = EGADecoder(palette=TITLEPAG_PALETTE)
    order = [0, 1, 2, 3]
    
    # Extract as 64x64 tiles
    tile_size = 2048 # 64x64x4/8
    num_tiles = len(image_data) // tile_size
    
    print(f"Extracting {num_tiles} tiles of 64x64...")
    for i in range(num_tiles):
        tile_data = image_data[i * tile_size : (i + 1) * tile_size]
        sprite = decoder.decode_planar(
            tile_data, 
            width=64, 
            height=64, 
            plane_order=order
        )
        
        # Check if tile is empty
        if all(p == 0 for p in sprite.pixels):
            continue
            
        img = Image.frombytes("RGB", (64, 64), sprite.to_rgb_bytes())
        img.save(output_dir / f"wall_64x64_{i:03d}.png")

    # Also try 32x32 tiles
    tile_size_32 = 512
    num_tiles_32 = len(image_data) // tile_size_32
    print(f"Extracting {num_tiles_32} tiles of 32x32...")
    for i in range(num_tiles_32):
        tile_data = image_data[i * tile_size_32 : (i + 1) * tile_size_32]
        sprite = decoder.decode_planar(
            tile_data, 
            width=32, 
            height=32, 
            plane_order=order
        )
        
        if all(p == 0 for p in sprite.pixels):
            continue
            
        img = Image.frombytes("RGB", (32, 32), sprite.to_rgb_bytes())
        img.save(output_dir / f"tile_32x32_{i:03d}.png")

if __name__ == "__main__":
    extract()
