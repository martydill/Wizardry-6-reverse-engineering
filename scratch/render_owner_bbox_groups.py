from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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


def render_owner(owner_records, sprites, canvas=(200, 140)) -> Image.Image:
    im = Image.new("RGB", canvas, (8, 8, 12))
    draw = ImageDraw.Draw(im)
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


def owner_bbox(owner_records, sprites) -> tuple[int, int, int, int]:
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
        return (0, 0, 0, 0)
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return x0, y0, x1 - x0 + 1, y1 - y0 + 1


def main() -> None:
    ap = argparse.ArgumentParser(description="Render MAZEDATA owners grouped by bbox family")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--output", type=Path, default=Path("scratch/owner_bbox_groups"))
    args = ap.parse_args()

    path = args.gamedata / "MAZEDATA.EGA"
    raw = path.read_bytes()
    _, _, records = parse_records(raw)
    sprites = decode_mazedata_tiles(path)

    by_owner = defaultdict(list)
    for r in records:
        by_owner[r.owner_id].append(r)

    owners = sorted(by_owner.keys())
    rendered = {oid: render_owner(by_owner[oid], sprites) for oid in owners}
    groups = defaultdict(list)
    for oid in owners:
        k = owner_bbox(by_owner[oid], sprites)
        groups[k].append(oid)

    # Sort biggest groups first.
    group_items = sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)

    args.output.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default()
    manifest = []

    for gi, (bbox, owner_ids) in enumerate(group_items):
        cols = 4
        thumb_w, thumb_h = 200, 140
        rows = (len(owner_ids) + cols - 1) // cols
        header_h = 26
        sheet = Image.new("RGB", (cols * thumb_w, header_h + rows * thumb_h), (0, 0, 0))
        draw = ImageDraw.Draw(sheet)
        draw.text((6, 6), f"group={gi} bbox={bbox} owners={owner_ids}", fill=(220, 220, 220), font=font)

        for i, oid in enumerate(owner_ids):
            x = (i % cols) * thumb_w
            y = header_h + (i // cols) * thumb_h
            card = rendered[oid].copy()
            cd = ImageDraw.Draw(card)
            cd.rectangle((0, 0, thumb_w - 1, thumb_h - 1), outline=(80, 80, 90))
            cd.text((4, 4), f"owner {oid:03d}", fill=(255, 255, 255), font=font)
            sheet.paste(card, (x, y))

        out = args.output / f"group_{gi:03d}.png"
        sheet.save(out)
        manifest.append(
            {
                "group_index": gi,
                "bbox": {"x0": bbox[0], "y0": bbox[1], "w": bbox[2], "h": bbox[3]},
                "owners": owner_ids,
                "image": str(out),
            }
        )

    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Wrote groups: {len(group_items)}")
    print(f"Manifest: {args.output / 'manifest.json'}")


if __name__ == "__main__":
    main()
