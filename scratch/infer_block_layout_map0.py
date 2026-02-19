from pathlib import Path
import random


DATA = Path("gamedata/NEWGAME.DBS")
BASE = 0x01C0


def decode_planes(data: bytes):
    def get(arr, idx):
        b = data[arr + idx // 4]
        return ((b >> ((idx % 4) * 2)) & 0x03) != 0

    fields = []
    for block in range(12):
        for row in range(8):
            for col in range(8):
                idx = (block << 6) + (row << 3) + col
                fields.append(
                    {
                        "block": block,
                        "row": row,
                        "col": col,
                        "south": get(BASE + 0x60, idx),
                        "east": get(BASE + 0x120, idx),
                    }
                )
    return fields


def block_maps(fields):
    maps = [dict() for _ in range(12)]
    for t in fields:
        b = t["block"]
        r = t["row"]
        c = t["col"]
        maps[b][("h", c, r + 1)] = t["south"]
        maps[b][("v", c + 1, r)] = t["east"]
    return maps


def score(origins, maps):
    seen = {}
    for b in range(12):
        ox, oy = origins[b]
        for (k, x, y), v in maps[b].items():
            seen.setdefault((k, x + ox, y + oy), []).append(v)

    s = 0.0
    for vals in seen.values():
        if len(vals) < 2:
            continue
        t = sum(1 for v in vals if v)
        f = len(vals) - t
        s += t * (t - 1) * 0.5
        s += f * (f - 1) * 0.5
        s -= t * f * 2.0
    return s


def infer(maps, seed=1337):
    rng = random.Random(seed)
    best = None
    best_s = -1e18
    for _ in range(24):
        origins = [(rng.randint(0, 12), rng.randint(0, 12)) for _ in range(12)]
        cur = score(origins, maps)
        for _ in range(2500):
            b = rng.randrange(12)
            ox, oy = origins[b]
            trial = list(origins)
            trial[b] = (ox + rng.choice([-1, 0, 1]), oy + rng.choice([-1, 0, 1]))
            ts = score(trial, maps)
            if ts >= cur:
                origins = trial
                cur = ts
        if cur > best_s:
            best = origins
            best_s = cur
    return best_s, best


def added_edges(orig_fields, mod_fields, origins):
    def mk(fields):
        maps = [dict() for _ in range(12)]
        for t in fields:
            b = t["block"]
            r = t["row"]
            c = t["col"]
            maps[b][("h", c, r + 1)] = t["south"]
            maps[b][("v", c + 1, r)] = t["east"]
        return maps

    o = mk(orig_fields)
    m = mk(mod_fields)
    out = set()
    for b in range(12):
        ox, oy = origins[b]
        for key in set(o[b]) | set(m[b]):
            if m[b].get(key, False) and not o[b].get(key, False):
                kind, x, y = key
                out.add((kind, x + ox, y + oy))
    return out


def best_shift(added):
    target_h = {(0, 7), (0, 14), (16, 0), (17, 0), (18, 0), (19, 0), (16, 2), (17, 2), (18, 2), (19, 2)}
    target_v = {(1, 7), (16, 0), (16, 1), (18, 0), (18, 1), (20, 0), (20, 1)}
    best = (0, 0, -10**9)
    for sx in range(-30, 31):
        for sy in range(-30, 31):
            hit = 0
            miss = 0
            for kind, x, y in added:
                tx, ty = x + sx, y + sy
                if kind == "h":
                    if (tx, ty) in target_h:
                        hit += 1
                    else:
                        miss += 1
                else:
                    if (tx, ty) in target_v:
                        hit += 1
                    else:
                        miss += 1
            s = hit * 10 - miss
            if s > best[2]:
                best = (sx, sy, s)
    return best


def main():
    mod = DATA.read_bytes()
    orig = Path("gamedata/NEWGAME_original.DBS").read_bytes()
    fields = decode_planes(mod)
    fields_orig = decode_planes(orig)
    maps = block_maps(fields)
    score_val, origins = infer(maps)
    ax, ay, ascore = best_shift(added_edges(fields_orig, fields, origins))
    print(f"score={score_val:.2f}")
    print(f"align_shift dx={ax} dy={ay} score={ascore}")
    for i, (x, y) in enumerate(origins):
        print(f"block {i:2d}: ox={x:2d} oy={y:2d}")


if __name__ == "__main__":
    main()
