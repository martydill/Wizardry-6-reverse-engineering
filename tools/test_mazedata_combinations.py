"""Test different gray mappings for MAZEDATA tiles."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def test_mappings():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    # Skip index, pick a known wall tile (e.g. tile 0,0)
    # 64x64 4-bit = 2048 bytes
    tile_data = data[767 : 767+2048]
    
    pixels = []
    for b in tile_data:
        pixels.append(b >> 4)
        pixels.append(b & 0x0F)
        
    output_dir = Path("output/mazedata_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping 1: Default EGA (The one the user said has too much color)
    save_tile(pixels, DEFAULT_16_PALETTE, output_dir / "default_ega.png")
    
    # Mapping 2: Pure Grayscale ramp (Linear)
    gray_ramp = []
    for i in range(16):
        v = int(i * 255 / 15)
        gray_ramp.append((v, v, v))
    save_tile(pixels, gray_ramp, output_dir / "linear_gray_ramp.png")
    
    # Mapping 3: Only 4 grays (0, 8, 7, 15) based on bit count
    map3 = []
    grays = [ (0,0,0), (85,85,85), (170,170,170), (255,255,255) ]
    for i in range(16):
        # count bits
        bits = bin(i).count('1')
        if bits == 0: v = grays[0]
        elif bits == 1: v = grays[1]
        elif bits <= 3: v = grays[2]
        else: v = grays[3]
        map3.append(v)
    save_tile(pixels, map3, output_dir / "bitcount_gray.png")

    # Mapping 4: Titlepag grays for 0-3, black for rest
    map4 = [ (0,0,0), (84,84,84), (168,168,168), (252,252,252) ] + [(0,0,0)]*12
    save_tile(pixels, map4, output_dir / "titlepag_limited.png")

def save_tile(pixels, palette, path):
    sprite = Sprite(64, 64, pixels, palette)
    img = Image.frombytes("RGB", (64, 64), sprite.to_rgb_bytes())
    img.save(path)
    print(f"Saved {path.name}")

if __name__ == "__main__":
    test_mappings()
