from __future__ import annotations

import json
from pathlib import Path


DB_PATH = Path("gamedata/NEWGAME.DBS")
OUT_PATH = Path("scratch/all_maps_walls.json")

MAP_HEADER_SIZE = 0x019E
MAP_RECORD_SIZE = 0x0C0E


def read_u2_field(data: bytes, start: int, idx: int) -> int:
    b = data[start + (idx // 4)]
    return (b >> ((idx % 4) * 2)) & 0x03


def record_base(map_id: int) -> int:
    return MAP_HEADER_SIZE + map_id * MAP_RECORD_SIZE


def decode_wall_planes(data: bytes, base: int):
    a_start = base + 0x60
    b_start = base + 0x120
    a_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    b_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    for block in range(12):
        for row in range(8):
            for col in range(8):
                idx = (block << 6) + (row << 3) + col
                a_vals[block][row][col] = read_u2_field(data, a_start, idx)
                b_vals[block][row][col] = read_u2_field(data, b_start, idx)
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
    res = resolve_world_cell(origins, wx, wy - 1, prefer_block=block) if mode == 2 else resolve_world_cell(origins, wx - 1, wy, prefer_block=block)
    if res is None:
        return 0 if map_id in (0x0A, 0x0C) else 2
    rb, rr, rc = res
    return a_vals[rb][rr][rc] if mode == 2 else b_vals[rb][rr][rc]


def build_boundaries(a_vals, b_vals, origins, map_id, block):
    h = [[0] * 8 for _ in range(9)]
    v = [[0] * 9 for _ in range(8)]
    for y in range(9):
        for x in range(8):
            if y == 0:
                h[y][x] = 1 if wall_mode_value(a_vals, b_vals, origins, map_id, block, 0, x, 2) != 0 else 0
            else:
                h[y][x] = 1 if wall_mode_value(a_vals, b_vals, origins, map_id, block, y - 1, x, 0) != 0 else 0
    for y in range(8):
        for x in range(9):
            if x == 0:
                v[y][x] = 1 if wall_mode_value(a_vals, b_vals, origins, map_id, block, y, 0, 3) != 0 else 0
            else:
                v[y][x] = 1 if wall_mode_value(a_vals, b_vals, origins, map_id, block, y, x - 1, 1) != 0 else 0
    return h, v


def active_block(origins, a_vals, b_vals, block):
    ox, oy = origins[block]
    if ox != 0 or oy != 0:
        return True
    for r in range(8):
        for c in range(8):
            if a_vals[block][r][c] or b_vals[block][r][c]:
                return True
    return False


def main() -> None:
    data = DB_PATH.read_bytes()
    num_maps = max(0, (len(data) - MAP_HEADER_SIZE) // MAP_RECORD_SIZE)
    out = {"file": str(DB_PATH), "num_maps": num_maps, "maps": []}

    for map_id in range(num_maps):
        base = record_base(map_id)
        a_vals, b_vals = decode_wall_planes(data, base)
        origins = decode_origins(data, base)

        blocks = []
        for b in range(12):
            if not active_block(origins, a_vals, b_vals, b):
                continue
            h, v = build_boundaries(a_vals, b_vals, origins, map_id, b)
            blocks.append(
                {
                    "block": b,
                    "origin_x": origins[b][0],
                    "origin_y": origins[b][1],
                    "h": h,
                    "v": v,
                }
            )

        out["maps"].append({"map_id": map_id, "base": base, "blocks": blocks})

    OUT_PATH.write_text(json.dumps(out, indent=2))
    print(f"Wrote {OUT_PATH} with {num_maps} map records")


if __name__ == "__main__":
    main()
