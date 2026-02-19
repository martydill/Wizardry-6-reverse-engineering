from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def run_renderer(
    map_id: int,
    wx: int,
    wy: int,
    facing: str,
    mode: str,
    out_png: Path,
    out_json: Path,
) -> None:
    cmd = [
        sys.executable,
        "scratch/render_map_3d_owner_prototype.py",
        "--map-id",
        str(map_id),
        "--wx",
        str(wx),
        "--wy",
        str(wy),
        "--facing",
        facing,
        "--use-map-streams",
        "--use-stream-offsets",
        "--stream-high-mode",
        mode,
        "--out",
        str(out_png),
        "--debug-json",
        str(out_json),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Render minus28/highbit side-by-side for top high-code viewpoints.")
    ap.add_argument(
        "--candidates",
        type=Path,
        default=Path("scratch/map_owner_streams/high_code_viewpoints.json"),
    )
    ap.add_argument("--per-map", type=int, default=6, help="Rows per map.")
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path("scratch/proto_decode_compare/batch"),
    )
    ap.add_argument(
        "--sheet",
        type=Path,
        default=Path("scratch/proto_decode_compare/decode_mode_sheet.png"),
    )
    args = ap.parse_args()

    data = json.loads(args.candidates.read_text())
    rows: list[dict[str, object]] = []

    for map_key in sorted(data.get("maps", {}).keys(), key=lambda s: int(s)):
        top = data["maps"][map_key].get("top_candidates", [])[: args.per_map]
        for c in top:
            rows.append(
                {
                    "map_id": int(map_key),
                    "wx": int(c["wx"]),
                    "wy": int(c["wy"]),
                    "facing": str(c["facing"]),
                }
            )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for row in rows:
        map_id = int(row["map_id"])
        wx = int(row["wx"])
        wy = int(row["wy"])
        facing = str(row["facing"])
        stem = f"m{map_id:02d}_{wx}_{wy}_{facing}"
        minus_png = args.out_dir / f"{stem}_minus28.png"
        minus_json = args.out_dir / f"{stem}_minus28.json"
        high_png = args.out_dir / f"{stem}_highbit.png"
        high_json = args.out_dir / f"{stem}_highbit.json"
        run_renderer(map_id, wx, wy, facing, "minus28", minus_png, minus_json)
        run_renderer(map_id, wx, wy, facing, "highbit", high_png, high_json)
        rendered.append((row, minus_png, high_png))

    tile_w = 176
    tile_h = 112
    label_h = 18
    gap_x = 8
    gap_y = 6
    margin = 10

    cols = 2
    rows_n = len(rendered)
    canvas_w = margin * 2 + cols * tile_w + (cols - 1) * gap_x
    canvas_h = margin * 2 + rows_n * (label_h + tile_h + gap_y)
    sheet = Image.new("RGB", (canvas_w, canvas_h), (12, 14, 20))
    draw = ImageDraw.Draw(sheet)

    y = margin
    for row, minus_png, high_png in rendered:
        label = f"map {row['map_id']:02d} ({row['wx']},{row['wy']}) {row['facing']}"
        draw.text((margin, y), label, fill=(220, 220, 220))
        draw.text((margin + tile_w + gap_x, y), "highbit", fill=(220, 220, 220))
        draw.text((margin, y + 2), "minus28", fill=(220, 220, 220))

        a = Image.open(minus_png).convert("RGB")
        b = Image.open(high_png).convert("RGB")
        sheet.paste(a, (margin, y + label_h))
        sheet.paste(b, (margin + tile_w + gap_x, y + label_h))
        y += label_h + tile_h + gap_y

    args.sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.sheet)
    print(f"Wrote {args.sheet}")


if __name__ == "__main__":
    main()
