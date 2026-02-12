"""Extract images from MAZEDATA.EGA file.

This script extracts images from the Wizardry 6 MAZEDATA.EGA file, which contains
wall, floor, and ceiling textures in 4bpp planar format.

Based on analysis, MAZEDATA.EGA contains:
- A 320x200 texture atlas in sequential planar format (first 32,000 bytes)
- Additional texture data and metadata after the main atlas
- 4-bit grayscale values (0-15) that are colorized at runtime
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Add the project root to the path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow not found. Install with 'pip install Pillow' for image saving.")


def create_grayscale_palette() -> List[Tuple[int, int, int]]:
    """Create a 16-level grayscale palette for texture data.
    
    Maps 4-bit values (0-15) to grayscale RGB values.
    0 = black (0, 0, 0)
    15 = white (255, 255, 255)
    """
    palette = []
    for i in range(16):
        # Linear interpolation from 0 to 255
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def decode_sequential_planar(data: bytes, width: int, height: int, 
                           palette: List[Tuple[int, int, int]]) -> 'Sprite':
    """Decode sequential planar EGA data into a sprite.
    
    Sequential planar format stores each complete plane consecutively:
    - Plane 0: all bytes for this plane
    - Plane 1: all bytes for this plane
    - Plane 2: all bytes for this plane
    - Plane 3: all bytes for this plane
    """
    if width % 8 != 0:
        raise ValueError(f"Width must be multiple of 8, got {width}")

    bytes_per_row = width // 8
    plane_size = bytes_per_row * height
    planes = 4  # EGA uses 4 planes
    expected_size = plane_size * planes

    if len(data) < expected_size:
        print(f"Warning: Data too short: expected {expected_size} bytes, got {len(data)}")
        # Pad with zeros
        data = data + b"\x00" * (expected_size - len(data))

    pixels: List[int] = [0] * (width * height)

    for plane in range(planes):
        plane_offset = plane * plane_size
        for y in range(height):
            row_offset = plane_offset + y * bytes_per_row
            for byte_idx in range(bytes_per_row):
                byte_val = data[row_offset + byte_idx]
                for bit in range(8):
                    x = byte_idx * 8 + (7 - bit)  # MSB first
                    pixel_idx = y * width + x
                    if byte_val & (1 << bit):
                        pixels[pixel_idx] |= 1 << plane

    # Create a simple sprite-like object
    class Sprite:
        def __init__(self, width, height, pixels, palette):
            self.width = width
            self.height = height
            self.pixels = pixels
            self.palette = palette
        
        def get_pixel(self, x, y):
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.pixels[y * self.width + x]
            return 0
    
    return Sprite(width, height, pixels, palette)


def decode_tiled_planar(data: bytes, width: int, height: int, 
                       palette: List[Tuple[int, int, int]]) -> 'Sprite':
    """Decode EGA tiled planar format.
    
    Each 32-byte block is one 8x8 tile:
      - Bytes 0-7: plane 0 (bit 0 of color)
      - Bytes 8-15: plane 1 (bit 1 of color)
      - Bytes 16-23: plane 2 (bit 2 of color)
      - Bytes 24-31: plane 3 (bit 3 of color)
    """
    if width % 8 != 0 or height % 8 != 0:
        raise ValueError(f"Tiled planar decode requires 8x8 alignment, got {width}x{height}")

    tiles_x = width // 8
    tiles_y = height // 8
    expected_tiles = tiles_x * tiles_y
    expected_bytes = expected_tiles * 32

    if len(data) < expected_bytes:
        data = data + b"\x00" * (expected_bytes - len(data))

    pixels = [0] * (width * height)

    for tile_idx in range(expected_tiles):
        tile_base = tile_idx * 32
        tile_x = tile_idx % tiles_x
        tile_y = tile_idx // tiles_x

        for row in range(8):
            for bit in range(8):
                mask = 0x80 >> bit
                color = 0
                for plane_idx in range(4):
                    if data[tile_base + row + plane_idx * 8] & mask:
                        color |= (1 << plane_idx)

                px = tile_x * 8 + bit
                py = tile_y * 8 + row
                pixels[py * width + px] = color

    # Create a simple sprite-like object
    class Sprite:
        def __init__(self, width, height, pixels, palette):
            self.width = width
            self.height = height
            self.pixels = pixels
            self.palette = palette
        
        def get_pixel(self, x, y):
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.pixels[y * self.width + x]
            return 0
    
    return Sprite(width, height, pixels, palette)


def extract_texture_bands(sprite, output_dir: Path) -> None:
    """Extract individual texture bands from the 320x200 atlas."""
    if not HAS_PIL:
        print("Cannot extract texture bands without Pillow")
        return

    # Create output directory
    bands_dir = output_dir / "bands"
    bands_dir.mkdir(parents=True, exist_ok=True)

    # Define band configurations
    band_configs = [
        (0, 32, "floor_wall_patterns"),
        (32, 64, "wall_patterns"),
        (64, 96, "complex_patterns"),
        (96, 128, "varied_patterns"),
        (128, 160, "clear_tiles"),
        (160, 200, "ceiling_floor_solid"),
    ]

    # Create full atlas image
    img = Image.new('RGB', (sprite.width, sprite.height))
    pixels = []

    for y in range(sprite.height):
        for x in range(sprite.width):
            intensity = sprite.get_pixel(x, y)
            if 0 <= intensity < len(sprite.palette):
                pixels.append(sprite.palette[intensity])
            else:
                pixels.append((0, 0, 0))

    img.putdata(pixels)

    # Save full atlas
    img.save(output_dir / "mazedata_atlas_320x200.png")
    print(f"Saved full atlas: {output_dir}/mazedata_atlas_320x200.png")

    # Extract and save each band
    for y_start, y_end, name in band_configs:
        band_img = img.crop((0, y_start, 320, y_end))
        
        # Scale up 4x for visibility
        band_scaled = band_img.resize((1280, (y_end - y_start) * 4), Image.NEAREST)
        
        filename = bands_dir / f"{name}_y{y_start}-{y_end}.png"
        band_scaled.save(filename)
        print(f"Saved band: {filename}")


def extract_individual_tiles(data: bytes, output_dir: Path, start_offset: int = 0) -> None:
    """Extract individual 8x8 tiles from the data."""
    if not HAS_PIL:
        print("Cannot extract individual tiles without Pillow")
        return

    # Create output directory
    tiles_dir = output_dir / "tiles"
    tiles_dir.mkdir(parents=True, exist_ok=True)

    # Calculate how many tiles we can extract
    available_bytes = len(data) - start_offset
    num_tiles = available_bytes // 32

    print(f"Extracting {num_tiles} tiles from offset 0x{start_offset:04X}")

    # Extract first 100 tiles for demonstration
    tiles_to_extract = min(100, num_tiles)
    
    for i in range(tiles_to_extract):
        offset = start_offset + i * 32
        tile_data = data[offset:offset + 32]

        # Decode the tile (each tile is 8x8 pixels in planar format)
        pixels = [0] * 64  # 8x8 = 64 pixels

        for plane in range(4):
            plane_offset = plane * 8

            for row in range(8):
                byte_val = tile_data[plane_offset + row]

                # Extract 8 pixels from this byte (MSB first)
                for bit in range(8):
                    pixel_idx = row * 8 + (7 - bit)  # MSB first
                    if byte_val & (1 << bit):
                        pixels[pixel_idx] |= (1 << plane)

        # Create tile image
        tile_img = Image.new('RGB', (8, 8))
        tile_pixels = []

        for y in range(8):
            for x in range(8):
                color_idx = pixels[y * 8 + x]
                if 0 <= color_idx < len(DEFAULT_16_PALETTE):
                    tile_pixels.append(DEFAULT_16_PALETTE[color_idx])
                else:
                    tile_pixels.append((0, 0, 0))

        tile_img.putdata(tile_pixels)

        # Scale up for visibility
        scaled_tile = tile_img.resize((64, 64), Image.NEAREST)

        filename = tiles_dir / f"tile_{i:03d}_offset_{offset:04X}.png"
        scaled_tile.save(filename)

    print(f"Saved {tiles_to_extract} individual tiles to {tiles_dir}/")


def main():
    """Main function to extract images from MAZEDATA.EGA."""
    print("MAZEDATA.EGA Image Extractor")
    print("=" * 50)
    
    # Check if MAZEDATA.EGA exists
    mazedata_path = Path("gamedata") / "MAZEDATA.EGA"
    if not mazedata_path.exists():
        print(f"Error: {mazedata_path} not found")
        print("Please ensure the gamedata directory contains MAZEDATA.EGA")
        return

    # Create output directory
    output_dir = Path("extracted_images")
    output_dir.mkdir(exist_ok=True)

    # Read the file
    print(f"Reading: {mazedata_path}")
    data = mazedata_path.read_bytes()
    print(f"File size: {len(data):,} bytes")

    # Mark task 2 as in progress
    print("\nTask 2: Implementing sequential planar decoding...")
    
    # Decode as sequential planar (first 32,000 bytes = 320x200 image)
    atlas_size = 320 * 200 // 2  # 320*200 pixels at 4 bits per pixel = 32000 bytes
    if len(data) >= atlas_size:
        print("Decoding main texture atlas (320x200)...")
        
        # Use grayscale palette for texture data
        grayscale_palette = create_grayscale_palette()
        atlas_sprite = decode_sequential_planar(
            data[:atlas_size], 
            width=320, 
            height=200, 
            palette=grayscale_palette
        )
        
        print("Extracting texture bands...")
        extract_texture_bands(atlas_sprite, output_dir)
    else:
        print(f"File too small for 320x200 atlas: only {len(data)} bytes")

    # Mark task 3 as in progress
    print("\nTask 3: Implementing tiled planar decoding...")
    
    # Extract individual tiles from different sections of the file
    print("Extracting individual tiles...")
    
    # Try different starting points based on analysis
    possible_starts = [
        (0x0000, "file_start"),
        (0x0AF9, "after_first_null_seq"),
        (0x1931, "after_big_null_seq"),
    ]

    for start_offset, description in possible_starts:
        if start_offset < len(data):
            print(f"Trying tile extraction from {description} (offset 0x{start_offset:04X})...")
            extract_individual_tiles(data, output_dir / description, start_offset)
    
    # Mark task 4 as in progress
    print("\nTask 4: Adding grayscale decoding option...")
    
    # Create a grayscale version of the atlas
    if HAS_PIL and len(data) >= atlas_size:
        print("Creating grayscale version...")
        
        # Create grayscale atlas image
        grayscale_img = Image.new('RGB', (320, 200))
        grayscale_pixels = []

        for y in range(200):
            for x in range(320):
                intensity = atlas_sprite.get_pixel(x, y)
                if 0 <= intensity < len(grayscale_palette):
                    grayscale_pixels.append(grayscale_palette[intensity])
                else:
                    grayscale_pixels.append((0, 0, 0))

        grayscale_img.putdata(grayscale_pixels)
        grayscale_img.save(output_dir / "mazedata_grayscale_320x200.png")
        print(f"Saved grayscale atlas: {output_dir}/mazedata_grayscale_320x200.png")

    # Mark task 5 as in progress
    print("\nTask 5: Saving extracted images to output directory...")
    
    print(f"\nExtraction complete!")
    print(f"Images saved to: {output_dir.absolute()}")
    print("\nDirectory structure:")
    print(f"  {output_dir}/")
    print(f"  - mazedata_atlas_320x200.png          # Full texture atlas")
    print(f"  - mazedata_grayscale_320x200.png      # Grayscale version")
    print(f"  - bands/                              # Individual texture bands")
    print(f"  - tiles/                              # Individual 8x8 tiles")
    print(f"    - file_start/, after_first_null_seq/, after_big_null_seq/")
    print(f"      - Individual tile images")


if __name__ == "__main__":
    main()