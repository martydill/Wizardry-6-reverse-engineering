"""Test linear 2-bit decoding for MAZEDATA.EGA."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def test_2bit():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        return

    data = path.read_bytes()
    image_data = data[767:]
    
    # Map 2-bit values to EGA grays: 0, 8, 7, 15
    # Let's try: 00->0, 01->8, 10->7, 11->15
    gray_map = [0, 8, 7, 15]
    
    width = 320
    # 2 bits per pixel means 4 pixels per byte
    # 320 pixels = 80 bytes
    
    height = len(image_data) // 80
    if height > 200: height = 200 # Only do first image
    
    pixels = []
    for i in range(width * height // 4):
        b = image_data[i]
        # Try MSB first: bits 7-6, 5-4, 3-2, 1-0
        pixels.append(gray_map[(b >> 6) & 3])
        pixels.append(gray_map[(b >> 4) & 3])
        pixels.append(gray_map[(b >> 2) & 3])
        pixels.append(gray_map[b & 3])
        
    sprite = Sprite(width, height, pixels, DEFAULT_16_PALETTE)
    img = Image.frombytes("RGB", (width, height), sprite.to_rgb_bytes())
    img.save("output/mazedata_linear_2bit.png")
    print(f"Saved 2-bit linear test to output/mazedata_linear_2bit.png")

if __name__ == "__main__":
    test_2bit()
