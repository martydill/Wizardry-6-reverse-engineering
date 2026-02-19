from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from PIL import Image

from bane.data.sprite_decoder import decode_mazedata_tiles


MAP_HEADER_SIZE = 0x019E
MAP_RECORD_SIZE = 0x0C0E
MAP_STREAM_WINDOW = 0x01B0


def record_base(map_id: int) -> int:
    return MAP_HEADER_SIZE + map_id * MAP_RECORD_SIZE


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


def parse_display_records(path: Path):
    data = path.read_bytes()
    n = data[0] | (data[1] << 8)
    n2 = data[2] | (data[3] << 8)
    st = 4 + n * 5
    raw = data[st : st + n2 * 5]
    recs = []
    for i in range(n2):
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


def decode_stream_code_to_owner(code: int, high_mode: str = "minus28") -> int | None:
    # Observed map-stream codes are mostly direct owner IDs.
    # High-band handling can be switched to test decode hypotheses.
    if 0 <= code <= 152:
        return code
    if 153 <= code <= 180:
        if high_mode == "minus28":
            return code - 28
        if high_mode == "highbit":
            return code & 0x7F
        if high_mode == "identity":
            return code
    return None


def extract_primary_map_stream(db: bytes, map_id: int) -> list[int]:
    base = record_base(map_id)
    chunk = db[base : base + MAP_STREAM_WINDOW]
    if not chunk:
        return []
    start = 0
    if chunk[0] == 0:
        while start < len(chunk) and chunk[start] == 0:
            start += 1
    out: list[int] = []
    for i in range(start, len(chunk)):
        b = chunk[i]
        if b == 0:
            break
        out.append(b)
    return out


def extract_map_stream_at_offset(db: bytes, map_id: int, start: int) -> list[int]:
    base = record_base(map_id)
    chunk = db[base : base + MAP_STREAM_WINDOW]
    if not chunk:
        return []
    if start < 0 or start >= len(chunk):
        return []
    out: list[int] = []
    for i in range(start, len(chunk)):
        b = chunk[i]
        if b == 0:
            break
        out.append(b)
    return out


