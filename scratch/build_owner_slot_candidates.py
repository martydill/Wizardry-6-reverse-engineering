from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from bane.data.sprite_decoder import decode_mazedata_tiles


@dataclass
class OwnerGeom:
    owner_id: int
    x0: int
    y0: int
    x1: int
    y1: int
    w: int
    h: int
    area: int
    cx: float
    cy: float
    drawable_records: int
    total_records: int
    warm_ratio: float


def parse_records(data: bytes):
    tile_count = data[0] | (data[1] << 8)
    record_count = data[2] | (data[3] << 8)
    start = 4 + tile_count * 5
    raw = data[start : start + record_count * 5]
    recs = []
    for i in range(record_count):
        b = raw[i * 5 : i * 5 + 5]
        if len(b) < 5:
            break
        recs.append(
            {
                "owner_id": b[0],
                "tile_ref": b[1],
                "x": b[2],
                "y": b[3],
                "aux": b[4],
            }
        )
    return recs


def render_owner(owner_records, sprites, canvas=(200, 140)) -> Image.Image:
    im = Image.new("RGBA", canvas, (0, 0, 0, 0))
    for r in owner_records:
        t = r["tile_ref"]
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if idx < 0 or idx >= len(sprites):
            continue
        sp = sprites[idx]
        rgb = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
        rgba = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
        rgba.paste(rgb, (0, 0))
        # Consider non-zero RGB as opaque; black remains transparent.
        px = rgba.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                rr, gg, bb, _ = px[x, y]
                if rr == 0 and gg == 0 and bb == 0:
                    px[x, y] = (0, 0, 0, 0)
                else:
                    px[x, y] = (rr, gg, bb, 255)
        im.alpha_composite(rgba, (r["x"], r["y"]))
    return im


def owner_geom(owner_id: int, rs, sprites) -> OwnerGeom:
    boxes = []
    dc = 0
    for r in rs:
        t = r["tile_ref"]
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if idx < 0 or idx >= len(sprites):
            continue
        sp = sprites[idx]
        boxes.append((r["x"], r["y"], r["x"] + sp.width - 1, r["y"] + sp.height - 1))
        dc += 1
    if not boxes:
        return OwnerGeom(owner_id, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0, 0, len(rs), 0.0)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    w = x1 - x0 + 1
    h = y1 - y0 + 1
    # Warm pixel ratio heuristic (door/brick-like slices tend to be warm).
    warm = 0
    total = 0
    rim = render_owner(rs, sprites)
    rp = rim.load()
    for y in range(rim.height):
        for x in range(rim.width):
            rr, gg, bb, aa = rp[x, y]
            if aa == 0:
                continue
            total += 1
            if rr > 80 and rr > gg + 20 and rr > bb + 20:
                warm += 1
    warm_ratio = (warm / total) if total else 0.0

    return OwnerGeom(
        owner_id=owner_id,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        w=w,
        h=h,
        area=w * h,
        cx=(x0 + x1) / 2.0,
        cy=(y0 + y1) / 2.0,
        drawable_records=dc,
        total_records=len(rs),
        warm_ratio=warm_ratio,
    )


def orientation_for_geom(g: OwnerGeom) -> str:
    if g.w == 0 or g.h == 0:
        return "none"
    if g.cx < 74:
        return "left"
    if g.cx > 102:
        return "right"
    return "center"


def rank_depths(geoms: list[OwnerGeom]) -> dict[int, int]:
    # Near -> far buckets based on area, 4 bands.
    vals = sorted((g.area, g.owner_id) for g in geoms if g.area > 0)
    if not vals:
        return {}
    n = len(vals)
    out: dict[int, int] = {}
    for i, (_, oid) in enumerate(vals):
        q = i / max(1, n - 1)
        if q < 0.25:
            depth = 1
        elif q < 0.50:
            depth = 2
        elif q < 0.75:
            depth = 3
        else:
            depth = 4
        out[oid] = depth
    return out


def mirror_distance(a: Image.Image, b: Image.Image) -> int:
    # Compare alpha mask only.
    am = a.split()[-1]
    bm = b.split()[-1]
    fm = ImageOps.mirror(am)
    if fm.size != bm.size:
        return 1 << 30
    ap = fm.tobytes()
    bp = bm.tobytes()
    return sum(abs(x - y) for x, y in zip(ap, bp))


