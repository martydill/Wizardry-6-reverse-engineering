
import sys
from pathlib import Path
from PIL import Image

# Add parent directory to path to import bane modules
sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, TITLEPAG_PALETTE, Sprite

def decode_and_save(data, offset, width, height, palette, order, filename):
    decoder = EGADecoder(palette=palette)
    
    # EGA usually rounds up width to multiple of 8 for planar packing
    decode_width = ((width + 7) // 8) * 8
    
    required_bytes = (decode_width * height) // 2
    tile_data = data[offset : offset + required_bytes]
    
    if len(tile_data) < required_bytes:
        print(f"Warning: tile data too short for {filename}")
        tile_data = tile_data + b"\x00" * (required_bytes - len(tile_data))
        
    sprite = decoder.decode_planar(tile_data, decode_width, height, plane_order=order)
    
    # Create image and crop to actual width
    img = Image.frombytes("RGB", (decode_width, height), sprite.to_rgb_bytes())
    if decode_width != width:
        img = img.crop((0, 0, width, height))
    
    # Scale up for better visibility
    scale = 4
    if width < 32 or height < 32:
        scale = 8
    
    scaled = img.resize((width * scale, height * scale), Image.NEAREST)
    scaled.save(filename)
    return sprite

def test():
    path = Path("gamedata/MAZEDATA.EGA")
    data = path.read_bytes()
    
    # Data starts at 0x2A00 according to one doc, or maybe elsewhere?
    # In extract_all_tile_descriptors.py, it used 0x2A00.
    DATA_REGION_START = 0x2A00
    tile_data_region = data[DATA_REGION_START:]
    
    output_dir = Path("test_tiles")
    output_dir.mkdir(exist_ok=True)
    
    # Use TITLEPAG_PALETTE and order [3, 0, 2, 1]
    palette = TITLEPAG_PALETTE
    order = [3, 0, 2, 1]
    
    # Try a few descriptors from the 4-byte records
    # [ 16] @ meta 0x0040: offset=0x0385, dims= 32x 32
    decode_and_save(tile_data_region, 0x0385, 32, 32, palette, order, output_dir / "tile16_v3params.png")
    
    # [ 24] @ meta 0x0060: offset=0x0208, dims=156x108
    decode_and_save(tile_data_region, 0x0208, 156, 108, palette, order, output_dir / "tile24_v3params.png")
    
    # Also try order [0, 1, 2, 3] to compare
    decode_and_save(tile_data_region, 0x0385, 32, 32, palette, [0, 1, 2, 3], output_dir / "tile16_defaultorder.png")
    
    print(f"Test tiles saved to {output_dir}")

if __name__ == "__main__":
    test()
