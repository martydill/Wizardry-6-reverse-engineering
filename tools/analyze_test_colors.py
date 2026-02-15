"""Analyze color distribution in MAZEDATA test outputs."""

from pathlib import Path
from PIL import Image

def analyze_colors():
    dirs = [Path("output/mazedata_linear_extracted/64x64")]
    
    for test_dir in dirs:
        if not test_dir.exists():
            continue
        print(f"\n--- Analyzing directory: {test_dir} ---")
        # Sample first few files
        count = 0
        for path in sorted(test_dir.glob("tile_*.png")):
            if count > 10: break
            print(f"\nAnalyzing {path.name}:")
            img = Image.open(path)
            colors = img.getcolors(maxcolors=256)
            if not colors:
                print("  No colors found")
                continue
                
            colors.sort(key=lambda x: x[0], reverse=True)
            
            gray_count = 0
            total_pixels = img.width * img.height
            
            for c_count, rgb in colors[:10]:
                is_gray = (rgb[0] == rgb[1] == rgb[2])
                gray_mark = "*" if is_gray else " "
                print(f"  {gray_mark} {rgb}: {c_count:4d} ({c_count/total_pixels*100:4.1f}%)")
                if is_gray:
                    gray_count += c_count
                    
            print(f"  Total gray pixels: {gray_count} ({gray_count/total_pixels*100:4.1f}%)")
            count += 1

if __name__ == "__main__":
    analyze_colors()
