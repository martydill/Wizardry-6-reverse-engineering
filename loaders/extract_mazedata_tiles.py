"""Generate a sprite sheet of all MAZEDATA.EGA wall-texture tiles.

Outputs:
  output/mazedata/spritesheet.png  — all 153 tiles in a grid with labels

Usage:
    python -m loaders.extract_mazedata_tiles
    python -m loaders.extract_mazedata_tiles --cols 12 --scale 2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.sprite_decoder import decode_mazedata_tiles

BG = (20, 20, 30)
BORDER = (60, 60, 80)
PAD = 4
LABEL_H = 14


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract MAZEDATA.EGA tile sprite sheet")
    parser.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    parser.add_argument("--output", type=Path, default=Path("output/mazedata"))
    parser.add_argument("--cols", type=int, default=12, help="Columns in grid (default: 12)")
    parser.add_argument("--scale", type=int, default=2, help="Scale factor (default: 2)")
    args = parser.parse_args()

    path = args.gamedata / "MAZEDATA.EGA"
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    print(f"Decoding {path} ...")
    sprites = decode_mazedata_tiles(path)
    print(f"  {len(sprites)} tiles decoded")

    args.output.mkdir(parents=True, exist_ok=True)

    scale = max(1, args.scale)
    cols = max(1, args.cols)
    rows = (len(sprites) + cols - 1) // cols

    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except Exception:
        font = ImageFont.load_default()

    # First pass: compute max scaled dimensions per grid cell
    cell_w = max(sp.width * scale for sp in sprites) + PAD * 2
    cell_h = max(sp.height * scale for sp in sprites) + PAD * 2 + LABEL_H

    sheet_w = cell_w * cols
    sheet_h = cell_h * rows

    sheet = Image.new("RGB", (sheet_w, sheet_h), BG)
    draw = ImageDraw.Draw(sheet)

    for idx, sp in enumerate(sprites):
        col = idx % cols
        row = idx // cols
        ox = col * cell_w
        oy = row * cell_h

        # Label
        label = f"{idx} {sp.width}x{sp.height}"
        draw.text((ox + PAD, oy + 1), label, fill=(160, 160, 160), font=font)

        # Scale and paste sprite, centred in cell
        img = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
        img = img.resize((sp.width * scale, sp.height * scale), Image.NEAREST)

        px = ox + PAD + (cell_w - PAD * 2 - img.width) // 2
        py = oy + LABEL_H + (cell_h - LABEL_H - PAD * 2 - img.height) // 2
        sheet.paste(img, (px, py))
        draw.rectangle(
            [px - 1, py - 1, px + img.width, py + img.height],
            outline=BORDER,
        )

    out_path = args.output / "spritesheet.png"
    sheet.save(out_path)
    print(f"Saved: {out_path} ({sheet_w}x{sheet_h})")


if __name__ == "__main__":
    main()
