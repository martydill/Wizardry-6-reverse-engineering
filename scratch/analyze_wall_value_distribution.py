from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def record_base(map_id: int) -> int:
    return 0x019E + map_id * 0x0C0E


def decode_wall_planes(data: bytes, base: int):
    a_start = base + 0x60
    b_start = base + 0x120

    def get_field(start: int, idx: int) -> int:
        b = data[start + (idx // 4)]
        shift = (idx % 4) * 2
        return (b >> shift) & 0x03

    a_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    b_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    for block in range(12):
        for row in range(8):
            for col in range(8):
                idx = (block << 6) + (row << 3) + col
                a_vals[block][row][col] = get_field(a_start, idx)
                b_vals[block][row][col] = get_field(b_start, idx)
    return a_vals, b_vals


def decode_origins(data: bytes, base: int):
    xs = list(data[base + 0x1E0 : base + 0x1E0 + 12])
    ys = list(data[base + 0x1EC : base + 0x1EC + 12])
    return list(zip(xs, ys))


def resolve_world_cell(origins, wx, wy, prefer_block=None):
    if prefer_block is not None:
        ox, oy = origins[prefer_block]
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return prefer_block, wy - oy, wx - ox
    for b, (ox, oy) in enumerate(origins):
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return b, wy - oy, wx - ox
    return None


def wall_mode_value(a_vals, b_vals, origins, map_id, block, row, col, mode):
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


def collect_world_edge_values(a_vals, b_vals, origins, map_id):
    out = {}
    for b, (ox, oy) in enumerate(origins):
        if ox == 0 and oy == 0:
            continue
        for y in range(9):
            for x in range(8):
                if y == 0:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, 0, x, 2)
                else:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y - 1, x, 0)
                if val:
                    out[("h", ox + x, oy + y)] = val
        for y in range(8):
            for x in range(9):
                if x == 0:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y, 0, 3)
                else:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y, x - 1, 1)
                if val:
                    out[("v", ox + x, oy + y)] = val
    return out


def main() -> None:
    db = Path("gamedata/NEWGAME.DBS").read_bytes()
    max_maps = max(1, (len(db) - 0x019E) // 0x0C0E)

    per_map = []
    total = Counter()
    for map_id in range(max_maps):
        base = record_base(map_id)
        a_vals, b_vals = decode_wall_planes(db, base)
        origins = decode_origins(db, base)
        edges = collect_world_edge_values(a_vals, b_vals, origins, map_id)
        c = Counter(edges.values())
        total.update(c)
        per_map.append(
            {
                "map_id": map_id,
                "edge_count": len(edges),
                "counts": {str(k): int(v) for k, v in sorted(c.items())},
            }
        )

    out = {
        "map_count": max_maps,
        "total_counts": {str(k): int(v) for k, v in sorted(total.items())},
        "per_map": per_map,
    }
    out_dir = Path("scratch/wall_value_distribution")
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / "distribution.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"Wrote {p}")
    print(f"Total counts: {out['total_counts']}")


if __name__ == "__main__":
    main()
