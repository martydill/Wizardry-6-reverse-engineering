"""Generate monster sprite sheets from all MON*.PIC files.

Outputs:
  output/monsters/MON00.png … MON58.png  — per-monster sheet (all frames)
  output/monsters/overview.png            — combined grid of all monsters

Usage:
    python -m loaders.extract_pic_sprites
    python -m loaders.extract_pic_sprites --transparent 15
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))

from bane.data.pic_decoder import decode_pic_frames
from bane.data.sprite_decoder import Sprite

# Background colour used behind sprites in the output PNG
BG = (20, 20, 30)
# Highlight border colour around each frame cell
BORDER = (60, 60, 80)
# Cell padding (pixels around each frame)
PAD = 4
# Scale factor applied to every frame when rendering
SCALE = 4


def sprite_to_image(sprite: Sprite, transparent_index: int = 15) -> Image.Image:
    """Convert a Sprite to a PIL RGBA Image."""
    rgba = sprite.to_rgba_bytes(transparent_index=transparent_index)
    return Image.frombytes("RGBA", (sprite.width, sprite.height), rgba)


def make_monster_sheet(frames: list[Sprite], transparent_index: int) -> Image.Image:
    """Arrange all frames of one monster into a horizontal strip."""
    if not frames:
        return Image.new("RGBA", (8, 8), (0, 0, 0, 0))

    # Scale frames and compute layout
    imgs = [sprite_to_image(f, transparent_index).resize(
        (f.width * SCALE, f.height * SCALE), Image.NEAREST) for f in frames]

    max_h = max(im.height for im in imgs)
    total_w = sum(im.width + PAD * 2 for im in imgs) + PAD
    total_h = max_h + PAD * 2

    sheet = Image.new("RGBA", (total_w, total_h), (*BG, 255))
    draw = ImageDraw.Draw(sheet)

    x = PAD
    for im in imgs:
        y = PAD + (max_h - im.height) // 2
        draw.rectangle([x - 1, PAD - 1, x + im.width, PAD + max_h], outline=BORDER)
        sheet.alpha_composite(im, (x, y))
        x += im.width + PAD * 2

    return sheet


def make_overview(
    monsters: list[tuple[str, list[Sprite]]],
    transparent_index: int,
    cols: int = 6,
    cell_size: int = 160,
) -> Image.Image:
    """One cell per monster showing its largest frame, scaled to fit cell_size×cell_size."""
    if not monsters:
        return Image.new("RGB", (1, 1))

    LABEL_H = 14
    rows = (len(monsters) + cols - 1) // cols
    img = Image.new("RGB", (cols * cell_size, rows * (cell_size + LABEL_H)), BG)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    for idx, (name, frames) in enumerate(monsters):
        col = idx % cols
        row = idx // cols
        ox = col * cell_size
        oy = row * (cell_size + LABEL_H)

        # Pick the largest frame (by pixel area) as the representative thumbnail
        best = max(frames, key=lambda f: f.width * f.height)
        im = sprite_to_image(best, transparent_index)

        # Scale to fit within cell_size, preserving aspect ratio
        scale = min(cell_size / im.width, cell_size / im.height)
        new_w = max(1, int(im.width * scale))
        new_h = max(1, int(im.height * scale))
        im = im.resize((new_w, new_h), Image.NEAREST)

        # Composite onto dark background cell
        cell = Image.new("RGB", (cell_size, cell_size), BG)
        px = (cell_size - new_w) // 2
        py = (cell_size - new_h) // 2
        cell.paste(im, (px, py), mask=im.split()[3])
        img.paste(cell, (ox, oy))

        draw.text((ox + 2, oy + cell_size + 1), name, fill=(180, 180, 180), font=font)

    return img


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Wizardry 6 monster sprite sheets")
    parser.add_argument(
        "--gamedata", type=Path, default=Path("gamedata"),
        help="Directory containing MON*.PIC files",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/monsters"),
        help="Output directory",
    )
    parser.add_argument(
        "--transparent", type=int, default=15,
        help="Palette index treated as transparent (default: 15)",
    )
    parser.add_argument(
        "--cols", type=int, default=6,
        help="Columns in the overview sheet",
    )
    args = parser.parse_args()

    pic_files = sorted(args.gamedata.glob("MON*.PIC"))
    if not pic_files:
        print(f"No MON*.PIC files found in {args.gamedata}")
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    overview_data: list[tuple[str, list[Sprite]]] = []

    for pic_path in pic_files:
        try:
            frames = decode_pic_frames(pic_path.read_bytes())
        except Exception as exc:
            print(f"  ERROR decoding {pic_path.name}: {exc}")
            continue

        if not frames:
            print(f"  {pic_path.name}: 0 frames (skipped)")
            continue

        sheet = make_monster_sheet(frames, args.transparent)
        out_path = args.output / f"{pic_path.stem}.png"
        sheet.save(out_path)
        sizes = ", ".join(f"{f.width}x{f.height}" for f in frames)
        print(f"  {pic_path.name}: {len(frames)} frames [{sizes}]  -> {out_path}")
        overview_data.append((pic_path.stem, frames))

    if overview_data:
        overview = make_overview(overview_data, args.transparent, cols=args.cols)
        ov_path = args.output / "overview.png"
        overview.save(ov_path)
        print(f"\nOverview sheet: {ov_path} ({overview.width}x{overview.height})")

    print("Done.")


if __name__ == "__main__":
    main()
