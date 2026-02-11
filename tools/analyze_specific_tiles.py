"""Analyze color distribution in specific MAZEDATA tiles."""

from pathlib import Path
from PIL import Image

def analyze_specific_tiles():
    target_dir = Path("output/mazedata_extracted_v5/atlas_1_64x64")
    
    # Analyze all 64x64 tiles in atlas 1
    for path in sorted(target_dir.glob("tile_*.png")):
            
        print(f"\nAnalyzing {path.name}:")
        img = Image.open(path)
        colors = img.getcolors(maxcolors=256)
        if not colors:
            print("  No colors found")
            continue
            
        colors.sort(key=lambda x: x[0], reverse=True)
        
        gray_count = 0
        total_pixels = img.width * img.height
        
        for count, rgb in colors[:5]:
            is_gray = (rgb[0] == rgb[1] == rgb[2])
            gray_mark = "*" if is_gray else " "
            print(f"  {gray_mark} {rgb}: {count:4d} ({count/total_pixels*100:4.1f}%)")
            if is_gray:
                gray_count += count
                
        print(f"  Total gray pixels: {gray_count} ({gray_count/total_pixels*100:4.1f}%)")

if __name__ == "__main__":
    analyze_specific_tiles()
