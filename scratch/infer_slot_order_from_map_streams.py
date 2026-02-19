from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

from bane.data.sprite_decoder import decode_mazedata_tiles


def parse_display_records(path: Path):
    data = path.read_bytes()
    n = data[0] | (data[1] << 8)
    n2 = data[2] | (data[3] << 8)
    st = 4 + n * 5
    recs = []
    for i in range(n2):
        b = data[st + i * 5 : st + i * 5 + 5]
        recs.append({"owner_id": b[0], "tile_ref": b[1], "x": b[2], "y": b[3], "aux": b[4]})
    return recs


def render_owner(owner_records, sprites, canvas=(200, 140)) -> Image.Image:
    im = Image.new("RGBA", canvas, (0, 0, 0, 0))
    for r in owner_records:
        t = r["tile_ref"]
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if not (0 <= idx < len(sprites)):
            continue
        sp = sprites[idx]
        rgb = Image.frombytes("RGB", (sp.width, sp.height), sp.to_rgb_bytes())
        tile = Image.new("RGBA", rgb.size, (0, 0, 0, 0))
        tile.paste(rgb, (0, 0))
        px = tile.load()
        for y in range(tile.height):
            for x in range(tile.width):
                rr, gg, bb, _ = px[x, y]
                if rr == 0 and gg == 0 and bb == 0:
                    px[x, y] = (0, 0, 0, 0)
                else:
                    px[x, y] = (rr, gg, bb, 255)
        im.alpha_composite(tile, (r["x"], r["y"]))
    return im


def owner_cx(img: Image.Image) -> float | None:
    bb = img.split()[-1].getbbox()
    if bb is None:
        return None
    x0, _, x1, _ = bb
    return (x0 + x1 - 1) / 2.0


def orient(cx: float | None) -> str:
    if cx is None:
        return "none"
    if cx < 74:
        return "left"
    if cx > 102:
        return "right"
    return "center"


def code_to_owner(c: int) -> int | None:
    if 0 <= c <= 152:
        return c
    if 153 <= c <= 180:
        return c - 28
    return None


def main() -> None:
    mstream = json.loads(Path('scratch/map_owner_streams/streams.json').read_text())
    mpath = Path('gamedata/MAZEDATA.EGA')
    sprites = decode_mazedata_tiles(mpath)
    recs = parse_display_records(mpath)
    by_owner = defaultdict(list)
    for r in recs:
        by_owner[r['owner_id']].append(r)
    oimg = {oid: render_owner(rs, sprites) for oid, rs in by_owner.items()}
    ocx = {oid: owner_cx(im) for oid, im in oimg.items()}

    pos_orients = [Counter() for _ in range(12)]
    pos_codes = [Counter() for _ in range(12)]

    for m in mstream:
        s = m['stream0'] if m['stream0'] else m.get('stream0_nonzero', [])
        if len(s) < 12:
            continue
        set0 = s[:12]
        for i, c in enumerate(set0):
            oid = code_to_owner(c)
            if oid is None:
                pos_orients[i]['unknown'] += 1
                continue
            pos_codes[i][oid] += 1
            pos_orients[i][orient(ocx.get(oid))] += 1

    out = {
        'position_orient_hist': [dict(c) for c in pos_orients],
        'position_top_owners': [[(oid, n) for oid, n in pos_codes[i].most_common(8)] for i in range(12)],
    }
    outp = Path('scratch/map_owner_streams/slot_order_inference.json')
    outp.write_text(json.dumps(out, indent=2))
    print(f'Wrote: {outp}')
    for i,c in enumerate(pos_orients):
        print(i, dict(c))


if __name__ == '__main__':
    main()
