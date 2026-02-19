from __future__ import annotations

import argparse
from pathlib import Path


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")
MAP0_WALL_BASE = 0x01C0


def load(path: Path) -> bytes:
    return path.read_bytes()


def decode_wall_planes(data: bytes, base: int):
    a_start = base + 0x60
    b_start = base + 0x120

    def get_field(start: int, idx: int) -> int:
        b = data[start + (idx // 4)]
        shift = (idx % 4) * 2
        return (b >> shift) & 0x03

    out = []
    for block in range(12):
        for row in range(8):
            for col in range(8):
                idx = (block << 6) + (row << 3) + col
                out.append(
                    {
                        "block": block,
                        "row": row,
                        "col": col,
                        "south": get_field(a_start, idx),
                        "east": get_field(b_start, idx),
                    }
                )
    return out


def build_plane_values(fields):
    a_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    b_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    for t in fields:
        b = t["block"]
        r = t["row"]
        c = t["col"]
        a_vals[b][r][c] = int(t["south"])
        b_vals[b][r][c] = int(t["east"])
    return a_vals, b_vals


def rotate_local_edge(kind, x, y, rot):
    rot = rot % 4
    if rot == 0:
        return kind, x, y
    if kind == "h":
        p1 = (x, y)
        p2 = (x + 1, y)
    else:
        p1 = (x, y)
        p2 = (x, y + 1)

    def rp(px, py):
        if rot == 1:
            return 8 - py, px
        if rot == 2:
            return 8 - px, 8 - py
        return py, 8 - px

    q1 = rp(*p1)
    q2 = rp(*p2)
    if q1[1] == q2[1]:
        return "h", min(q1[0], q2[0]), q1[1]
    return "v", q1[0], min(q1[1], q2[1])


def block_plane_maps(fields, block_rot=0):
    per_block = [dict() for _ in range(12)]
    for t in fields:
        b = t["block"]
        r = t["row"]
        c = t["col"]
        hk, hx, hy = rotate_local_edge("h", c, r + 1, block_rot)
        vk, vx, vy = rotate_local_edge("v", c + 1, r, block_rot)
        per_block[b][(hk, hx, hy)] = t["south"] != 0
        per_block[b][(vk, vx, vy)] = t["east"] != 0
    return per_block


def score_layout(origins, per_block):
    seen = {}
    for b in range(12):
        ox, oy = origins[b]
        for (kind, x, y), v in per_block[b].items():
            key = (kind, x + ox, y + oy)
            seen.setdefault(key, []).append(v)

    score = 0.0
    for vals in seen.values():
        if len(vals) < 2:
            continue
        trues = sum(1 for v in vals if v)
        falses = len(vals) - trues
        score += trues * (trues - 1) * 1.0
        score -= trues * falses * 3.0
    return score


def infer_block_layout(fields, fixed_origins=None, block_rot=0):
    import random

    per_block = block_plane_maps(fields, block_rot=block_rot)
    rng = random.Random(1337)
    fixed_origins = fixed_origins or {}
    origins = [fixed_origins.get(i, (rng.randint(-8, 16), rng.randint(-8, 24))) for i in range(12)]

    for _ in range(8000):
        b = rng.randrange(12)
        if b in fixed_origins:
            continue
        ox, oy = origins[b]
        best = (ox, oy)
        best_s = score_layout(origins, per_block)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            trial = list(origins)
            trial[b] = (ox + dx, oy + dy)
            s = score_layout(trial, per_block)
            if s > best_s:
                best = trial[b]
                best_s = s
        origins[b] = best
    return origins


def infer_anchor_fixed_origins(orig_fields, mod_fields, block_rot=0):
    def by_idx(fields):
        d = {}
        for t in fields:
            d[(t["block"] << 6) + (t["row"] << 3) + t["col"]] = t
        return d

    o = by_idx(orig_fields)
    m = by_idx(mod_fields)
    fixed = {0: (0, 0), 1: (8, 0), 2: (0, -8), 3: (8, -8)}

    # Anchors from controlled edits in this workspace history.
    if o[118]["south"] != m[118]["south"]:
        fixed[1] = (8, 0)
    if o[228]["south"] != m[228]["south"]:
        fixed[3] = (8, -8)
    return fixed


def resolve_world_cell(origins, wx, wy, prefer_block=None):
    if prefer_block is not None:
        ox, oy = origins[prefer_block]
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return prefer_block, wy - oy, wx - ox
    for b, (ox, oy) in enumerate(origins):
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return b, wy - oy, wx - ox
    return None


def wall_mode_value(a_vals, b_vals, origins, block, row, col, mode, map_id=0):
    if mode == 0:
        return a_vals[block][row][col]
    if mode == 1:
        return b_vals[block][row][col]

    ox, oy = origins[block]
    wx = ox + col
    wy = oy + row
    if mode == 2:
        res = resolve_world_cell(origins, wx, wy - 1, prefer_block=block)
    else:
        res = resolve_world_cell(origins, wx - 1, wy, prefer_block=block)
    if res is None:
        return 0 if map_id in (0x0A, 0x0C) else 2
    rb, rr, rc = res
    return a_vals[rb][rr][rc] if mode == 2 else b_vals[rb][rr][rc]


def block_mode_edges(fields, origins, block, map_id=0):
    a_vals, b_vals = build_plane_values(fields)
    h = [[False] * 8 for _ in range(9)]
    v = [[False] * 9 for _ in range(8)]
    for y in range(9):
        for x in range(8):
            if y == 0:
                h[y][x] = wall_mode_value(a_vals, b_vals, origins, block, 0, x, 2, map_id=map_id) != 0
            else:
                h[y][x] = wall_mode_value(a_vals, b_vals, origins, block, y - 1, x, 0, map_id=map_id) != 0
    for y in range(8):
        for x in range(9):
            if x == 0:
                v[y][x] = wall_mode_value(a_vals, b_vals, origins, block, y, 0, 3, map_id=map_id) != 0
            else:
                v[y][x] = wall_mode_value(a_vals, b_vals, origins, block, y, x - 1, 1, map_id=map_id) != 0
    return h, v


def seam_mismatches(fields, origins, map_id=0):
    a_vals, b_vals = build_plane_values(fields)
    out = []
    for b, (ox, oy) in enumerate(origins):
        # Compare east seam of b with west seam of neighbor.
        for r in range(8):
            wx = ox + 7
            wy = oy + r
            right = wall_mode_value(a_vals, b_vals, origins, b, r, 7, 1, map_id=map_id) != 0
            ncell = resolve_world_cell(origins, wx + 1, wy)
            if ncell is None:
                continue
            nb, nr, nc = ncell
            left = wall_mode_value(a_vals, b_vals, origins, nb, nr, nc, 3, map_id=map_id) != 0
            if right != left:
                out.append(("v", b, r, nb, nr, right, left))
        # Compare south seam of b with north seam of neighbor.
        for c in range(8):
            wx = ox + c
            wy = oy + 7
            down = wall_mode_value(a_vals, b_vals, origins, b, 7, c, 0, map_id=map_id) != 0
            ncell = resolve_world_cell(origins, wx, wy + 1)
            if ncell is None:
                continue
            nb, nr, nc = ncell
            up = wall_mode_value(a_vals, b_vals, origins, nb, nr, nc, 2, map_id=map_id) != 0
            if down != up:
                out.append(("h", b, c, nb, nc, down, up))
    return out


def main():
    ap = argparse.ArgumentParser(description="Dump mode-resolved map0 block edges and seam mismatches")
    ap.add_argument("--modified", action="store_true", help="Use NEWGAME.DBS (default is original)")
    ap.add_argument("--block", type=int, default=3, help="Block to dump")
    ap.add_argument("--rot", type=int, choices=[0, 90, 180, 270], default=0)
    ap.add_argument("--map-id", type=lambda s: int(s, 0), default=0, help="Map id for OOB fallback rule")
    args = ap.parse_args()

    data = load(MOD_PATH if args.modified else ORIG_PATH)
    fields = decode_wall_planes(data, MAP0_WALL_BASE)
    other = decode_wall_planes(load(ORIG_PATH), MAP0_WALL_BASE)
    fixed = infer_anchor_fixed_origins(other, fields, block_rot=(args.rot // 90) % 4)
    origins = infer_block_layout(fields, fixed_origins=fixed, block_rot=(args.rot // 90) % 4)

    print("origins:")
    for i, xy in enumerate(origins):
        print(f"  b{i}: {xy}")

    mism = seam_mismatches(fields, origins, map_id=args.map_id)
    print(f"seam_mismatches={len(mism)}")
    for m in mism[:80]:
        print(" ", m)

    b = args.block
    h, v = block_mode_edges(fields, origins, b, map_id=args.map_id)
    print(f"block={b} h-edges:")
    for y in range(9):
        row = "".join("#" if h[y][x] else "." for x in range(8))
        print(f"  y{y}: {row}")
    print(f"block={b} v-edges:")
    for y in range(8):
        row = "".join("#" if v[y][x] else "." for x in range(9))
        print(f"  y{y}: {row}")


if __name__ == "__main__":
    main()

