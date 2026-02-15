"""Create contact sheets of extracted MAZEDATA tiles for visual inspection."""

import sys
from pathlib import Path
from PIL import Image

def create_contact_sheet(tile_dir: Path, output_path: Path, max_tiles: int = 64, cols: int = 8):
    """Create a contact sheet from tiles."""
    # Find all PNG files
    tiles = sorted(tile_dir.glob("tile_*.png"))[:max_tiles]

    if not tiles:
        print(f"No tiles found in {tile_dir}")
        return

    # Load first tile to get size
    first_img = Image.open(tiles[0])
    tile_w, tile_h = first_img.size

    # Calculate grid dimensions
    rows = (len(tiles) + cols - 1) // cols

    # Create contact sheet
    sheet = Image.new("RGB", (tile_w * cols, tile_h * rows), (0, 0, 0))

    for idx, tile_path in enumerate(tiles):
        x = (idx % cols) * tile_w
        y = (idx // cols) * tile_h

        try:
            img = Image.open(tile_path)
            # Resize if needed
            if img.size != (tile_w, tile_h):
                img = img.resize((tile_w, tile_h), Image.NEAREST)
            sheet.paste(img, (x, y))
        except Exception as e:
            print(f"Failed to load {tile_path}: {e}")

    sheet.save(output_path)
    print(f"Created contact sheet: {output_path} ({len(tiles)} tiles)")

def main():
    # Compare different extraction methods
    base_dir = Path("output")

    # Fixed extraction (our new method)
    if (base_dir / "mazedata_fixed").exists():
        create_contact_sheet(
            base_dir / "mazedata_fixed",
            base_dir / "mazedata_fixed_sheet.png",
            max_tiles=64,
            cols=8
        )

    # V3 extraction
    if (base_dir / "mazedata_v3").exists():
        create_contact_sheet(
            base_dir / "mazedata_v3",
            base_dir / "mazedata_v3_sheet.png",
            max_tiles=64,
            cols=8
        )

    # Dump extraction
    if (base_dir / "mazedata_dump" / "desc_base02A00_u4").exists():
        create_contact_sheet(
            base_dir / "mazedata_dump" / "desc_base02A00_u4",
            base_dir / "mazedata_dump_sheet.png",
            max_tiles=64,
            cols=8
        )

if __name__ == "__main__":
    main()