def stream_sets_from_codes(codes: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for i in range(0, len(codes), 12):
        s = codes[i : i + 12]
        if len(s) < 12:
            break
        out.append(s)
    return out


def parse_stream_set_map(spec: str) -> dict[int, int]:
    out = {2: 0, 1: 1, 3: 2}
    for part in spec.split(","):
        p = part.strip()
        if not p or ":" not in p:
            continue
        a, b = p.split(":", 1)
        try:
            w = int(a, 0)
            s = int(b, 0)
        except ValueError:
            continue
        if w in (1, 2, 3):
            out[w] = s
    return out


def parse_stream_offset_map(spec: str) -> dict[int, int]:
    out = {2: 0x00, 1: 0x24, 3: 0x48}
    for part in spec.split(","):
        p = part.strip()
        if not p or ":" not in p:
            continue
        a, b = p.split(":", 1)
        try:
            w = int(a, 0)
            off = int(b, 0)
        except ValueError:
            continue
        if w in (1, 2, 3):
            out[w] = off
    return out


def slot_keys_depth_triplets() -> list[str]:
    out = []
    for d in range(1, 5):
        out.extend([f"center_d{d}", f"left_d{d}", f"right_d{d}"])
    return out


def owner_metrics(img: Image.Image) -> dict[str, float]:
    a = img.split()[-1]
    bb = a.getbbox()
    if bb is None:
        return {"cx": 0.0, "area": 0.0, "warm_ratio": 0.0}
    x0, y0, x1, y1 = bb
    w = max(0, x1 - x0)
    h = max(0, y1 - y0)
    px = img.load()
    warm = 0
    total = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            rr, gg, bbv, aa = px[x, y]
            if aa == 0:
                continue
            total += 1
            if rr > 80 and rr > gg + 20 and rr > bbv + 20:
                warm += 1
    wr = (warm / total) if total else 0.0
    cx = (x0 + x1 - 1) / 2.0
    return {"cx": cx, "area": float(w * h), "warm_ratio": wr}


def infer_stream_set_map(
    stream_sets: list[list[int]],
    owner_metric: dict[int, dict[str, float]],
) -> tuple[dict[int, int], dict[int, float]]:
    # Score each 12-code set as a slot map:
    # - expected orient per triplet slot (center/left/right)
    # - monotonic area decrease by depth
    # Choose:
    # - wall=2: best structural score
    # - wall=3: warmest among remaining
    # - wall=1: next best structural among remaining
    if not stream_sets:
        return ({2: 0, 1: 0, 3: 0}, {})

    def code_owner(c: int) -> int | None:
        return decode_stream_code_to_owner(c, "minus28")

    def orient_score(cx: float, expected: str) -> float:
        if expected == "center":
            # favor center-ish band.
            d = abs(cx - 88.0)
            return max(0.0, 1.0 - d / 60.0)
        if expected == "left":
            return max(0.0, min(1.0, (90.0 - cx) / 90.0))
        if expected == "right":
            return max(0.0, min(1.0, (cx - 86.0) / 90.0))
        return 0.0

    set_struct: dict[int, float] = {}
    set_warm: dict[int, float] = {}
    for si, s in enumerate(stream_sets):
        if len(s) < 12:
            continue
        exp = [
            ("center", 1),
            ("left", 1),
            ("right", 1),
            ("center", 2),
            ("left", 2),
            ("right", 2),
            ("center", 3),
            ("left", 3),
            ("right", 3),
            ("center", 4),
            ("left", 4),
            ("right", 4),
        ]
        orient_acc = 0.0
        warm_acc = 0.0
        warm_n = 0
        by_orient = {"center": [], "left": [], "right": []}
        for i, code in enumerate(s[:12]):
            owner = code_owner(code)
            if owner is None:
                continue
            m = owner_metric.get(owner)
            if not m:
                continue
            eo, _ = exp[i]
            orient_acc += orient_score(m["cx"], eo)
            by_orient[eo].append(m["area"])
            warm_acc += m["warm_ratio"]
            warm_n += 1
        # Monotonic depth prior: near >= far per orient.
        mono = 0.0
        mono_n = 0
        for eo in ("center", "left", "right"):
            arr = by_orient[eo]
            if len(arr) >= 2:
                for i in range(1, len(arr)):
                    mono += 1.0 if arr[i - 1] >= arr[i] else 0.0
                    mono_n += 1
        mono_score = (mono / mono_n) if mono_n else 0.0
        struct_score = orient_acc + 4.0 * mono_score
        set_struct[si] = struct_score
        set_warm[si] = (warm_acc / warm_n) if warm_n else 0.0

    if not set_struct:
        return ({2: 0, 1: 0, 3: 0}, set_struct)

    # wall 2 (dominant solid): best structure with cool bias.
    s2 = max(set_struct, key=lambda k: set_struct[k] - 3.0 * set_warm.get(k, 0.0))
    remaining = [k for k in set_struct.keys() if k != s2]
    if not remaining:
        return ({2: s2, 1: s2, 3: s2}, set_struct)

    # wall 3 (special/door-like): warm-biased among structurally plausible sets.
    s3 = max(remaining, key=lambda k: set_struct.get(k, 0.0) + 3.0 * set_warm.get(k, 0.0))
    remaining2 = [k for k in remaining if k != s3]
    if not remaining2:
        return ({2: s2, 1: s2, 3: s3}, set_struct)

    # wall 1: best leftover, slight cool preference.
    s1 = max(remaining2, key=lambda k: set_struct.get(k, -1e9) - 1.5 * set_warm.get(k, 0.0))
    return ({2: s2, 1: s1, 3: s3}, set_struct)


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


def dir_vec(facing: str) -> tuple[int, int]:
    if facing == "N":
        return (0, -1)
    if facing == "S":
        return (0, 1)
    if facing == "E":
        return (1, 0)
    if facing == "W":
        return (-1, 0)
    raise ValueError(f"bad facing: {facing}")


def left_vec(dx: int, dy: int) -> tuple[int, int]:
    return (-dy, dx)


def wall_between(edges, wx: int, wy: int, dx: int, dy: int) -> int:
    if dx == 0 and dy == -1:
        return edges.get(("h", wx, wy), 0)
    if dx == 0 and dy == 1:
        return edges.get(("h", wx, wy + 1), 0)
    if dx == -1 and dy == 0:
        return edges.get(("v", wx, wy), 0)
    if dx == 1 and dy == 0:
        return edges.get(("v", wx + 1, wy), 0)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Prototype first-person renderer using real map edges + MAZEDATA owners")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--map-id", type=int, default=0)
    ap.add_argument("--wx", type=int, default=None)
    ap.add_argument("--wy", type=int, default=None)
    ap.add_argument("--facing", choices=["N", "E", "S", "W"], default="N")
    ap.add_argument("--out", type=Path, default=Path("scratch/proto_3d_view.png"))
    ap.add_argument(
        "--debug-json",
        type=Path,
        default=None,
        help="Optional path to write detailed render decision trace JSON.",
    )
    ap.add_argument(
        "--slot-candidates",
        type=Path,
        default=Path("scratch/owner_slot_candidates/slot_candidates.json"),
    )
    ap.add_argument(
        "--mapping-overrides-file",
        type=Path,
        default=None,
        help="JSON file with per-wall-value slot picks: {\"1\": {\"slot\": owner, ...}, ...}",
    )
    ap.add_argument(
        "--override",
        action="append",
        default=[],
        help="Override mapping: 'slot=owner' (all wall values) or 'wall:slot=owner' (specific wall 1/2/3)",
    )
    ap.add_argument(
        "--use-map-streams",
        action="store_true",
        help="Use real map-record stream codes (+0x1B0 window) to pick owners per wall value.",
    )
    ap.add_argument(
        "--stream-set-map",
        default="2:0,1:1,3:2",
        help="Wall value to stream-set index mapping, e.g. '2:0,1:1,3:2'.",
    )
    ap.add_argument(
        "--use-stream-offsets",
        action="store_true",
        help="Use offset streams per wall value (default offsets: 2->0x00, 1->0x24, 3->0x48).",
    )
    ap.add_argument(
        "--stream-offset-map",
        default="2:0x0,1:0x24,3:0x48",
        help="Wall value to stream-byte offset mapping within +0x1B0 window.",
    )
    ap.add_argument(
        "--auto-stream-set-map",
        action="store_true",
        help="Infer wall->stream-set map from owner geometry/warmth instead of fixed mapping.",
    )
    ap.add_argument(
        "--stream-code-map-file",
        type=Path,
        default=None,
        help="Optional JSON {\"code\": owner_id} mapping to override stream-code decoding.",
    )
    ap.add_argument(
        "--stream-high-mode",
        choices=["minus28", "highbit", "identity"],
        default="minus28",
        help="Decode strategy for stream high-band codes (153..180).",
    )
    args = ap.parse_args()

    db = (args.gamedata / "NEWGAME.DBS").read_bytes()
    base = record_base(args.map_id)
    a_vals, b_vals = decode_wall_planes(db, base)
    origins = decode_origins(db, base)
    edges = collect_world_edge_values(a_vals, b_vals, origins, args.map_id)

    # Choose a default in-bounds starting cell from first active block.
    if args.wx is None or args.wy is None:
        b0 = next((i for i, (x, y) in enumerate(origins) if not (x == 0 and y == 0)), 0)
        ox, oy = origins[b0]
        wx, wy = ox + 3, oy + 3
    else:
        wx, wy = args.wx, args.wy

    mpath = args.gamedata / "MAZEDATA.EGA"
    sprites = decode_mazedata_tiles(mpath)
    all_records = parse_display_records(mpath)
    by_owner = defaultdict(list)
    for r in all_records:
        by_owner[r["owner_id"]].append(r)
    owner_img = {oid: render_owner(rs, sprites) for oid, rs in by_owner.items()}
    owner_metric = {oid: owner_metrics(img) for oid, img in owner_img.items()}
    stream_code_map: dict[int, int] = {}
    if args.stream_code_map_file and args.stream_code_map_file.exists():
        try:
            raw_map = json.loads(args.stream_code_map_file.read_text())
            if isinstance(raw_map, dict):
                for k, v in raw_map.items():
                    try:
                        code = int(k, 0)
                        owner = int(v, 0)
                    except Exception:
                        continue
                    stream_code_map[code] = owner
        except Exception:
            pass

    slot_data = json.loads(args.slot_candidates.read_text())
    slots_generic = slot_data["slot_candidates"]
    slots_by_val = slot_data.get("slot_candidates_by_wall_value", {})

    # Pick one candidate per slot and wall value for the prototype.
    pick_by_val: dict[int, dict[str, int | None]] = {}
    for wallv in (1, 2, 3):
        kv = slots_by_val.get(str(wallv), {})
        picks = {}
        for slot_key, generic_ids in slots_generic.items():
            ids = kv.get(slot_key, generic_ids)
            picks[slot_key] = ids[0] if ids else None
        if picks.get("center_d1") is None:
            picks["center_d1"] = 0
        pick_by_val[wallv] = picks

    map_stream_info = {
        "codes": [],
        "sets": [],
        "set_map": parse_stream_set_map(args.stream_set_map),
        "offset_map": parse_stream_offset_map(args.stream_offset_map),
        "high_mode": args.stream_high_mode,
        "offset_streams": {},
        "picked_codes_by_wall": {},
        "set_struct_scores": {},
    }
    if args.use_map_streams:
        if args.use_stream_offsets and args.stream_set_map.strip() == "2:0,1:1,3:2":
            # When stream offsets are used, each wall class has its own stream entry.
            # Default to set 0 per class unless caller explicitly supplied set mapping.
            map_stream_info["set_map"] = {1: 0, 2: 0, 3: 0}
        if args.use_stream_offsets:
            for wv in (1, 2, 3):
                off = map_stream_info["offset_map"].get(wv, 0)
                codes = extract_map_stream_at_offset(db, args.map_id, off)
                map_stream_info["offset_streams"][str(wv)] = codes
        stream_codes = extract_primary_map_stream(db, args.map_id)
        stream_sets = stream_sets_from_codes(stream_codes)
        map_stream_info["codes"] = stream_codes
        map_stream_info["sets"] = stream_sets
        if args.auto_stream_set_map and stream_sets:
            inferred, scores = infer_stream_set_map(stream_sets, owner_metric)
            map_stream_info["set_map"] = inferred
            map_stream_info["set_struct_scores"] = {str(k): v for k, v in scores.items()}
        slot_order = slot_keys_depth_triplets()
        for wv in (1, 2, 3):
            chosen_sets = stream_sets
            if args.use_stream_offsets:
                wcodes = map_stream_info["offset_streams"].get(str(wv), [])
                chosen_sets = stream_sets_from_codes(wcodes)
                if not chosen_sets:
                    chosen_sets = stream_sets
            if not chosen_sets:
                continue
            set_idx = map_stream_info["set_map"].get(wv, 0)
            if set_idx < 0:
                continue
            if set_idx >= len(chosen_sets):
                set_idx = len(chosen_sets) - 1
            codes12 = chosen_sets[set_idx]
            map_stream_info["picked_codes_by_wall"][str(wv)] = {
                slot_order[i]: codes12[i] for i in range(min(len(slot_order), len(codes12)))
            }
            for i, slot_key in enumerate(slot_order):
                code = codes12[i]
                owner = stream_code_map.get(code)
                if owner is None:
                    owner = decode_stream_code_to_owner(code, args.stream_high_mode)
                if owner is not None:
                    pick_by_val[wv][slot_key] = owner

    # Apply persisted mapping overrides file, if supplied.
    if args.mapping_overrides_file and args.mapping_overrides_file.exists():
        try:
            ov = json.loads(args.mapping_overrides_file.read_text())
            for ws, mp in ov.items():
                try:
                    wv = int(ws, 0)
                except Exception:
                    continue
                if wv not in pick_by_val or not isinstance(mp, dict):
                    continue
                for slot_key, owner in mp.items():
                    if isinstance(owner, int):
                        pick_by_val[wv][slot_key] = owner
        except Exception:
            pass

    # Apply manual overrides.
    for spec in args.override:
        if "=" not in spec:
            continue
        lhs, rhs = spec.split("=", 1)
        try:
            owner = int(rhs, 0)
        except ValueError:
            continue
        if ":" in lhs:
            ws, slot_key = lhs.split(":", 1)
            try:
                wv = int(ws, 0)
            except ValueError:
                continue
            if wv in pick_by_val:
                pick_by_val[wv][slot_key] = owner
        else:
            slot_key = lhs
            for wv in pick_by_val:
                pick_by_val[wv][slot_key] = owner

    dx, dy = dir_vec(args.facing)
    lx, ly = left_vec(dx, dy)
    rx, ry = -lx, -ly

    # Build visibility slots from map edges.
    visible = []
    blocked_ahead = False
    for depth in range(1, 5):
        base_x = wx + dx * (depth - 1)
        base_y = wy + dy * (depth - 1)
        fw = wall_between(edges, base_x, base_y, dx, dy)
        lw = wall_between(edges, base_x, base_y, lx, ly)
        rw = wall_between(edges, base_x, base_y, rx, ry)
        visible.append(("center", depth, fw))
        visible.append(("left", depth, lw))
        visible.append(("right", depth, rw))
        if fw != 0:
            blocked_ahead = True
        if blocked_ahead:
            break

    canvas = Image.new("RGBA", (200, 140), (10, 10, 14, 255))
    # Draw far -> near.
    drawn = []
    for orient, depth, wallv in sorted(visible, key=lambda t: t[1], reverse=True):
        if wallv == 0:
            continue
        slot_key = f"{orient}_d{depth}"
        picker = pick_by_val.get(wallv, pick_by_val[2])
        oid = picker.get(slot_key)
        if oid is None:
            # Fallback to generic default.
            ids = slots_generic.get(slot_key, [])
            oid = ids[0] if ids else None
        if oid is None:
            continue
        img = owner_img.get(oid)
        if img is None:
            continue
        canvas.alpha_composite(img, (0, 0))
        drawn.append(
            {
                "slot": slot_key,
                "orient": orient,
                "depth": depth,
                "wall_value": wallv,
                "owner_id": oid,
            }
        )

    # Crop toward original viewport scale.
    out = canvas.crop((12, 14, 188, 126)).convert("RGB")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.save(args.out)
    if args.debug_json is not None:
        payload = {
            "map_id": args.map_id,
            "position": {"wx": wx, "wy": wy},
            "facing": args.facing,
            "visible": [
                {"orient": o, "depth": d, "wall_value": wv}
                for (o, d, wv) in visible
            ],
            "drawn": drawn,
            "pick_by_val": pick_by_val,
            "map_stream_info": map_stream_info if args.use_map_streams else {},
        }
        args.debug_json.parent.mkdir(parents=True, exist_ok=True)
        args.debug_json.write_text(json.dumps(payload, indent=2))
        print(f"Wrote {args.debug_json}")
    print(f"Wrote {args.out}")
    print(f"map={args.map_id} pos=({wx},{wy}) facing={args.facing}")
    print(f"slot picks by wall value: {pick_by_val}")
    if args.use_map_streams:
        print(f"map stream codes: {map_stream_info['codes']}")
        print(f"map stream sets(12): {map_stream_info['sets']}")
        print(f"wall->set map: {map_stream_info['set_map']}")
        if args.use_stream_offsets:
            print(f"wall->offset map: {map_stream_info['offset_map']}")
            print(f"wall offset streams: {map_stream_info['offset_streams']}")
        if map_stream_info["picked_codes_by_wall"]:
            print(f"picked stream codes by wall: {map_stream_info['picked_codes_by_wall']}")
        if map_stream_info["set_struct_scores"]:
            print(f"set structural scores: {map_stream_info['set_struct_scores']}")
    print(f"visible slots: {visible}")


if __name__ == "__main__":
    main()
