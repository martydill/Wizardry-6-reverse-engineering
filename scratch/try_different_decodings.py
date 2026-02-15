"""Try different decoding methods for MAZEDATA.EGA.

Based on the project's analysis, MAZEDATA.EGA has been successfully decoded,
but let's try different approaches to see if we can get more recognizable patterns.
"""

import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, EGA_64_PALETTE

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow not found. Install with 'pip install Pillow' for image saving.")


def create_grayscale_palette() -> List[Tuple[int, int, int]]:
    """Create a 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def try_sequential_planar_decodings(data: bytes, output_dir: Path):
    """Try different sequential planar decodings."""
    print("Trying sequential planar decodings...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Different plane orders that might work
    plane_orders = [
        [0, 1, 2, 3],  # Standard order
        [3, 2, 1, 0],  # Reverse order
        [3, 0, 2, 1],  # Found to work for some EGA files
        [1, 0, 3, 2],  # Another permutation
        [2, 3, 0, 1],  # Another permutation
    ]
    
    width, height = 320, 200
    bytes_needed = width * height // 2  # 4 bits per pixel
    
    if len(data) < bytes_needed:
        print(f"Not enough data for {width}x{height} image, have {len(data)} bytes")
        return
    
    for i, plane_order in enumerate(plane_orders):
        try:
            decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
            sprite = decoder.decode_planar(
                data[:bytes_needed],
                width=width,
                height=height,
                msb_first=True,
                plane_order=plane_order
            )
            
            # Create image
            img = Image.new('RGB', (sprite.width, sprite.height))
            pixels = []
            
            for y in range(sprite.height):
                for x in range(sprite.width):
                    color_idx = sprite.get_pixel(x, y)
                    if 0 <= color_idx < len(sprite.palette):
                        pixels.append(sprite.palette[color_idx])
                    else:
                        pixels.append((0, 0, 0))
            
            img.putdata(pixels)
            
            # Save
            filename = output_dir / f"seq_planar_order_{i}_{plane_order}.png"
            img.save(filename)
            print(f"Saved: {filename}")
            
        except Exception as e:
            print(f"Failed for plane order {plane_order}: {e}")


def try_tiled_planar_decodings(data: bytes, output_dir: Path):
    """Try different tiled planar decodings."""
    print("Trying tiled planar decodings...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Different tile sizes that might work
    tile_sizes = [(8, 8), (16, 16)]
    
    for tile_w, tile_h in tile_sizes:
        if tile_w % 8 != 0 or tile_h % 8 != 0:
            continue
            
        # Calculate how many tiles we could fit in a reasonable image
        # Try to make a roughly square arrangement
        bytes_per_tile = (tile_w * tile_h // 8) * 4  # 4 planes
        max_tiles = len(data) // bytes_per_tile
        
        if max_tiles == 0:
            continue
            
        # Try different numbers of tiles to form a square-ish image
        for tile_count in [16, 36, 64, 100]:  # 4x4, 6x6, 8x8, 10x10 grids
            if tile_count > max_tiles:
                continue
                
            grid_w = int(tile_count ** 0.5)
            grid_h = (tile_count + grid_w - 1) // grid_w  # Round up division
            
            img_w = grid_w * tile_w
            img_h = grid_h * tile_h
            
            try:
                decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
                
                # For tiled planar, we need to arrange tiles in the right order
                sprite = decoder.decode_tiled_planar(
                    data[:tile_count * bytes_per_tile],
                    width=img_w,
                    height=img_h,
                    msb_first=True
                )
                
                # Create image
                img = Image.new('RGB', (sprite.width, sprite.height))
                pixels = []
                
                for y in range(sprite.height):
                    for x in range(sprite.width):
                        color_idx = sprite.get_pixel(x, y)
                        if 0 <= color_idx < len(sprite.palette):
                            pixels.append(sprite.palette[color_idx])
                        else:
                            pixels.append((0, 0, 0))
                
                img.putdata(pixels)
                
                # Save
                filename = output_dir / f"tiled_{tile_w}x{tile_h}_{grid_w}x{grid_h}.png"
                img.save(filename)
                print(f"Saved: {filename}")
                
            except Exception as e:
                print(f"Failed for {tile_w}x{tile_h} tiles: {e}")


def try_linear_decodings(data: bytes, output_dir: Path):
    """Try linear (non-planar) decodings."""
    print("Trying linear decodings...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Try treating as 4-bit packed data (2 pixels per byte)
    sizes = [
        (320, 200),  # Standard EGA resolution
        (640, 100),  # Same pixel count, different aspect
        (160, 400),  # Another possibility
        (160, 200),  # Half-width, full-height
        (320, 100),  # Full-width, half-height
    ]
    
    for width, height in sizes:
        pixel_count = width * height
        byte_count = (pixel_count + 1) // 2  # 2 pixels per byte in 4-bit packed
        
        if byte_count > len(data):
            continue
            
        try:
            decoder = EGADecoder(palette=DEFAULT_16_PALETTE)
            sprite = decoder.decode_linear(data[:byte_count], width, height)
            
            # Create image
            img = Image.new('RGB', (sprite.width, sprite.height))
            pixels = []
            
            for y in range(sprite.height):
                for x in range(sprite.width):
                    color_idx = sprite.get_pixel(x, y)
                    if 0 <= color_idx < len(sprite.palette):
                        pixels.append(sprite.palette[color_idx])
                    else:
                        pixels.append((0, 0, 0))
            
            img.putdata(pixels)
            
            # Save
            filename = output_dir / f"linear_{width}x{height}.png"
            img.save(filename)
            print(f"Saved: {filename}")
            
        except Exception as e:
            print(f"Failed for {width}x{height}: {e}")


def try_different_palettes(data: bytes, output_dir: Path):
    """Try different palettes with the known good format."""
    print("Trying different palettes...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Based on the docs, MAZEDATA.EGA uses sequential planar with grayscale values
    width, height = 320, 200
    bytes_needed = width * height // 2
    
    if len(data) < bytes_needed:
        print(f"Not enough data for {width}x{height} image")
        return
    
    # Different palettes to try
    palettes = [
        ("default_16", DEFAULT_16_PALETTE),
        ("grayscale", create_grayscale_palette()),
        ("ega_64_subset", EGA_64_PALETTE[:16]),
        ("intensities", [(i*17, i*17, i*17) for i in range(16)]),  # 0, 17, 34, ..., 255
    ]
    
    decoder = EGADecoder()  # Will be reset for each palette
    
    for name, palette in palettes:
        try:
            decoder.palette = palette
            sprite = decoder.decode_planar(
                data[:bytes_needed],
                width=width,
                height=height,
                msb_first=True,
                plane_order=[3, 0, 2, 1]  # Based on docs, this worked well
            )
            
            # Create image
            img = Image.new('RGB', (sprite.width, sprite.height))
            pixels = []
            
            for y in range(sprite.height):
                for x in range(sprite.width):
                    color_idx = sprite.get_pixel(x, y)
                    if 0 <= color_idx < len(sprite.palette):
                        pixels.append(sprite.palette[color_idx])
                    else:
                        pixels.append((0, 0, 0))
            
            img.putdata(pixels)
            
            # Save
            filename = output_dir / f"palette_{name}.png"
            img.save(filename)
            print(f"Saved: {filename}")
            
        except Exception as e:
            print(f"Failed for palette {name}: {e}")


def try_offset_decodings(data: bytes, output_dir: Path):
    """Try decoding from different offsets."""
    print("Trying offset decodings...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Known interesting offsets from the analysis
    offsets = [0x0000, 0x0AF9, 0x1931, 0x7C00, 0x8000]
    width, height = 320, 200
    bytes_needed = width * height // 2
    
    for offset in offsets:
        if offset + bytes_needed > len(data):
            print(f"Offset {hex(offset)} too large, skipping")
            continue
            
        try:
            decoder = EGADecoder(palette=create_grayscale_palette())
            sprite = decoder.decode_planar(
                data[offset:offset + bytes_needed],
                width=width,
                height=height,
                msb_first=True,
                plane_order=[3, 0, 2, 1]
            )
            
            # Create image
            img = Image.new('RGB', (sprite.width, sprite.height))
            pixels = []
            
            for y in range(sprite.height):
                for x in range(sprite.width):
                    color_idx = sprite.get_pixel(x, y)
                    if 0 <= color_idx < len(sprite.palette):
                        pixels.append(sprite.palette[color_idx])
                    else:
                        pixels.append((0, 0, 0))
            
            img.putdata(pixels)
            
            # Save
            filename = output_dir / f"offset_{offset:04X}.png"
            img.save(filename)
            print(f"Saved: {filename}")
            
        except Exception as e:
            print(f"Failed for offset {hex(offset)}: {e}")


def main():
    """Main function to try different decodings."""
    print("Trying Different MAZEDATA.EGA Decodings")
    print("=" * 50)
    
    # Check if MAZEDATA.EGA exists
    mazedata_path = Path("gamedata") / "MAZEDATA.EGA"
    if not mazedata_path.exists():
        print(f"Error: {mazedata_path} not found")
        return

    # Create output directory
    output_dir = Path("different_decodings")
    output_dir.mkdir(exist_ok=True)

    # Read the file
    print(f"Reading: {mazedata_path}")
    data = mazedata_path.read_bytes()
    print(f"File size: {len(data):,} bytes")

    # Try different approaches
    try_sequential_planar_decodings(data, output_dir)
    print()
    
    try_tiled_planar_decodings(data, output_dir)
    print()
    
    try_linear_decodings(data, output_dir)
    print()
    
    try_different_palettes(data, output_dir)
    print()
    
    try_offset_decodings(data, output_dir)
    print()
    
    print(f"All decodings saved to: {output_dir.absolute()}")


if __name__ == "__main__":
    main()