"""Extract wall textures from MAZEDATA.EGA forcing grays."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def extract_forced_gray():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    image_data = data[767:]
    
    # Map all 16 indices to the "closest" gray in default EGA
    # This is a bit arbitrary, but let's try to map by "intensity" (number of bits set)
    # or just force everything to the 4 grays.
    gray_map = {
        0: 0,   # Black
        1: 8,   # Blue -> Dark Gray
        2: 8,   # Green -> Dark Gray
        3: 7,   # Cyan -> Light Gray
        4: 8,   # Red -> Dark Gray
        5: 7,   # Magenta -> Light Gray
        6: 8,   # Brown -> Dark Gray
        7: 7,   # Light Gray
        8: 8,   # Dark Gray
        9: 7,   # Light Blue -> Light Gray
        10: 7,  # Light Green -> Light Gray
        11: 15, # Light Cyan -> White
        12: 7,  # Light Red -> Light Gray
        13: 15, # Light Magenta -> White
        14: 15, # Yellow -> White
        15: 15, # White
    }
    
    output_dir = Path("output/mazedata_forced_gray")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pixels = []
    for b in image_data[:32000]:
        pixels.append(gray_map[b >> 4])
        pixels.append(gray_map[b & 0x0F])
        
    width = 320
    height = 200
    
    atlas = Sprite(width, height, pixels, DEFAULT_16_PALETTE)
    img = Image.frombytes("RGB", (width, height), atlas.to_rgb_bytes())
    img.save(output_dir / "forced_gray_atlas.png")
    
    # Extract 64x64 tiles
    extract_from_atlas(atlas, 64, 64, output_dir / "64x64")

def extract_from_atlas(atlas: Sprite, tile_w: int, tile_h: int, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    cols = atlas.width // tile_w
    rows = atlas.height // tile_h
    count = 0
    for r in range(rows):
        for c in range(cols):
            x = c * tile_w
            y = r * tile_h
            pixels = []
            is_empty = True
            for ty in range(tile_h):
                for tx in range(tile_w):
                    px = atlas.get_pixel(x + tx, y + ty)
                    pixels.append(px)
                    if px != 0: is_empty = False
            
            if is_empty: continue
            
            tile = Sprite(tile_w, tile_h, pixels, atlas.palette)
            img = Image.frombytes("RGB", (tile_w, tile_h), tile.to_rgb_bytes())
            img.save(target_dir / f"tile_{r}_{c}.png")
            count += 1
    print(f"  Extracted {count} {tile_w}x{tile_h} tiles to {target_dir.name}")

if __name__ == "__main__":
    extract_forced_gray()
