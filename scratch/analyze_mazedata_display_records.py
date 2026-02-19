from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw

from bane.data.sprite_decoder import decode_mazedata_tiles


@dataclass
class DisplayRecord:
    record_index: int
    owner_id: int
    tile_ref: int
    x: int
    y: int
    aux: int


def parse_records(data: bytes) -> tuple[int, int, list[DisplayRecord]]:
    tile_count = data[0] | (data[1] << 8)
    record_count = data[2] | (data[3] << 8)
    display_start = 4 + tile_count * 5
    raw = data[display_start : display_start + record_count * 5]

    records: list[DisplayRecord] = []
    for i in range(record_count):
        b = raw[i * 5 : i * 5 + 5]
        if len(b) < 5:
            break
        records.append(
            DisplayRecord(
                record_index=i,
                owner_id=b[0],
                tile_ref=b[1],
                x=b[2],
                y=b[3],
                aux=b[4],
            )
        )
    return tile_count, record_count, records


def build_owner_index(records: list[DisplayRecord]) -> dict[int, list[DisplayRecord]]:
    out: dict[int, list[DisplayRecord]] = defaultdict(list)
    for rec in records:
        out[rec.owner_id].append(rec)
    return out


def render_owner_composite(
    owner_id: int,
    owner_records: list[DisplayRecord],
    sprites,
    out_path: Path,
    canvas_size: tuple[int, int] = (176, 112),
) -> None:
    canvas = Image.new("RGB", canvas_size, (18, 18, 24))
    draw = ImageDraw.Draw(canvas)
    draw.text((3, 2), f"owner={owner_id}", fill=(220, 220, 220))

    for rec in owner_records:
        # Current best interpretation:
        # - tile_ref 1..153 maps to primitive tile index 0..152
        # - x,y are direct pixel coordinates
        # - tile_ref 0 and 255 are control/sentinel
        if rec.tile_ref in (0, 255):
            continue
        tile_idx = rec.tile_ref - 1
        if tile_idx < 0 or tile_idx >= len(sprites):
            continue
        sp = sprites[tile_idx]
        tile_img = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
        canvas.paste(tile_img, (rec.x, rec.y))
        draw.rectangle(
            [rec.x, rec.y, rec.x + sp.width - 1, rec.y + sp.height - 1],
            outline=(60, 60, 84),
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def write_contact_sheet(image_paths: list[Path], out_path: Path, cols: int = 10) -> None:
    if not image_paths:
        return
    thumbs: list[Image.Image] = []
    for p in image_paths:
        im = Image.open(p)
        w, h = im.size
        t = im.resize((max(1, w // 2), max(1, h // 2)), Image.NEAREST)
        draw = ImageDraw.Draw(t)
        draw.text((2, 2), p.stem.split("_")[-1], fill=(255, 255, 255))
        thumbs.append(t)

    tw, th = thumbs[0].size
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
    for i, t in enumerate(thumbs):
        x = (i % cols) * tw
        y = (i // cols) * th
        sheet.paste(t, (x, y))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze MAZEDATA.EGA display-record table")
    parser.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    parser.add_argument("--output", type=Path, default=Path("scratch/mazedata_display_analysis"))
    parser.add_argument("--preview-count", type=int, default=80)
    args = parser.parse_args()

    path = args.gamedata / "MAZEDATA.EGA"
    if not path.exists():
        raise FileNotFoundError(path)

    data = path.read_bytes()
    tile_count, record_count, records = parse_records(data)
    owners = build_owner_index(records)

    sprites = decode_mazedata_tiles(path)

    print(f"tile_count={tile_count}, display_record_count={record_count}")
    print(f"decoded_primitive_tiles={len(sprites)}")
    print(f"owner_id_count={len(owners)}")

    tile_ref_counter = Counter(r.tile_ref for r in records)
    owner_hist = Counter(len(v) for v in owners.values())
    print(f"owner record-count histogram: {dict(sorted(owner_hist.items()))}")
    print(f"top tile_ref values: {tile_ref_counter.most_common(20)}")

    # Emit machine-readable dump.
    dump = {
        "tile_count": tile_count,
        "record_count": record_count,
        "owner_id_count": len(owners),
        "owner_record_histogram": dict(sorted(owner_hist.items())),
        "tile_ref_top": tile_ref_counter.most_common(30),
        "records": [asdict(r) for r in records],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "display_records.json").write_text(json.dumps(dump, indent=2))

    # Render owner composites for quick visual validation.
    preview_paths: list[Path] = []
    for owner_id in sorted(owners.keys())[: max(1, args.preview_count)]:
        out_img = args.output / "owners" / f"owner_{owner_id:03d}.png"
        render_owner_composite(owner_id, owners[owner_id], sprites, out_img)
        preview_paths.append(out_img)

    write_contact_sheet(
        preview_paths,
        args.output / "owner_contact_sheet.png",
        cols=10,
    )
    print(f"Wrote analysis to: {args.output}")


if __name__ == "__main__":
    main()

