"""Focus on extracting individual tiles that form recognizable patterns.

Based on the project's findings, there should be recognizable tile patterns
in the MAZEDATA.EGA file. Let's try to extract them more systematically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Pillow not found. Install with 'pip install Pillow' for image saving.")


def create_grayscale_palette() -> list[tuple[int, int, int]]:
    """Create a 16-level grayscale palette."""
    palette = []
    for i in range(16):
        gray = int((i / 15.0) * 255)
        palette.append((gray, gray, gray))
    return palette


def extract_specific_regions():
    """Extract specific regions that should contain recognizable patterns."""
    print("Extracting specific regions with recognizable patterns...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()
    print(f"Loaded: {len(data)} bytes")

    # Create output directory
    output_dir = Path("recognizable_patterns")
    output_dir.mkdir(exist_ok=True)
    
    # Based on the documentation, band 4 (y=128-160) had clear tile patterns
    # Let's extract that region specifically
    grayscale_palette = create_grayscale_palette()
    decoder = EGADecoder(palette=grayscale_palette)
    
    # Decode the full image first
    full_atlas = decoder.decode_planar(
        data[:32000],  # First 32000 bytes
        width=320,
        height=200,
        msb_first=True
    )
    
    # Create the full image
    full_img = Image.new('RGB', (full_atlas.width, full_atlas.height))
    full_pixels = []
    
    for y in range(full_atlas.height):
        for x in range(full_atlas.width):
            intensity = full_atlas.get_pixel(x, y)
            if 0 <= intensity < len(full_atlas.palette):
                full_pixels.append(full_atlas.palette[intensity])
            else:
                full_pixels.append((0, 0, 0))
    
    full_img.putdata(full_pixels)
    
    # Extract the specific band that had clear patterns (Band 4: y=128-160)
    band_4_img = full_img.crop((0, 128, 320, 160))
    band_4_img.save(output_dir / "band_4_clear_tiles_region.png")
    print(f"Saved band 4 region (y=128-160): {output_dir}/band_4_clear_tiles_region.png")
    
    # Scale it up for better visibility
    band_4_scaled = band_4_img.resize((1280, 128), Image.NEAREST)
    band_4_scaled.save(output_dir / "band_4_scaled_4x.png")
    print(f"Saved scaled band 4: {output_dir}/band_4_scaled_4x.png")
    
    # Now let's try to identify individual tiles within this band
    # Each tile is likely 32x32 pixels based on the documentation
    tile_width, tile_height = 32, 32
    
    # Calculate how many tiles fit in the band (320x32)
    tiles_per_row = 320 // tile_width
    num_rows = 32 // tile_height  # Should be 1 for this band
    
    print(f"Extracting {tiles_per_row} tiles from band 4...")
    
    tiles_dir = output_dir / "extracted_band4_tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    for row in range(num_rows):
        for col in range(tiles_per_row):
            left = col * tile_width
            upper = row * tile_height + 128  # Offset for band position
            right = left + tile_width
            lower = upper + tile_height
            
            tile_img = full_img.crop((left, upper, right, lower))
            tile_filename = tiles_dir / f"band4_tile_row{row}_col{col}.png"
            tile_img.save(tile_filename)
            print(f"  Saved tile: {tile_filename.name}")


def try_column_major_extraction():
    """Try column-major extraction which was mentioned as successful."""
    print("\nTrying column-major extraction...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()
    
    # Create output directory
    output_dir = Path("column_major")
    output_dir.mkdir(exist_ok=True)
    
    # Based on some analysis, let's try a different approach
    # Maybe the data is arranged differently than standard planar
    # Let's try treating it as linear grayscale data
    
    # For a 320x200 image with 4 bits per pixel, we need 320*200/2 = 32000 bytes
    # Let's try interpreting the first 32000 bytes as 4-bit grayscale values
    
    grayscale_palette = create_grayscale_palette()
    decoder = EGADecoder(palette=grayscale_palette)
    
    # Try linear decoding instead of planar
    try:
        # First, convert 4-bit data to 8-bit for linear processing
        raw_data = data[:32000]  # First 32k bytes
        
        # Convert 4-bit packed to 8-bit unpacked
        pixels = []
        for byte_val in raw_data:
            # High nibble first, then low nibble
            pixels.append((byte_val >> 4) & 0x0F)  # High 4 bits
            pixels.append(byte_val & 0x0F)          # Low 4 bits
        
        # Create image from these grayscale values
        width, height = 320, 200
        if len(pixels) >= width * height:
            pixels = pixels[:width * height]
        else:
            # Pad if too short
            pixels.extend([0] * (width * height - len(pixels)))
        
        img = Image.new('RGB', (width, height))
        rgb_pixels = []
        
        for pixel_val in pixels:
            if 0 <= pixel_val < len(grayscale_palette):
                rgb_pixels.append(grayscale_palette[pixel_val])
            else:
                rgb_pixels.append((0, 0, 0))
        
        img.putdata(rgb_pixels)
        img.save(output_dir / "linear_4bit_grayscale.png")
        print(f"Saved linear 4-bit grayscale: {output_dir}/linear_4bit_grayscale.png")
        
    except Exception as e:
        print(f"Linear decoding failed: {e}")


def extract_known_tile_areas():
    """Extract areas that are known to contain tiles based on analysis."""
    print("\nExtracting known tile areas...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()
    
    # Create output directory
    output_dir = Path("known_tile_areas")
    output_dir.mkdir(exist_ok=True)
    
    # According to the docs, there might be tile structures in the data
    # Let's try to find 64x64 and 32x32 texture areas
    
    # Based on the docs, let's try to extract from the area that was identified
    # as containing clear tile patterns
    start_offsets = [0x0000, 0x0AF9, 0x1931]
    
    # For each start offset, try to extract potential tile structures
    for offset in start_offsets:
        if offset >= len(data):
            continue
            
        print(f"Examining data from offset 0x{offset:04X}...")
        
        # Try to extract a 64x64 texture (would be 64*64/2 = 2048 bytes in 4-bit format)
        # Or in planar format, would be 64*64/8 * 4 = 2048 bytes as well
        texture_size = 64 * 64 // 2  # 2048 bytes for 64x64 4-bit texture
        
        if offset + texture_size <= len(data):
            texture_data = data[offset:offset + texture_size]
            
            # Try to decode this as a 64x64 texture
            try:
                grayscale_palette = create_grayscale_palette()
                decoder = EGADecoder(palette=grayscale_palette)
                
                # Try linear decoding first
                texture_sprite = decoder.decode_linear(texture_data, 64, 64)
                
                # Create image
                img = Image.new('RGB', (texture_sprite.width, texture_sprite.height))
                pixels = []
                
                for y in range(texture_sprite.height):
                    for x in range(texture_sprite.width):
                        color_idx = texture_sprite.get_pixel(x, y)
                        if 0 <= color_idx < len(texture_sprite.palette):
                            pixels.append(texture_sprite.palette[color_idx])
                        else:
                            pixels.append((0, 0, 0))
                
                img.putdata(pixels)
                
                # Save
                filename = output_dir / f"texture_64x64_offset_{offset:04X}.png"
                img.save(filename)
                print(f"  Saved 64x64 texture: {filename.name}")
                
            except Exception as e:
                print(f"  Failed to decode 64x64 texture at offset 0x{offset:04X}: {e}")
        
        # Also try 32x32 textures
        texture_size = 32 * 32 // 2  # 512 bytes for 32x32 4-bit texture
        
        if offset + texture_size <= len(data):
            texture_data = data[offset:offset + texture_size]
            
            try:
                grayscale_palette = create_grayscale_palette()
                decoder = EGADecoder(palette=grayscale_palette)
                
                texture_sprite = decoder.decode_linear(texture_data, 32, 32)
                
                # Create image
                img = Image.new('RGB', (texture_sprite.width, texture_sprite.height))
                pixels = []
                
                for y in range(texture_sprite.height):
                    for x in range(texture_sprite.width):
                        color_idx = texture_sprite.get_pixel(x, y)
                        if 0 <= color_idx < len(texture_sprite.palette):
                            pixels.append(texture_sprite.palette[color_idx])
                        else:
                            pixels.append((0, 0, 0))
                
                img.putdata(pixels)
                
                # Save
                filename = output_dir / f"texture_32x32_offset_{offset:04X}.png"
                img.save(filename)
                print(f"  Saved 32x32 texture: {filename.name}")
                
            except Exception as e:
                print(f"  Failed to decode 32x32 texture at offset 0x{offset:04X}: {e}")


def main():
    """Main function to extract recognizable patterns."""
    print("Extracting Recognizable Patterns from MAZEDATA.EGA")
    print("=" * 60)
    
    extract_specific_regions()
    try_column_major_extraction()
    extract_known_tile_areas()
    
    print(f"\nAll results saved to respective directories.")
    print("Check the following directories:")
    print("  - recognizable_patterns/: Specific regions with clear patterns")
    print("  - column_major/: Alternative column-major interpretation")
    print("  - known_tile_areas/: Areas with known tile structures")


if __name__ == "__main__":
    main()