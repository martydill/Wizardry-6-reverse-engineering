from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

from bane.data.sprite_decoder import decode_mazedata_tiles
def parse_records(data: bytes):
    tile_count = data[0] | (data[1] << 8)
    record_count = data[2] | (data[3] << 8)
    display_start = 4 + tile_count * 5
    raw = data[display_start : display_start + record_count * 5]
    records = []
    for i in range(record_count):
        b = raw[i * 5 : i * 5 + 5]
        if len(b) < 5:
            break
        records.append(
            type(
                "R",
                (),
                {
                    "record_index": i,
                    "owner_id": b[0],
                    "tile_ref": b[1],
                    "x": b[2],
                    "y": b[3],
                    "aux": b[4],
                },
            )()
        )
    return tile_count, record_count, records


@dataclass
class OwnerSummary:
    owner_id: int
    record_count: int
    drawable_count: int
    render_x0: int
    render_y0: int
    render_x1: int
    render_y1: int
    render_w: int
    render_h: int
    render_area: int
    tile_refs: list[int]


def render_owner_image(owner_records, sprites, canvas=(200, 140)) -> Image.Image:
    im = Image.new("RGB", canvas, (0, 0, 0))
    for r in owner_records:
        t = r.tile_ref
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if idx < 0 or idx >= len(sprites):
            continue
        sp = sprites[idx]
        tile = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
        im.paste(tile, (r.x, r.y))
    return im


def bounding_box_from_records(owner_records, sprites) -> tuple[int, int, int, int, int]:
    boxes = []
    for r in owner_records:
        t = r.tile_ref
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if idx < 0 or idx >= len(sprites):
            continue
        sp = sprites[idx]
        boxes.append((r.x, r.y, r.x + sp.width - 1, r.y + sp.height - 1))
    if not boxes:
        return 0, 0, 0, 0, 0
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return x0, y0, x1, y1, len(boxes)


def image_distance(a: Image.Image, b: Image.Image) -> int:
    diff = ImageChops.difference(a, b)
    h = diff.histogram()
    # Sum of channel differences weighted by intensity bucket.
    return sum(i * n for i, n in enumerate(h))


def main() -> None:
    ap = argparse.ArgumentParser(description="Infer MAZEDATA owner slot taxonomy from composite geometry")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--output", type=Path, default=Path("scratch/owner_slot_taxonomy"))
    args = ap.parse_args()

    mpath = args.gamedata / "MAZEDATA.EGA"
    raw = mpath.read_bytes()
    _, _, records = parse_records(raw)
    sprites = decode_mazedata_tiles(mpath)

    by_owner: dict[int, list] = defaultdict(list)
    for r in records:
        by_owner[r.owner_id].append(r)

    summaries: list[OwnerSummary] = []
    rendered: dict[int, Image.Image] = {}
    for oid in sorted(by_owner):
        rs = by_owner[oid]
        x0, y0, x1, y1, dc = bounding_box_from_records(rs, sprites)
        w = (x1 - x0 + 1) if dc else 0
        h = (y1 - y0 + 1) if dc else 0
        tile_refs = [r.tile_ref for r in rs]
        summaries.append(
            OwnerSummary(
                owner_id=oid,
                record_count=len(rs),
                drawable_count=dc,
                render_x0=x0,
                render_y0=y0,
                render_x1=x1,
                render_y1=y1,
                render_w=w,
                render_h=h,
                render_area=w * h,
                tile_refs=tile_refs,
            )
        )
        rendered[oid] = render_owner_image(rs, sprites)

    # Exact structural duplicates.
    sig_map: dict[tuple, list[int]] = defaultdict(list)
    for s in summaries:
        sig = (s.record_count, tuple(s.tile_refs))
        sig_map[sig].append(s.owner_id)
    exact_duplicate_groups = [ids for ids in sig_map.values() if len(ids) > 1]

    # Mirror candidates: compare each owner with horizontally flipped others.
    mirror_pairs: list[tuple[int, int, int]] = []
    owners = [s.owner_id for s in summaries]
    for i, a in enumerate(owners):
        fa = ImageOps.mirror(rendered[a])
        best_b = None
        best_d = None
        for b in owners:
            if a == b:
                continue
            d = image_distance(fa, rendered[b])
            if best_d is None or d < best_d:
                best_d = d
                best_b = b
        if best_b is not None and best_d is not None:
            mirror_pairs.append((a, best_b, best_d))

    # Keep only strong mirror candidates by ranking percentile.
    mirror_pairs.sort(key=lambda t: t[2])
    keep_n = min(60, len(mirror_pairs))
    top_mirror = mirror_pairs[:keep_n]

    # Group by rendered bbox footprint; this often maps to perspective slot families.
    bbox_groups: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
    for s in summaries:
        key = (s.render_x0, s.render_y0, s.render_w, s.render_h)
        bbox_groups[key].append(s.owner_id)
    bbox_groups_sorted = sorted(
        ((k, v) for k, v in bbox_groups.items()),
        key=lambda kv: len(kv[1]),
        reverse=True,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    out = {
        "owner_count": len(summaries),
        "summaries": [asdict(s) for s in summaries],
        "exact_duplicate_groups": exact_duplicate_groups,
        "top_mirror_candidates": [
            {"owner": a, "mirror_of": b, "distance": d} for a, b, d in top_mirror
        ],
        "bbox_groups": [
            {
                "bbox_key": {"x0": k[0], "y0": k[1], "w": k[2], "h": k[3]},
                "owners": v,
            }
            for k, v in bbox_groups_sorted
        ],
    }
    (args.output / "owner_taxonomy.json").write_text(json.dumps(out, indent=2))

    print(f"Wrote: {args.output / 'owner_taxonomy.json'}")
    print(f"Owner count: {len(summaries)}")
    print(f"Exact duplicate groups: {len(exact_duplicate_groups)}")
    print(f"Top bbox group size: {len(bbox_groups_sorted[0][1]) if bbox_groups_sorted else 0}")


if __name__ == "__main__":
    main()
