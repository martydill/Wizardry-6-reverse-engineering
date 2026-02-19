from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from bane.data.sprite_decoder import decode_mazedata_tiles


MAP_PATH = Path("gamedata/NEWGAME.DBS")
MAZE_PATH = Path("gamedata/MAZEDATA.EGA")
OUT_DIR = Path("scratch/map_owner_streams")

MAP_HEADER = 0x019E
MAP_REC = 0x0C0E
STREAM_WINDOW = 0x1B0


def parse_display_records(path: Path) -> list[dict]:
    data = path.read_bytes()
    n = data[0] | (data[1] << 8)
    n2 = data[2] | (data[3] << 8)
    start = 4 + n * 5
    out = []
    for i in range(n2):
        b = data[start + i * 5 : start + i * 5 + 5]
        out.append(
            {
                "owner_id": b[0],
                "tile_ref": b[1],
                "x": b[2],
                "y": b[3],
                "aux": b[4],
            }
        )
    return out


def owner_records(records: list[dict]) -> dict[int, list[dict]]:
    d: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        d[r["owner_id"]].append(r)
    return d


def render_owner(oid: int, recs: list[dict], sprites, size=(72, 96)) -> Image.Image:
    canvas = Image.new("RGBA", size, (8, 10, 20, 255))
    for r in recs:
        t = r["tile_ref"]
        if not (1 <= t <= len(sprites)):
            continue
        sp = sprites[t - 1]
        if sp.width <= 0 or sp.height <= 0:
            continue
        tile = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
        px = tile.load()
        idx = 0
        for yy in range(sp.height):
            for xx in range(sp.width):
                v = sp.pixels[idx]
                idx += 1
                if v != 0:
                    c = 160 + v * 6
                    px[xx, yy] = (c, c, c, 255)
        canvas.alpha_composite(tile, (r["x"], r["y"]))
    dr = ImageDraw.Draw(canvas)
    dr.text((2, 2), f"{oid}", fill=(255, 255, 255, 255))
    return canvas


def extract_stream(chunk: bytes, off: int) -> list[int]:
    out = []
    for i in range(off, min(len(chunk), STREAM_WINDOW)):
        b = chunk[i]
        if b == 0:
            break
        out.append(b)
    return out


def extract_first_nonzero_run(chunk: bytes, start: int = 0, end: int = STREAM_WINDOW) -> list[int]:
    i = start
    while i < min(len(chunk), end) and chunk[i] == 0:
        i += 1
    out = []
    while i < min(len(chunk), end):
        b = chunk[i]
        if b == 0:
            break
        out.append(b)
        i += 1
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    m = MAP_PATH.read_bytes()
    maps = (len(m) - MAP_HEADER) // MAP_REC

    sprites = decode_mazedata_tiles(MAZE_PATH)
    recs = parse_display_records(MAZE_PATH)
    by_owner = owner_records(recs)

    info = []
    for mid in range(maps):
        b = MAP_HEADER + mid * MAP_REC
        chunk = m[b : b + STREAM_WINDOW]
        stream0 = extract_stream(chunk, 0)
        stream0_nonzero = extract_first_nonzero_run(chunk, 0, 0x60)
        stream1 = extract_stream(chunk, 0x24)
        stream2 = extract_stream(chunk, 0x48)

        info.append(
            {
                "map_id": mid,
                "stream0_len": len(stream0),
                "stream0": stream0,
                "stream0_nonzero_len": len(stream0_nonzero),
                "stream0_nonzero": stream0_nonzero,
                "stream24_len": len(stream1),
                "stream24": stream1,
                "stream48_len": len(stream2),
                "stream48": stream2,
            }
        )

        render_stream = stream0 if stream0 else stream0_nonzero
        # Render map stream owner cards.
        cols = 8
        card_w, card_h = 72, 96
        n = max(1, len(render_stream))
        rows = (n + cols - 1) // cols
        sheet = Image.new("RGBA", (cols * card_w, rows * card_h + 20), (4, 6, 14, 255))
        dr = ImageDraw.Draw(sheet)
        dr.text((6, 4), f"map {mid:02d} stream {render_stream}", fill=(230, 230, 230, 255))
        for i, oid in enumerate(render_stream):
            x = (i % cols) * card_w
            y = 20 + (i // cols) * card_h
            rec_list = by_owner.get(oid, [])
            card = render_owner(oid, rec_list, sprites, size=(card_w, card_h))
            sheet.alpha_composite(card, (x, y))
        sheet.save(OUT_DIR / f"map_{mid:02d}_stream0.png")

    (OUT_DIR / "streams.json").write_text(json.dumps(info, indent=2))
    print(f"Wrote: {OUT_DIR / 'streams.json'}")
    print(f"Sheets: {OUT_DIR}")


if __name__ == "__main__":
    main()
