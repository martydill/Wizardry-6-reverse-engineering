"""Brute-force scan PIC decoding layouts and emit a contact sheet.

Usage:
    python -m tools.pic_scan gamedata/MON00.PIC --out mon00_scan.png
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from bane.data.pic_decoder import PIC_HEIGHT, PIC_WIDTH, decode_pic_file


@dataclass(frozen=True)
class Candidate:
    score: int
    layout: str
    plane_order: str
    header_skip: int
    sprite: object


def _score_sprite(pixels: list[int], width: int, height: int) -> int:
    """Heuristic: reward horizontal/vertical adjacency of equal colors."""
    score = 0
    for y in range(height):
        row = pixels[y * width:(y + 1) * width]
        score += sum(1 for i in range(1, width) if row[i] == row[i - 1])
    for x in range(width):
        col_prev = pixels[x]
        for y in range(1, height):
            v = pixels[y * width + x]
            if v == col_prev:
                score += 1
            col_prev = v
    return score


def _iter_candidates(
    layout_choices: Iterable[str],
    header_skips: Iterable[int],
    plane_orders: Iterable[str],
    file: Path,
    width: int,
    height: int,
) -> Iterable[Candidate]:
    for layout in layout_choices:
        for header_skip in header_skips:
            for plane_order in plane_orders:
                try:
                    sprite = decode_pic_file(
                        str(file),
                        width=width,
                        height=height,
                        layout=layout,
                        header_skip=header_skip,
                        plane_order=[int(ch) for ch in plane_order],
                    )
                except Exception:
                    continue
                score = _score_sprite(sprite.pixels, sprite.width, sprite.height)
                yield Candidate(score, layout, plane_order, header_skip, sprite)


def _render_contact_sheet(
    candidates: list[Candidate],
    out_path: Path,
    cols: int,
    scale: int,
) -> None:
    if not candidates:
        raise ValueError("No candidates to render")

    rows = (len(candidates) + cols - 1) // cols
    thumb_w = candidates[0].sprite.width * scale
    thumb_h = candidates[0].sprite.height * scale
    label_h = 28
    pad = 10

    sheet_w = cols * (thumb_w + pad) + pad
    sheet_h = rows * (thumb_h + label_h + pad) + pad
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (20, 20, 30, 255))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    for idx, cand in enumerate(candidates):
        r = idx // cols
        c = idx % cols
        x = pad + c * (thumb_w + pad)
        y = pad + r * (thumb_h + label_h + pad)

        rgba = cand.sprite.to_rgba_bytes()
        img = Image.frombytes("RGBA", (cand.sprite.width, cand.sprite.height), rgba)
        if scale != 1:
            img = img.resize((thumb_w, thumb_h), Image.NEAREST)
        sheet.alpha_composite(img, (x, y))

        label = f"{cand.layout} o={cand.plane_order} s={cand.header_skip}"
        draw.text((x, y + thumb_h + 4), label, fill=(220, 220, 220, 255), font=font)

    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-pic-scan",
        description="Brute-force scan PIC decoding layouts",
    )
    parser.add_argument("file", type=Path, help="Path to .PIC file")
    parser.add_argument("--out", type=Path, default=Path("pic_scan.png"))
    parser.add_argument("--width", type=int, default=PIC_WIDTH)
    parser.add_argument("--height", type=int, default=PIC_HEIGHT)
    parser.add_argument("--top", type=int, default=36, help="Number of top candidates")
    parser.add_argument("--cols", type=int, default=6, help="Columns in contact sheet")
    parser.add_argument("--scale", type=int, default=1, help="Thumbnail scale")
    args = parser.parse_args()

    layouts = ["planar", "planar-lsb", "planar-row", "planar-row-lsb"]
    header_skips = [0, 1, 2, 4, 8, 16, 32, 64]
    plane_orders = ["".join(p) for p in itertools.permutations("0123")]

    candidates = list(
        _iter_candidates(
            layouts, header_skips, plane_orders, args.file, args.width, args.height
        )
    )
    candidates.sort(key=lambda c: c.score, reverse=True)
    top = candidates[: max(1, args.top)]

    _render_contact_sheet(top, args.out, cols=args.cols, scale=max(1, args.scale))


if __name__ == "__main__":
    main()
