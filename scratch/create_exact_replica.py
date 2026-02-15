"""Final attempt using the exact specifications from the successful decoding.

According to the documentation, MAZEDATA.EGA was successfully decoded as:
- Sequential planar format
- 320x200 resolution  
- 4-bit grayscale values (0-15) treated as intensity, not palette indices
- MSB-first bit ordering
- Plane order [3, 0, 2, 1] was found to work well
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from bane.data.sprite_decoder import EGADecoder

try:
    from PIL import Image, ImageDraw
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


def create_exact_replica():
    """Create an exact replica using the documented successful method."""
    print("Creating exact replica using documented successful method...")
    
    if not HAS_PIL:
        print("Pillow required for this function")
        return
    
    # Load MAZEDATA.EGA
    path = Path("gamedata") / "MAZEDATA.EGA"
    if not path.exists():
        print(f"Error: {path} not found")
        return

    data = path.read_bytes()
    print(f"File size: {len(data):,} bytes")
    
    # Create output directory
    output_dir = Path("exact_replica")
    output_dir.mkdir(exist_ok=True)
    
    # According to docs, use grayscale palette and specific plane order
    grayscale_palette = create_grayscale_palette()
    
    # Decode with the exact parameters that worked
    decoder = EGADecoder(palette=grayscale_palette)
    
    # The docs say the main 320x200 texture atlas is in the first 32,000 bytes
    # Using sequential planar format with MSB-first and specific plane order
    atlas = decoder.decode_planar(
        data[:32000],  # First 32000 bytes as per docs
        width=320,
        height=200,
        msb_first=True,
        plane_order=[3, 0, 2, 1]  # Documented as working order
    )
    
    print(f"Successfully decoded 320x200 atlas")
    
    # Create the image
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
    
    # Save the main image
    main_file = output_dir / "mazedata_exact_replica.png"
    img.save(main_file)
    print(f"Saved main atlas: {main_file}")
    
    # Create a zoomed version to see details better
    zoomed = img.resize((960, 600), Image.NEAREST)  # 3x scale
    zoomed_file = output_dir / "mazedata_zoomed_3x.png"
    zoomed.save(zoomed_file)
    print(f"Saved zoomed version: {zoomed_file}")
    
    # Extract the specific bands mentioned in the docs
    print("\nExtracting documented texture bands...")
    
    band_configs = [
        (0, 32, "floor_wall_patterns"),
        (32, 64, "wall_patterns"), 
        (64, 96, "complex_patterns"),
        (96, 128, "varied_patterns"),
        (128, 160, "clear_tiles"),  # This one should have recognizable patterns
        (160, 200, "ceiling_floor_solid"),
    ]
    
    for y_start, y_end, name in band_configs:
        band_img = img.crop((0, y_start, 320, y_end))
        
        # Save original size
        band_file = output_dir / f"band_{name}_y{y_start}-{y_end}.png"
        band_img.save(band_file)
        
        # Create enlarged version for better visibility
        enlarged = band_img.resize((1280, (y_end - y_start) * 4), Image.NEAREST)
        enlarged_file = output_dir / f"band_{name}_enlarged_y{y_start}-{y_end}.png"
        enlarged.save(enlarged_file)
        
        print(f"  Saved {name}: {band_file.name} and {enlarged_file.name}")
    
    # Focus extra attention on the "clear_tiles" band (128-160) which should have recognizable patterns
    print(f"\nFocusing on 'clear_tiles' band (y=128-160)...")
    clear_tiles_band = img.crop((0, 128, 320, 160))  # 320x32 region
    
    # This band should contain 10 tiles of 32x32 each (based on 320/32 = 10)
    # Or maybe 32 tiles of 16x16 each (320/16 = 20, 32/16 = 2, so 20*2 = 40 but that doesn't match)
    # Actually, let's think: if it's 320x32 and we want square tiles, 
    # possibilities are: 16x16 (20x2 grid), 32x32 (10x1 grid), etc.
    
    # Let's try 16x16 tiles first (more tiles might show patterns better)
    tile_size = 16
    tiles_x = 320 // tile_size
    tiles_y = 32 // tile_size
    
    print(f"  Extracting {tiles_x}x{tiles_y} = {tiles_x * tiles_y} tiles of {tile_size}x{tile_size}px")
    
    tiles_dir = output_dir / "clear_tiles_16x16"
    tiles_dir.mkdir(exist_ok=True)
    
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            left = tx * tile_size
            top = ty * tile_size
            right = left + tile_size
            bottom = top + tile_size
            
            tile_img = clear_tiles_band.crop((left, top, right, bottom))
            
            # Enlarge for visibility
            enlarged_tile = tile_img.resize((64, 64), Image.NEAREST)  # 4x scale
            
            tile_file = tiles_dir / f"tile_{ty}_{tx:02d}.png"
            enlarged_tile.save(tile_file)
    
    print(f"  Saved {tiles_x * tiles_y} 16x16 tiles to {tiles_dir}")
    
    # Also try 32x32 tiles
    tile_size = 32
    tiles_x = 320 // tile_size
    tiles_y = 32 // tile_size
    
    print(f"  Extracting {tiles_x}x{tiles_y} = {tiles_x * tiles_y} tiles of {tile_size}x{tile_size}px")
    
    tiles_dir = output_dir / "clear_tiles_32x32"
    tiles_dir.mkdir(exist_ok=True)
    
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            left = tx * tile_size
            top = ty * tile_size
            right = left + tile_size
            bottom = top + tile_size
            
            tile_img = clear_tiles_band.crop((left, top, right, bottom))
            
            # Enlarge for visibility
            enlarged_tile = tile_img.resize((128, 128), Image.NEAREST)  # 4x scale
            
            tile_file = tiles_dir / f"tile_{ty}_{tx:02d}.png"
            enlarged_tile.save(tile_file)
    
    print(f"  Saved {tiles_x * tiles_y} 32x32 tiles to {tiles_dir}")
    
    # Create a combined view showing all bands with labels
    print(f"\nCreating combined overview with labels...")
    
    # Create a canvas large enough for all bands stacked vertically plus space for labels
    total_height = sum((y_end - y_start) * 4 for _, y_end, _ in band_configs) + len(band_configs) * 30
    if total_height <= 0:
        total_height = 600  # fallback height
    overview_img = Image.new('RGB', (1280, total_height), (20, 20, 20))  # Dark gray background
    
    draw = ImageDraw.Draw(overview_img)
    
    current_y = 0
    for y_start, y_end, name in band_configs:
        band_img = img.crop((0, y_start, 320, y_end))
        enlarged_band = band_img.resize((1280, (y_end - y_start) * 4), Image.NEAREST)
        
        # Paste the band
        overview_img.paste(enlarged_band, (0, current_y))
        
        # Add label
        draw.text((10, current_y + 5), f"{name} (y={y_start}-{y_end})", fill=(200, 200, 200))
        
        current_y += (y_end - y_start) * 4 + 30  # Add spacing
    
    overview_file = output_dir / "all_bands_combined.png"
    overview_img.save(overview_file)
    print(f"Saved combined overview: {overview_file}")
    
    print(f"\nAll exact replica images saved to: {output_dir}")


def main():
    """Main function for exact replica creation."""
    print("Creating Exact Replica Using Documented Success Method")
    print("=" * 65)
    
    create_exact_replica()
    
    print("\nThe extraction used the exact parameters that were documented")
    print("as successful in the project's analysis:")
    print("- Sequential planar format")
    print("- 320x200 resolution")
    print("- 4-bit grayscale values (0-15) as intensity")
    print("- MSB-first bit ordering") 
    print("- Plane order [3, 0, 2, 1]")
    print("- First 32,000 bytes contain the main texture atlas")


if __name__ == "__main__":
    main()