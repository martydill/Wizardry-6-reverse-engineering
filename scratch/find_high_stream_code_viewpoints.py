from __future__ import annotations

import argparse
import json
from pathlib import Path

import importlib.util


def load_renderer_module():
    p = Path("scratch/render_map_3d_owner_prototype.py")
    spec = importlib.util.spec_from_file_location("render_map_3d_owner_prototype", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to import {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect_world_cells(origins: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for ox, oy in origins:
        if ox == 0 and oy == 0:
            continue
        for wy in range(oy, oy + 8):
            for wx in range(ox, ox + 8):
                out.append((wx, wy))
    return out


def visible_slots(mod, edges, wx: int, wy: int, facing: str):
    dx, dy = mod.dir_vec(facing)
    lx, ly = mod.left_vec(dx, dy)
    rx, ry = -lx, -ly

    out: list[tuple[str, int, int]] = []
    blocked_ahead = False
    for depth in range(1, 5):
        base_x = wx + dx * (depth - 1)
        base_y = wy + dy * (depth - 1)
        fw = mod.wall_between(edges, base_x, base_y, dx, dy)
        lw = mod.wall_between(edges, base_x, base_y, lx, ly)
        rw = mod.wall_between(edges, base_x, base_y, rx, ry)
        out.append(("center", depth, fw))
        out.append(("left", depth, lw))
        out.append(("right", depth, rw))
        if fw != 0:
            blocked_ahead = True
        if blocked_ahead:
            break
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Find viewpoints that actually draw high stream codes.")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--maps", default="11,12", help="Comma-separated map IDs.")
    ap.add_argument("--top", type=int, default=60, help="Top N candidates per map.")
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("scratch/map_owner_streams/high_code_viewpoints.json"),
    )
    args = ap.parse_args()

    mod = load_renderer_module()
    db = (args.gamedata / "NEWGAME.DBS").read_bytes()
    slot_order = mod.slot_keys_depth_triplets()
    offsets = {1: 0x24, 2: 0x00, 3: 0x48}

    map_ids = [int(x.strip(), 0) for x in args.maps.split(",") if x.strip()]
    payload: dict[str, object] = {"maps": {}}

    for map_id in map_ids:
        base = mod.record_base(map_id)
        a_vals, b_vals = mod.decode_wall_planes(db, base)
        origins = mod.decode_origins(db, base)
        edges = mod.collect_world_edge_values(a_vals, b_vals, origins, map_id)

        picked_codes: dict[int, dict[str, int]] = {}
        for wv in (1, 2, 3):
            stream_codes = mod.extract_map_stream_at_offset(db, map_id, offsets[wv])
            stream_sets = mod.stream_sets_from_codes(stream_codes)
            if not stream_sets:
                stream_sets = mod.stream_sets_from_codes(mod.extract_primary_map_stream(db, map_id))
            if not stream_sets:
                continue
            codes12 = stream_sets[0]
            picked_codes[wv] = {
                slot_order[i]: codes12[i] for i in range(min(len(slot_order), len(codes12)))
            }

        high_slots = [
            {"wall_value": wv, "slot": sk, "code": code}
            for wv, by_slot in picked_codes.items()
            for sk, code in by_slot.items()
            if code > 152
        ]

        candidates = []
        for wx, wy in collect_world_cells(origins):
            for facing in ("N", "E", "S", "W"):
                vis = visible_slots(mod, edges, wx, wy, facing)
                hits = []
                for orient, depth, wallv in vis:
                    if wallv == 0:
                        continue
                    slot_key = f"{orient}_d{depth}"
                    code = picked_codes.get(wallv, {}).get(slot_key)
                    if code is not None and code > 152:
                        hits.append(
                            {
                                "slot": slot_key,
                                "wall_value": wallv,
                                "code": code,
                                "depth": depth,
                            }
                        )
                if hits:
                    max_depth = max(h["depth"] for h in hits)
                    candidates.append(
                        {
                            "wx": wx,
                            "wy": wy,
                            "facing": facing,
                            "hits": hits,
                            "score": max_depth * 10 + len(hits),
                        }
                    )

        candidates.sort(
            key=lambda c: (
                -int(c["score"]),
                -len(c["hits"]),
                int(c["wx"]),
                int(c["wy"]),
                str(c["facing"]),
            )
        )

        payload["maps"][str(map_id)] = {
            "high_slots": high_slots,
            "candidate_count": len(candidates),
            "top_candidates": candidates[: args.top],
        }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
