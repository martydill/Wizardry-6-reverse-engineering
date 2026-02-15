"""Extract individual wall textures from MAZEDATA.EGA using the default 16-color EGA palette."""

import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite

def extract_wall_textures(input_path: Path, output_dir: Path):
    """Extract all 64x64 and 32x32 textures from MAZEDATA.EGA."""
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    data = input_path.read_bytes()
    
    # Use DEFAULT_16_PALETTE as requested
    decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
    
    # plane_order verified by previous testing
    order = [0, 2, 3, 1]

    for atlas_idx in range(3):
        start = atlas_idx * 32000
        end = start + 32000
        if end > len(data):
            break

        print(f"Decoding atlas {atlas_idx} (offset {start})...")
        atlas_data = data[start:end]
        
        atlas = decoder.decode_planar(
            atlas_data,
            width=320,
            height=200,
            msb_first=True,
            plane_order=order
        )

        # 1. Extract 64x64 tiles
        extract_from_atlas(atlas, 64, 64, output_dir / f"atlas_{atlas_idx}_64x64")
        
        # 2. Extract 32x32 tiles
        extract_from_atlas(atlas, 32, 32, output_dir / f"atlas_{atlas_idx}_32x32")

    # Handle leftover data
    leftover_start = 3 * 32000
    if leftover_start < len(data):
        leftover = data[leftover_start:]
        print(f"Processing {len(leftover)} bytes of leftover data...")
        extract_8x8_tiles(leftover, output_dir / "leftover_8x8", decoder, order)

def extract_from_atlas(atlas: Sprite, tile_w: int, tile_h: int, target_dir: Path):
    """Extract tiles of specified size from a decoded atlas."""
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
                    if px != 0:
                        is_empty = False
            
            if is_empty:
                continue

            tile = Sprite(
                width=tile_w,
                height=tile_h,
                pixels=pixels,
                palette=atlas.palette
            )
            
            img = Image.frombytes("RGB", (tile.width, tile.height), tile.to_rgb_bytes())
            filename = f"tile_{atlas.width}x{atlas.height}_{r}_{c}.png"
            img.save(target_dir / filename)
            count += 1
            
    print(f"  Extracted {count} non-empty {tile_w}x{tile_h} tiles to {target_dir.name}")

def extract_8x8_tiles(data: bytes, target_dir: Path, decoder: EGADecoder, order: list[int]):
    """Extract 8x8 planar tiles from raw data."""
    target_dir.mkdir(parents=True, exist_ok=True)
    
    tile_size = 32
    num_tiles = len(data) // tile_size
    
    count = 0
    for i in range(num_tiles):
        tile_data = data[i * tile_size : (i + 1) * tile_size]
        tile = decoder.decode_planar(tile_data, width=8, height=8, plane_order=order)
        
        if any(p != 0 for p in tile.pixels):
            img = Image.frombytes("RGB", (tile.width, tile.height), tile.to_rgb_bytes())
            img.save(target_dir / f"tile_8x8_{i:03d}.png")
            count += 1
            
    print(f"  Extracted {count} non-empty 8x8 tiles to {target_dir.name}")

if __name__ == "__main__":
    input_file = Path("gamedata/MAZEDATA.EGA")
    output_path = Path("output/mazedata_default_ega")
    extract_wall_textures(input_file, output_path)
