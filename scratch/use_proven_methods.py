"""Extract textures using the methods that were proven successful in the project.

Based on the documentation, the MAZEDATA.EGA file was successfully decoded using
specific techniques. Let's replicate those exact methods.
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


def extract_texture_bands_method():
    """Use the exact method from the successful documentation."""
    print("Using the proven successful method from documentation...")
    
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

    # Create grayscale palette as mentioned in the docs
    grayscale_palette = create_grayscale_palette()

    # Decode as sequential planar with grayscale palette (as per docs)
    decoder = EGADecoder(palette=grayscale_palette)
    atlas = decoder.decode_planar(
        data[:32000],  # First 32000 bytes as per docs
        width=320,
        height=200,
        msb_first=True
    )

    print(f"Decoded: {atlas.width}x{atlas.height}")
    print(f"Palette: 16-level grayscale (0=black, 15=white)")

    # Convert to image
    img = Image.new('RGB', (atlas.width, atlas.height))
    pixels = []

    for y in range(atlas.height):
        for x in range(atlas.width):
            intensity = atlas.get_pixel(x, y)
            if 0 <= intensity < len(atlas.palette):
                pixels.append(atlas.palette[intensity])
            else:
                pixels.append((0, 0, 0))

    img.putdata(pixels)

    # Create output directory
    output_dir = Path("proven_success")
    output_dir.mkdir(exist_ok=True)

    # Save at different scales
    img.save(output_dir / "mazedata_grayscale_320x200.png")
    print(f"Saved: {output_dir}/mazedata_grayscale_320x200.png")

    # 2x scale
    scaled = img.resize((640, 400), Image.NEAREST)
    scaled.save(output_dir / "mazedata_grayscale_640x400.png")
    print(f"Saved: {output_dir}/mazedata_grayscale_640x400.png")

    # 3x scale
    scaled = img.resize((960, 600), Image.NEAREST)
    scaled.save(output_dir / "mazedata_grayscale_960x600.png")
    print(f"Saved: {output_dir}/mazedata_grayscale_960x600.png")

    # Extract individual bands as mentioned in the docs
    print()
    print("Extracting texture bands:")
    print("-" * 70)

    band_configs = [
        (0, 32, "Band_0_Floor_Wall"),
        (32, 64, "Band_1_Wall_Patterns"),
        (64, 96, "Band_2_Complex"),
        (96, 128, "Band_3_Varied"),
        (128, 160, "Band_4_Clear_Tiles"),
        (160, 200, "Band_5_Ceiling"),
    ]

    for y_start, y_end, name in band_configs:
        band_img = img.crop((0, y_start, 320, y_end))

        # Scale up 4x for visibility
        band_scaled = band_img.resize((1280, (y_end - y_start) * 4), Image.NEAREST)

        filename = output_dir / f"{name}_y{y_start}-{y_end}.png"
        band_scaled.save(filename)
        print(f"  {name}: {filename.name}")

    # Create annotated overview
    print()
    print("Creating annotated overview...")

    overview = Image.new('RGB', (960 + 400, 600), (20, 20, 20))
    overview.paste(scaled, (0, 0))

    # Add annotations
    from PIL import ImageDraw
    draw = ImageDraw.Draw(overview)

    # Draw band separators
    for i, (y_start, y_end, name) in enumerate(band_configs):
        y_line = y_end * 3  # 3x scale
        draw.line([(0, y_line), (960, y_line)], fill=(255, 255, 0), width=2)
        draw.text((5, y_start * 3 + 5), str(i), fill=(255, 255, 255))

    # Add title and notes
    draw.text((10, 575), "MAZEDATA.EGA - GRAYSCALE TEXTURES", fill=(255, 255, 255))
    draw.text((970, 20), "GRAYSCALE DECODING:", fill=(100, 255, 100))
    draw.text((970, 45), "4-bit values = intensity (0-15)", fill=(220, 220, 220))
    draw.text((970, 65), "0 = Black, 15 = White", fill=(220, 220, 220))
    draw.text((970, 90), "", fill=(220, 220, 220))
    draw.text((970, 110), "This is the correct format!", fill=(100, 255, 100))
    draw.text((970, 135), "Game colorizes at runtime", fill=(220, 220, 220))

    overview.save(output_dir / "grayscale_overview_annotated.png")
    print(f"Saved: {output_dir}/grayscale_overview_annotated.png")


def extract_individual_tiles_method():
    """Extract individual tiles using the successful method."""
    print("\nExtracting individual tiles using successful method...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()
    
    # Based on the docs, let's focus on the area with clear tile patterns (Band 4: y=128-160)
    # This corresponds to bytes in the range that would map to that region
    # For 320x200 image with 4 planes, each row takes 320/8*4 = 160 bytes
    # So rows 128-160 would be from byte offset 128*160 to 160*160
    
    # Actually, let's try to extract 8x8 tiles from the raw data
    # Each 8x8 tile in planar format is 32 bytes (8 bytes per plane * 4 planes)
    
    output_dir = Path("proven_success")
    output_dir.mkdir(exist_ok=True)
    
    # Create tiles directory
    tiles_dir = output_dir / "individual_tiles"
    tiles_dir.mkdir(exist_ok=True)
    
    # Try extracting tiles from the area that showed clear patterns
    # Based on the docs, Band 4 (y=128-160) had clear tile patterns
    # That's 32 rows, which is 32 * 320/8 * 4 = 5120 bytes of planar data
    # This could contain 5120/32 = 160 8x8 tiles
    
    # But let's also try from the beginning of the file
    start_positions = [
        (0, "beginning_of_file"),
        (0x0AF9, "after_first_null_seq"), 
        (0x1931, "after_big_null_seq"),
    ]
    
    for start_pos, desc in start_positions:
        print(f"Extracting tiles from {desc} (offset 0x{start_pos:04X})...")
        
        # Calculate how many tiles we can extract
        available_data = data[start_pos:]
        num_tiles = len(available_data) // 32  # 32 bytes per 8x8 tile in planar format
        
        print(f"  Available data: {len(available_data)} bytes")
        print(f"  Possible tiles: {num_tiles}")
        
        # Extract first 50 tiles for this position
        tiles_to_extract = min(50, num_tiles)
        
        for i in range(tiles_to_extract):
            tile_offset = start_pos + i * 32
            if tile_offset + 32 > len(data):
                break
                
            tile_data = data[tile_offset:tile_offset + 32]
            
            # Decode the 8x8 tile in planar format
            pixels = [0] * 64  # 8x8 = 64 pixels
            
            for plane in range(4):
                plane_offset = plane * 8  # 8 bytes per plane for 8x8 tile
                
                for row in range(8):
                    byte_val = tile_data[plane_offset + row]
                    
                    # Extract 8 pixels from this byte (MSB first)
                    for bit in range(8):
                        pixel_idx = row * 8 + (7 - bit)  # MSB first
                        if byte_val & (1 << bit):
                            pixels[pixel_idx] |= (1 << plane)
            
            # Create tile image with grayscale palette
            grayscale_palette = create_grayscale_palette()
            tile_img = Image.new('RGB', (8, 8))
            tile_pixels = []
            
            for y in range(8):
                for x in range(8):
                    color_idx = pixels[y * 8 + x]
                    if 0 <= color_idx < len(grayscale_palette):
                        tile_pixels.append(grayscale_palette[color_idx])
                    else:
                        tile_pixels.append((0, 0, 0))
            
            tile_img.putdata(tile_pixels)
            
            # Scale up for visibility
            scaled_tile = tile_img.resize((64, 64), Image.NEAREST)
            
            filename = tiles_dir / f"tile_{desc}_idx_{i:03d}_offset_{tile_offset:04X}.png"
            scaled_tile.save(filename)
    
    print(f"Individual tiles saved to: {tiles_dir}")


def main():
    """Main function to run the proven successful methods."""
    print("Running Proven Successful Methods")
    print("=" * 50)
    
    extract_texture_bands_method()
    extract_individual_tiles_method()
    
    print(f"\nAll results saved to: proven_success/")


if __name__ == "__main__":
    main()