"""Extract wall textures from MAZEDATA.EGA using a linear gray ramp."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import Sprite

def extract_linear_gray():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    # Skip index
    image_data = data[767:]
    
    # Create a 16-color linear gray ramp palette
    gray_ramp = []
    for i in range(16):
        v = int(i * 255 / 15)
        gray_ramp.append((v, v, v))
        
    output_dir = Path("output/mazedata_extracted_v2")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process the three main atlases
    for atlas_idx in range(3):
        start = atlas_idx * 32000
        end = start + 32000
        if end > len(image_data):
            break
            
        print(f"Decoding atlas {atlas_idx} as linear 4-bit gray ramp...")
        chunk = image_data[start:end]
        pixels = []
        for b in chunk:
            pixels.append(b >> 4)
            pixels.append(b & 0x0F)
            
        atlas = Sprite(320, 200, pixels, gray_ramp)
        
        # Save full atlas
        img = Image.frombytes("RGB", (320, 200), atlas.to_rgb_bytes())
        img.save(output_dir / f"atlas_{atlas_idx}_gray.png")
        
        # Extract 64x64 tiles
        extract_from_atlas(atlas, 64, 64, output_dir / f"atlas_{atlas_idx}_64x64")
        
        # Extract 32x32 tiles
        extract_from_atlas(atlas, 32, 32, output_dir / f"atlas_{atlas_idx}_32x32")

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
    extract_linear_gray()
