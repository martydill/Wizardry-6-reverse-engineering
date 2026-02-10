"""Quick viewer to compare different mazedata decodings."""

from pathlib import Path
from PIL import Image
import sys

def show_image(path):
    """Display image info and open it."""
    if not path.exists():
        print(f"File not found: {path}")
        return

    img = Image.open(path)
    print(f"\n{path.name}")
    print(f"  Size: {img.size}")
    print(f"  Mode: {img.mode}")

    # Show a sample of pixels from different regions
    # Top-left corner
    tl = img.getpixel((0, 0)) if img.mode == "RGB" else img.getpixel((0, 0))
    # Center
    cx, cy = img.size[0] // 2, img.size[1] // 2
    center = img.getpixel((cx, cy))
    # Check if image has actual content (not all black)
    unique_colors = set()
    for x in range(0, min(img.size[0], 100), 10):
        for y in range(0, min(img.size[1], 100), 10):
            unique_colors.add(img.getpixel((x, y)))

    print(f"  Colors in sample: {len(unique_colors)}")

    # Don't open viewer automatically
    # img.show()

def compare_images():
    """Compare different decoding attempts."""
    output_dir = Path("output")

    candidates = [
        "mazedata_atlas_skip0.png",
        "mazedata_atlas_skip2.png",
        "mazedata_atlas_skip31.png",
        "mazedata_320x200_skip0.png",
        "mazedata_sequential_planar_skip0.png",
    ]

    print("Comparing MAZEDATA.EGA decoding attempts:")
    print("=" * 70)

    for filename in candidates:
        path = output_dir / filename
        if path.exists():
            show_image(path)

    print("\nRecommendation: Look for the image that shows clear wall textures")
    print("in a grid pattern, not noise or garbled graphics.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        show_image(Path(sys.argv[1]))
    else:
        compare_images()