def make_slot_sheet(slot_key: str, owners: list[int], rendered: dict[int, Image.Image], out: Path) -> None:
    if not owners:
        return
    tw, th = 200, 140
    cols = 4
    rows = (len(owners) + cols - 1) // cols
    head = 24
    sheet = Image.new("RGBA", (cols * tw, head + rows * th), (8, 8, 12, 255))
    draw = ImageDraw.Draw(sheet)
    draw.text((6, 6), f"{slot_key} owners={owners}", fill=(230, 230, 230, 255))
    for i, oid in enumerate(owners):
        x = (i % cols) * tw
        y = head + (i // cols) * th
        card = rendered[oid].copy().convert("RGBA")
        cd = ImageDraw.Draw(card)
        cd.rectangle((0, 0, tw - 1, th - 1), outline=(80, 80, 90, 255))
        cd.text((4, 4), f"owner {oid:03d}", fill=(255, 255, 255, 255))
        sheet.alpha_composite(card, (x, y))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Build provisional MAZEDATA owner slot candidates")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--output", type=Path, default=Path("scratch/owner_slot_candidates"))
    args = ap.parse_args()

    mpath = args.gamedata / "MAZEDATA.EGA"
    data = mpath.read_bytes()
    recs = parse_records(data)
    sprites = decode_mazedata_tiles(mpath)

    by_owner: dict[int, list[dict]] = defaultdict(list)
    for r in recs:
        by_owner[r["owner_id"]].append(r)

    owners = sorted(by_owner.keys())
    rendered: dict[int, Image.Image] = {}
    geoms: dict[int, OwnerGeom] = {}
    for oid in owners:
        rs = by_owner[oid]
        rendered[oid] = render_owner(rs, sprites)
        geoms[oid] = owner_geom(oid, rs, sprites)

    orient_groups: dict[str, list[OwnerGeom]] = defaultdict(list)
    for oid in owners:
        g = geoms[oid]
        orient_groups[orientation_for_geom(g)].append(g)

    slot_map: dict[str, list[int]] = {}
    for orient, gs in orient_groups.items():
        depth = rank_depths(gs)
        buckets: dict[int, list[OwnerGeom]] = defaultdict(list)
        for g in gs:
            d = depth.get(g.owner_id, 4)
            buckets[d].append(g)
        for d in sorted(buckets):
            # Keep only reasonably wall-like primitives.
            cand = [g for g in buckets[d] if g.w >= 8 and g.h >= 16]
            cand.sort(key=lambda x: x.area, reverse=True)
            slot_map[f"{orient}_d{d}"] = [c.owner_id for c in cand]

    # Wall-value-specific slot maps:
    # - value 3 tends to be special/door; prefer warm composites.
    # - value 1/2 prefer non-warm composites.
    slot_map_by_val: dict[str, dict[str, list[int]]] = {
        "1": {},
        "2": {},
        "3": {},
    }
    geom_by_oid = {g.owner_id: g for g in geoms.values()}
    for slot_key, ids in slot_map.items():
        cool = [oid for oid in ids if geom_by_oid[oid].warm_ratio < 0.10]
        warm = [oid for oid in ids if geom_by_oid[oid].warm_ratio >= 0.10]
        slot_map_by_val["1"][slot_key] = cool if cool else ids
        slot_map_by_val["2"][slot_key] = cool if cool else ids
        slot_map_by_val["3"][slot_key] = warm if warm else ids

    # Mirror hints (left<->right).
    left_ids = [g.owner_id for g in orient_groups.get("left", [])]
    right_ids = [g.owner_id for g in orient_groups.get("right", [])]
    mirror_hints = []
    for lid in left_ids:
        best = None
        best_d = None
        for rid in right_ids:
            d = mirror_distance(rendered[lid], rendered[rid])
            if best_d is None or d < best_d:
                best_d = d
                best = rid
        if best is not None:
            mirror_hints.append({"left_owner": lid, "right_owner": best, "distance": best_d})
    mirror_hints.sort(key=lambda x: x["distance"])

    args.output.mkdir(parents=True, exist_ok=True)
    for slot_key, ids in slot_map.items():
        make_slot_sheet(slot_key, ids[:16], rendered, args.output / f"{slot_key}.png")

    out = {
        "slot_candidates": slot_map,
        "slot_candidates_by_wall_value": slot_map_by_val,
        "owner_geoms": [asdict(geoms[o]) for o in owners],
        "mirror_hints_top": mirror_hints[:80],
    }
    (args.output / "slot_candidates.json").write_text(json.dumps(out, indent=2))
    print(f"Wrote: {args.output / 'slot_candidates.json'}")


if __name__ == "__main__":
    main()
