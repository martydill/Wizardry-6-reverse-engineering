from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def run_renderer(
    python_exe: str,
    map_id: int,
    wx: int | None,
    wy: int | None,
    facing: str,
    slot_candidates: Path,
    out_path: Path,
    override: str,
) -> None:
    cmd = [
        python_exe,
        "scratch/render_map_3d_owner_prototype.py",
        "--map-id",
        str(map_id),
        "--facing",
        facing,
        "--slot-candidates",
        str(slot_candidates),
        "--out",
        str(out_path),
        "--override",
        override,
    ]
    if wx is not None:
        cmd.extend(["--wx", str(wx)])
    if wy is not None:
        cmd.extend(["--wy", str(wy)])
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate per-slot candidate scene sheet for manual mapping calibration")
    ap.add_argument("--map-id", type=int, default=10)
    ap.add_argument("--wx", type=int, default=None)
    ap.add_argument("--wy", type=int, default=None)
    ap.add_argument("--facing", choices=["N", "E", "S", "W"], default="N")
    ap.add_argument("--wall", type=int, choices=[1, 2, 3], default=2)
    ap.add_argument("--slot", type=str, default="center_d2")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument(
        "--slot-candidates",
        type=Path,
        default=Path("scratch/owner_slot_candidates/slot_candidates.json"),
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("scratch/slot_candidate_sheets"),
    )
    args = ap.parse_args()

    data = json.loads(args.slot_candidates.read_text())
    per_val = data.get("slot_candidates_by_wall_value", {})
    lst = per_val.get(str(args.wall), {}).get(args.slot)
    if not lst:
        lst = data.get("slot_candidates", {}).get(args.slot, [])
    lst = lst[: max(1, args.top)]
    if not lst:
        raise RuntimeError(f"No candidates found for wall={args.wall} slot={args.slot}")

    tmp_dir = args.output / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    shots: list[tuple[int, Path]] = []
    for owner in lst:
        override = f"{args.wall}:{args.slot}={owner}"
        out = tmp_dir / f"scene_{args.wall}_{args.slot}_{owner:03d}.png"
        run_renderer(
            sys.executable,
            args.map_id,
            args.wx,
            args.wy,
            args.facing,
            args.slot_candidates,
            out,
            override,
        )
        shots.append((owner, out))

    # Build sheet.
    thumbs = []
    for owner, p in shots:
        im = Image.open(p).convert("RGB")
        card = Image.new("RGB", (im.width, im.height + 20), (8, 8, 12))
        card.paste(im, (0, 20))
        draw = ImageDraw.Draw(card)
        draw.text((4, 4), f"owner={owner}", fill=(230, 230, 230))
        thumbs.append(card)

    cols = 4
    tw, th = thumbs[0].size
    rows = (len(thumbs) + cols - 1) // cols
    head = 26
    sheet = Image.new("RGB", (cols * tw, head + rows * th), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (6, 6),
        f"map={args.map_id} pos=({args.wx},{args.wy}) facing={args.facing} wall={args.wall} slot={args.slot}",
        fill=(230, 230, 230),
    )
    for i, t in enumerate(thumbs):
        x = (i % cols) * tw
        y = head + (i // cols) * th
        sheet.paste(t, (x, y))

    args.output.mkdir(parents=True, exist_ok=True)
    out_name = f"sheet_map{args.map_id}_{args.facing}_w{args.wall}_{args.slot}.png"
    out_path = args.output / out_name
    sheet.save(out_path)
    print(f"Wrote {out_path}")
    print(f"Candidates: {lst}")


if __name__ == "__main__":
    main()
