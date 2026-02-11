"""Extract individual wall textures from MAZEDATA.EGA."""

import os
import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def extract_tiles(sprite, tile_w, tile_h, output_dir):
    """Extract all tiles of a given size from a sprite."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rows = sprite.height // tile_h
    cols = sprite.width // tile_w
    
    print(f"Extracting {cols}x{rows} tiles of size {tile_w}x{tile_h}...")
    
    count = 0
    for r in range(rows):
        for c in range(cols):
            x = c * tile_w
            y = r * tile_h
            
            # Extract pixels
            pixels = []
            for ty in range(tile_h):
                for tx in range(tile_w):
                    pixels.append(sprite.get_pixel(x + tx, y + ty))
            
            # Create sub-sprite
            tile = Sprite(width=tile_w, height=tile_h, pixels=pixels, palette=sprite.palette)
            
            # Check if tile is empty (all black/color 0)
            if all(p == 0 for p in pixels):
                continue
                
            # Save tile
            img = Image.frombytes("RGB", (tile.width, tile.height), tile.to_rgb_bytes())
            img.save(output_dir / f"tile_{tile_w}x{tile_h}_{r}_{c}.png")
            count += 1
            
    print(f"Saved {count} non-empty tiles to {output_dir}")

def main():
    path = Path("gamedata/MAZEDATA.EGA")
    if not path.exists():
        print(f"File not found: {path}")
        return

    data = path.read_bytes()
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    
    output_base = Path("output/mazedata_extracted")
    output_base.mkdir(parents=True, exist_ok=True)

    # 1. Extract from the main 320x200 atlas (first 32,000 bytes)
    print("Processing main atlas (0-32000)...")
    atlas = decoder.decode_planar(data[:32000], width=320, height=200)
    
    # Try 64x64
    extract_tiles(atlas, 64, 64, output_base / "64x64")
    # Try 32x32
    extract_tiles(atlas, 32, 32, output_base / "32x32")
    # Try 40x40 (sometimes used for distant walls)
    extract_tiles(atlas, 40, 40, output_base / "40x40")

    # 2. Try to decode the next two 320x200 blocks
    for i in range(1, 3):
        start = i * 32000
        end = start + 32000
        if end <= len(data):
            print(f"Processing atlas {i} ({start}-{end})...")
            atlas_n = decoder.decode_planar(data[start:end], width=320, height=200)
            
            # Save the full atlas too
            img = Image.frombytes("RGB", (atlas_n.width, atlas_n.height), atlas_n.to_rgb_bytes())
            img.save(output_base / f"atlas_{i}.png")
            
            extract_tiles(atlas_n, 64, 64, output_base / f"atlas{i}_64x64")
            extract_tiles(atlas_n, 32, 32, output_base / f"atlas{i}_32x32")

    # 3. Check for leftover data
    leftover_start = 3 * 32000
    if leftover_start < len(data):
        leftover = data[leftover_start:]
        print(f"Leftover data: {len(leftover)} bytes at end")
        # Could be smaller tiles or 8x8 tiled format
        # Try decoding as 320 width with whatever height
        height = len(leftover) * 8 // (320 * 4)
        if height > 0:
            print(f"Decoding leftover as 320x{height} sequential planar...")
            try:
                atlas_left = decoder.decode_planar(leftover, width=320, height=height)
                img = Image.frombytes("RGB", (atlas_left.width, atlas_left.height), atlas_left.to_rgb_bytes())
                img.save(output_base / "leftover_planar.png")
            except Exception as e:
                print(f"Failed to decode leftover as planar: {e}")

if __name__ == "__main__":
    main()
