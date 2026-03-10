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


def decode_packed_plane(data: bytes, base: int, offset: int, bits: int):
    start = base + offset

    def get_field(idx: int) -> int:
        if bits == 2:
            b = data[start + (idx // 4)]
            shift = (idx % 4) * 2
            return (b >> shift) & 0x03
        if bits == 4:
            b = data[start + (idx // 2)]
            if idx & 1:
                return (b >> 4) & 0x0F
            return b & 0x0F
        raise ValueError(bits)

    vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
    for block in range(12):
        for row in range(8):
            for col in range(8):
                idx = (block << 6) + (row << 3) + col
                vals[block][row][col] = get_field(idx)
    return vals


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


def emulate_7ade_hit(origins, block_idx: int, wx: int, wy: int) -> int:
    # 7ADE: return block index iff (wx,wy) lies within the block's 8x8 origin box.
    try:
        ox, oy = origins[int(block_idx)]
    except Exception:
        return -1
    if ox <= int(wx) <= ox + 7 and oy <= int(wy) <= oy + 7:
        return int(block_idx)
    return -1


def emulate_7b1b_probe(origins, current_block: int, wx: int, wy: int, last_block_cache: int | None = None) -> dict:
    # 7B1B(inout block*, world_x, world_y, out_local_x*, out_local_y*)
    # Returns ax=0 on success (and updates block/cache), ax=1 on failure.
    cur = int(current_block) & 0xFFFF
    di = emulate_7ade_hit(origins, cur, wx, wy)
    if di < 0 and last_block_cache is not None:
        di = emulate_7ade_hit(origins, int(last_block_cache), wx, wy)
    if di < 0:
        si = (cur + 1) % 12
        while True:
            di = emulate_7ade_hit(origins, si, wx, wy)
            if di >= 0:
                break
            si = (si + 1) % 12
            if si == cur:
                return {"ax": 1, "ok": False, "world_x": int(wx), "world_y": int(wy), "block": cur}
    ox, oy = origins[int(di)]
    return {
        "ax": 0,
        "ok": True,
        "world_x": int(wx),
        "world_y": int(wy),
        "block": int(di),
        "local_x": int(wx) - int(ox),
        "local_y": int(wy) - int(oy),
        "last_block_cache": int(di),  # 7BC9 updates 0x4FA6 on success
    }


def emulate_7d0b_side_probe(origins, facing_idx: int, wx: int, wy: int, current_block: int, side_arg: int, last_block_cache: int | None = None) -> dict:
    # 7D0B as used by 7D8C side calls: rotate/apply (dx=side_arg, dy=0), then call 7B1B.
    x = int(wx)
    y = int(wy)
    dx = int(side_arg)
    dy = 0
    f = int(facing_idx) & 0xFFFF
    if f == 0:
        x += dx
        y += dy
    elif f == 1:
        x += dy
        y -= dx
    elif f == 2:
        x -= dx
        y -= dy
    elif f == 3:
        x -= dy
        y += dx
    return emulate_7b1b_probe(origins, int(current_block), x, y, last_block_cache=last_block_cache)


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
        return 0
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


def build_owner_runs(records: list[dict]) -> list[dict]:
    runs = []
    i = 0
    n = len(records)
    while i < n:
        owner = records[i]["owner_id"]
        j = i + 1
        while j < n and records[j]["owner_id"] == owner:
            j += 1
        runs.append({"start": i, "end": j, "owner_id": owner})
        i = j
    return runs


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


def parse_class_to_set_map(spec: str) -> dict[int, int]:
    out: dict[int, int] = {}
    for part in spec.split(","):
        p = part.strip()
        if not p or ":" not in p:
            continue
        a, b = p.split(":", 1)
        try:
            cls = int(a, 0)
            si = int(b, 0)
        except ValueError:
            continue
        out[cls] = si
    return out


def load_classifier_c4_class_map(path: Path) -> dict[int, int]:
    # Extract index->class-code from corrected 8175 table.
    try:
        doc = json.loads(path.read_text())
    except Exception:
        return {}
    tables = doc.get("tables", [])
    for t in tables:
        if t.get("name") != "8175.class_map_switch":
            continue
        out: dict[int, int] = {}
        for e in t.get("entries", []):
            try:
                idx = int(e.get("index"))
            except Exception:
                continue
            cs = e.get("class_code")
            if isinstance(cs, str) and cs.startswith("0x"):
                try:
                    out[idx] = int(cs, 16)
                except Exception:
                    continue
        return out
    return {}


def load_classifier_index_class_maps(path: Path) -> tuple[dict[int, int], dict[int, int]]:
    # Returns (map_a_8175, map_b_8332): index -> class_code.
    try:
        doc = json.loads(path.read_text())
    except Exception:
        return ({}, {})
    out_a: dict[int, int] = {}
    out_b: dict[int, int] = {}
    for t in doc.get("tables", []):
        name = str(t.get("name", ""))
        target = out_a if name == "8175.class_map_switch" else out_b if name == "8332.class_map_switch" else None
        if target is None:
            continue
        for e in t.get("entries", []):
            try:
                idx = int(e.get("index"))
            except Exception:
                continue
            cs = e.get("class_code")
            if isinstance(cs, str) and cs.startswith("0x"):
                try:
                    target[idx] = int(cs, 16)
                except Exception:
                    continue
    return (out_a, out_b)


def facing_to_index(facing: str) -> int:
    # Provisional orientation index for comparison against c2-derived modulo branch.
    return {"N": 0, "E": 1, "S": 2, "W": 3}.get(facing, 0)


def emulate_classifier_index(c4: int, c2: int, facing_idx: int, variant: str, seed_idx: int) -> int:
    # Corrected logic skeleton from 0x8175/0x8332:
    # - idx starts from helper-derived seed (unknown helper semantics)
    # - compute modulo gate from c2
    # - if modulo matches facing, idx is replaced by c4
    # 0x8175 path: (c2 + 1) % 4
    # 0x8332 path: (c2 + 3) % 4
    if variant == "A":
        rem = (int(c2) + 1) % 4
    else:
        rem = (int(c2) + 3) % 4
    return int(c4) if rem == int(facing_idx) else int(seed_idx)


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


def build_sprite_layers(sprites) -> tuple[list[Image.Image], list[Image.Image]]:
    # Transparent layer: palette index 0 treated as clear.
    # Opaque layer: palette index 0 kept as black.
    trans: list[Image.Image] = []
    opaque: list[Image.Image] = []
    for sp in sprites:
        timg = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
        oimg = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 255))
        pt = timg.load()
        po = oimg.load()
        for y in range(sp.height):
            row = y * sp.width
            for x in range(sp.width):
                idx = int(sp.pixels[row + x]) if row + x < len(sp.pixels) else 0
                if 0 <= idx < len(sp.palette):
                    rr, gg, bb = sp.palette[idx]
                else:
                    rr, gg, bb = (0, 0, 0)
                po[x, y] = (rr, gg, bb, 255)
                if idx == 0:
                    pt[x, y] = (0, 0, 0, 0)
                else:
                    pt[x, y] = (rr, gg, bb, 255)
        trans.append(timg)
        opaque.append(oimg)
    return trans, opaque


def aux_is_opaque(aux: int, mode: str = "heuristic") -> bool:
    if mode == "transparent":
        return False
    if mode == "opaque":
        return True
    # Heuristic from run distributions:
    # - aux 4 (dominant wall run) should be opaque polygon blit.
    # - keep low modes (0..3) transparent to preserve overlay behavior.
    return aux in (4, 5, 6, 7, 8, 9, 14, 18)


def render_owner_blitmode(
    owner_records,
    sprite_trans: list[Image.Image],
    sprite_opaque: list[Image.Image],
    canvas=(200, 140),
    blit_mode: str = "heuristic",
) -> Image.Image:
    im = Image.new("RGBA", canvas, (0, 0, 0, 0))
    for r in owner_records:
        t = int(r.get("tile_ref", 0))
        if t <= 0 or t == 255:
            continue
        idx = t - 1
        if idx < 0 or idx >= len(sprite_trans):
            continue
        aux = int(r.get("aux", 0))
        lay = sprite_opaque[idx] if aux_is_opaque(aux, blit_mode) else sprite_trans[idx]
        im.alpha_composite(lay, (int(r.get("x", 0)), int(r.get("y", 0))))
    return im


def alpha_composite_shifted(canvas: Image.Image, overlay: Image.Image, dx: int, dy: int) -> None:
    """Composite overlay at (dx,dy), allowing negative offsets by cropping first."""
    ov = overlay.convert("RGBA")
    ox0 = max(0, -int(dx))
    oy0 = max(0, -int(dy))
    ox1 = min(ov.width, canvas.width - int(dx))
    oy1 = min(ov.height, canvas.height - int(dy))
    if ox0 >= ox1 or oy0 >= oy1:
        return
    crop = ov.crop((ox0, oy0, ox1, oy1))
    canvas.alpha_composite(crop, (int(dx) + ox0, int(dy) + oy0))


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


def load_json_if_exists(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text())
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def resolve_pick_image(
    oid: int | None,
    pick_kind: str,
    owner_img: dict[int, Image.Image],
    run_img: dict[int, Image.Image],
    run_owner: dict[int, int],
    primitive_img: dict[int, Image.Image],
    primitive_owner: dict[int, int],
):
    if oid is None:
        return (None, None, None)
    img = None
    drawn_owner = oid
    drawn_kind = pick_kind
    if pick_kind == "record_run":
        img = run_img.get(oid)
        if img is not None:
            drawn_owner = run_owner.get(oid, oid)
        else:
            drawn_kind = "owner_fallback"
    elif pick_kind == "record_primitive":
        img = primitive_img.get(oid)
        if img is not None:
            drawn_owner = primitive_owner.get(oid, oid)
        else:
            drawn_kind = "owner_fallback"
    if img is None:
        img = owner_img.get(oid)
        if img is not None and drawn_kind == "owner_fallback":
            drawn_owner = oid
    return (img, drawn_owner, drawn_kind)


def _choose_pass_slot(pass_rec: dict) -> str:
    src = str(pass_rec.get("arg_bp6_source", ""))
    tgt = str(pass_rec.get("draw_target", ""))
    if src.endswith("0x5220"):
        return "center"
    if src.endswith("0x5222"):
        return "left"
    if src.endswith("0x5224"):
        return "right"
    if src.endswith("0x5226"):
        return "left"
    if src.endswith("0x5228"):
        return "right"
    if tgt == "0x8D07":
        bp6_map = pass_rec.get("immediate_by_bp_offset", {})
        side = bp6_map.get("0x08")
        return "left" if side == 0 else "right" if side == 2 else "center"
    return "center"


def _build_handler_call_map(doc: dict) -> dict[str, dict[int, list[dict]]]:
    out: dict[str, dict[int, list[dict]]] = {"0x85D0": {}, "0x8B18": {}}
    tbls = doc.get("tables", {})
    for tname, helper in (("85D0.class_draw_switch", "0x85D0"), ("8B18.class_draw_switch", "0x8B18")):
        rows = tbls.get(tname, [])
        if not isinstance(rows, list):
            continue
        hmap: dict[int, list[dict]] = {}
        for row in rows:
            try:
                idx = int(row.get("index"))
            except Exception:
                continue
            calls = row.get("draw_calls", [])
            if isinstance(calls, list):
                hmap[idx] = calls
        out[helper] = hmap
    return out


def _derive_draw_index_from_wall(
    wallv: int,
    fallback_seed_map: dict[int, int],
) -> int:
    if wallv <= 0:
        return 0
    return int(fallback_seed_map.get(int(wallv), 0))


def _helper_draw_modes_for_index(helper_draw_mode_doc: dict, helper: str, draw_index: int) -> list[str]:
    if not isinstance(helper_draw_mode_doc, dict):
        return []
    tbl_name = "85D0.class_draw_switch" if helper == "0x85D0" else "8B18.class_draw_switch" if helper == "0x8B18" else None
    if tbl_name is None:
        return []
    rec = (((helper_draw_mode_doc.get("tables") or {}).get(tbl_name) or {}).get(str(int(draw_index))) or {})
    modes = rec.get("modes", [])
    return [str(m) for m in modes] if isinstance(modes, list) else []


def _current_scene_origin_cell(visible_details: list[dict], facing_idx: int) -> tuple[int, int] | None:
    step_map = {
        0: (0, -1),
        1: (1, 0),
        2: (0, 1),
        3: (-1, 0),
    }
    step = step_map.get(int(facing_idx) & 3)
    if step is None:
        return None
    for row in visible_details:
        if not isinstance(row, dict):
            continue
        if str(row.get("orient")) != "center":
            continue
        try:
            if int(row.get("depth", -1)) != 1:
                continue
            base = row.get("base_cell", {}) or {}
            wx = int(base.get("wx"))
            wy = int(base.get("wy"))
        except Exception:
            continue
        return (wx - int(step[0]), wy - int(step[1]))
    return None


def _resolve_8d07_call_rows(
    *,
    pass_rec: dict,
    depth_index: int,
    visible_details: list[dict],
    facing_idx: int,
) -> tuple[list[dict], dict]:
    p_imms = pass_rec.get("immediate_by_bp_offset", {})
    if not isinstance(p_imms, dict):
        p_imms = {}
    scene_origin = _current_scene_origin_cell(visible_details, facing_idx)
    parity_521a = 0
    if scene_origin is not None:
        parity_521a = (int(scene_origin[0]) + int(scene_origin[1]) + (int(facing_idx) & 3)) & 1
    parity_3646 = 0
    table_5042_zero = True
    table_50aa_zero = True
    table_504e_zero = True

    rows: list[dict] = []
    if table_5042_zero:
        rows.append({"bp_offset_primary": "0x08", "depth_add": True, "imm_primary": None})
        if parity_521a != 0:
            rows.append({"bp_offset_primary": "0x0A", "depth_add": True, "imm_primary": None})
    if table_50aa_zero and table_504e_zero:
        rows.append({"bp_offset_primary": "0x0C", "depth_add": True, "imm_primary": None})
        if parity_521a != 0:
            rows.append({"bp_offset_primary": "0x0E", "depth_add": True, "imm_primary": None})
    elif not table_504e_zero:
        rows.append({"bp_offset_primary": "0x10", "depth_add": True, "imm_primary": None})
        if ((parity_521a + parity_3646) & 1) != 0:
            rows.append({"bp_offset_primary": "0x12", "depth_add": True, "imm_primary": None})
    trace = {
        "helper_selector": "0x8D07",
        "source": "8C23..8D12 branch model",
        "depth_index": int(depth_index),
        "scene_origin": [int(scene_origin[0]), int(scene_origin[1])] if scene_origin is not None else None,
        "parity_521a": int(parity_521a),
        "parity_3646": int(parity_3646),
        "table_5042_zero": bool(table_5042_zero),
        "table_50aa_zero": bool(table_50aa_zero),
        "table_504e_zero": bool(table_504e_zero),
        "selected_bp_offsets": [str(r.get("bp_offset_primary")) for r in rows],
        "ignored_bp_offsets": [k for k in sorted(p_imms.keys()) if k not in {str(r.get("bp_offset_primary")) for r in rows}],
    }
    return (rows, trace)


def _build_helper_36ac_call_map(doc: dict) -> dict[str, dict[int, list[dict]]]:
    out: dict[str, dict[int, list[dict]]] = {"0x85D0": {}, "0x8B18": {}, "0x8D07": {}}
    tbls = doc.get("tables", {})
    for tname, helper in (("85D0.class_draw_switch", "0x85D0"), ("8B18.class_draw_switch", "0x8B18")):
        rows = tbls.get(tname, [])
        if not isinstance(rows, list):
            continue
        hmap: dict[int, list[dict]] = {}
        for row in rows:
            try:
                idx = int(row.get("index"))
            except Exception:
                continue
            calls = row.get("calls_36ac", [])
            if isinstance(calls, list):
                hmap[idx] = [c for c in calls if isinstance(c, dict)]
        out[helper] = hmap
    rng = ((doc.get("ranges") or {}).get("8D07.helper_range") or {})
    calls = rng.get("calls_36ac", [])
    if isinstance(calls, list):
        out["0x8D07"][0] = [c for c in calls if isinstance(c, dict)]
    return out


def _build_direct_36ac_template_map(doc: dict) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for row in doc.get("direct_36ac_calls", []):
        if not isinstance(row, dict):
            continue
        try:
            call_addr = int(str(row.get("call_addr")), 16)
        except Exception:
            continue
        ctx = row.get("context_before", [])
        out[call_addr] = [str(v) for v in ctx] if isinstance(ctx, list) else []
    return out


def _template_line_addr(line: str) -> int | None:
    try:
        return int(str(line).split(":", 1)[0], 16)
    except Exception:
        return None


def _call_arg_has_depth_add(template_lines: list[str], *, source_addr: int | None, push_addr: int | None) -> bool:
    if source_addr is None or push_addr is None:
        return False
    for line in template_lines:
        la = _template_line_addr(line)
        if la is None or la <= int(source_addr) or la > int(push_addr):
            continue
        if "add    ax, word ptr [bp + 4]" in str(line).lower():
            return True
    return False


def _resolve_helper_direct_36ac_arg(
    arg_rec: dict,
    *,
    pass_immediates: dict,
    depth_index: int,
    call_addr: int | None,
    template_map: dict[int, list[str]],
) -> int | None:
    rec = arg_rec.get("resolved") if isinstance(arg_rec, dict) else None
    if not isinstance(rec, dict):
        rec = arg_rec if isinstance(arg_rec, dict) else {}
    source_kind = str(rec.get("source_kind") or rec.get("kind") or "")
    if source_kind == "imm":
        try:
            return int(rec.get("value")) & 0xFFFF
        except Exception:
            return None
    bp_offset = rec.get("bp_offset")
    if bp_offset is None:
        return None
    try:
        bp_offset = int(bp_offset)
    except Exception:
        return None
    base_val = pass_immediates.get(f"0x{bp_offset:02X}")
    if not isinstance(base_val, int):
        return None
    source_addr = rec.get("source_addr")
    push_addr = arg_rec.get("addr") if isinstance(arg_rec, dict) else None
    try:
        saddr = int(str(source_addr), 16) if source_addr is not None else None
    except Exception:
        saddr = None
    try:
        paddr = int(str(push_addr), 16) if push_addr is not None else None
    except Exception:
        paddr = None
    if call_addr is not None and _call_arg_has_depth_add(template_map.get(int(call_addr), []), source_addr=saddr, push_addr=paddr):
        base_val = int(base_val) + int(depth_index)
    return int(base_val) & 0xFFFF


def reconstruct_helper_direct_36ac_events(
    *,
    drawn_passes: list[dict],
    pass_param_doc: dict,
    helper_draw_calls_doc: dict,
    direct_36ac_template_doc: dict,
) -> tuple[list[dict], list[dict]]:
    pass_by_index: dict[int, dict] = {}
    pass_by_call_site: dict[str, dict] = {}
    for row in pass_param_doc.get("passes", []):
        if not isinstance(row, dict):
            continue
        try:
            pass_by_index[int(row.get("pass_index"))] = row
        except Exception:
            pass
        cs = row.get("draw_call_site")
        if cs is not None:
            pass_by_call_site[str(cs)] = row
    helper_map = _build_helper_36ac_call_map(helper_draw_calls_doc)
    template_map = _build_direct_36ac_template_map(direct_36ac_template_doc)
    events: list[dict] = []
    unresolved: list[dict] = []
    for prow in drawn_passes:
        if not isinstance(prow, dict):
            continue
        helper = str(prow.get("draw_target", ""))
        if helper not in ("0x85D0", "0x8B18", "0x8D07"):
            continue
        try:
            draw_index = int(prow.get("draw_index", 0))
            depth_index = int(prow.get("depth_index", 0))
        except Exception:
            continue
        pass_def = pass_by_call_site.get(str(prow.get("call_site"))) or pass_by_index.get(int(prow.get("pass_index", -1)))
        if not isinstance(pass_def, dict):
            unresolved.append(
                {
                    "reason": "missing_pass_definition",
                    "draw_target": helper,
                    "draw_index": draw_index,
                    "pass_index": prow.get("pass_index"),
                    "call_site": prow.get("call_site"),
                }
            )
            continue
        pass_immediates = pass_def.get("immediate_by_bp_offset", {})
        if not isinstance(pass_immediates, dict):
            pass_immediates = {}
        call_rows = (helper_map.get(helper) or {}).get(draw_index, [])
        if not call_rows:
            continue
        for call_row in call_rows:
            try:
                call_addr = int(str(call_row.get("call_addr")), 16)
            except Exception:
                call_addr = None
            args = []
            bad_args = []
            for arg_idx, arg in enumerate(call_row.get("args_callee_order", []), start=1):
                if not isinstance(arg, dict):
                    bad_args.append({"arg_index": arg_idx, "reason": "non_dict_arg"})
                    continue
                aval = _resolve_helper_direct_36ac_arg(
                    arg,
                    pass_immediates=pass_immediates,
                    depth_index=depth_index,
                    call_addr=call_addr,
                    template_map=template_map,
                )
                if aval is None:
                    bad_args.append(
                        {
                            "arg_index": arg_idx,
                            "arg": arg,
                            "reason": "unresolved_arg",
                        }
                    )
                    continue
                args.append(int(aval))
            if len(args) != 3:
                unresolved.append(
                    {
                        "reason": "unresolved_call_args",
                        "draw_target": helper,
                        "draw_index": draw_index,
                        "pass_index": prow.get("pass_index"),
                        "depth_index": depth_index,
                        "call_site": prow.get("call_site"),
                        "call_addr": call_row.get("call_addr"),
                        "bad_args": bad_args,
                    }
                )
                continue
            events.append(
                {
                    "driver_wrapper": "0x36AC",
                    "driver_args_wrapper_order": [int(args[0]), int(args[1]), int(args[2])],
                    "phase": "helper_direct_36ac",
                    "depth": int(depth_index) + 1,
                    "queue_index": None,
                    "source": {
                        "kind": "helper_direct_36ac",
                        "draw_target": helper,
                        "draw_index": draw_index,
                        "pass_index": prow.get("pass_index"),
                        "call_site": prow.get("call_site"),
                        "call_addr": call_row.get("call_addr"),
                        "slot_hint": prow.get("slot_hint"),
                        "wall_value": prow.get("wall_value"),
                    },
                }
            )
    return (events, unresolved)


def render_wmaze_pass_experimental(
    *,
    map_id: int,
    origins,
    facing_idx: int,
    canvas: Image.Image,
    visible: list[tuple[str, int, int]],
    visible_details: list[dict],
    primitive_img: dict[int, Image.Image],
    pass_param_doc: dict,
    handler_offsets_doc: dict,
    helper_draw_mode_doc: dict | None,
    fallback_seed_map: dict[int, int],
    drawidx_overrides: dict[tuple[int, str, str], int] | None = None,
    respect_helper_draw_modes: bool = False,
    suppress_direct_36ac_primitive_fallback: bool = False,
) -> tuple[list[dict], list[dict]]:
    passes = pass_param_doc.get("passes", [])
    if not isinstance(passes, list) or not passes:
        return ([], [])
    handler_call_map = _build_handler_call_map(handler_offsets_doc)

    slot_wall: dict[tuple[int, str], int] = {}
    for orient, depth, wallv in visible:
        slot_wall[(depth - 1, orient)] = int(wallv)

    drawn_passes: list[dict] = []
    gate_trace: list[dict] = []
    # 0x521E render-loop depth limit (exclusive), initialized to 4 in 0x91A3.
    loop_depth_limit = 4
    # Marker bytes at 0x5066/0x5067/0x5068 are zeroed at 0x90EB and later set by
    # 7D8C handler 0x7E7D depending on side (-1/0/+1).
    marker_506x: dict[str, list[int]] = {
        "5066": [0] * 16,
        "5067": [0] * 16,
        "5068": [0] * 16,
    }
    # Top-level WMAZE pass gates (per depth index), initialized to 1 in 0x90C0 loop.
    gate_flags: dict[int, dict[str, bool]] = {
        di: {
            "508a": True,
            "5082": True,
            "5072": True,
            "507a": True,
            "5092": True,
            "509a": True,
            "50a2": True,
            # Lower per-depth flags mutated by cleanup helpers 8EBB/8EE8/8F1A/8F4C.
            # These are distinct from the top-level pass gates above, but we track them
            # so gate traces reflect real cleanup side effects.
            "5073": True,
            "5074": True,
            "507b": True,
            "507c": True,
            "5083": True,
            "5084": True,
            "508b": True,
            "508c": True,
            "508d": True,
            "509b": True,
            "5093": True,
            "5094": True,
            "509c": True,
            "50a3": True,
            "50a4": True,
        }
        for di in range(4)
    }
    last_block_cache_4fa6: int | None = None

    def _gate_snapshot(di: int) -> dict[str, bool]:
        gf = gate_flags.get(int(di), {}) or {}
        return {
            k: bool(gf.get(k, False))
            for k in (
                "5072",
                "5073",
                "5074",
                "507a",
                "507b",
                "507c",
                "5082",
                "5083",
                "5084",
                "508b",
                "508c",
                "508d",
                "508a",
                "5092",
                "5093",
                "5094",
                "509a",
                "509b",
                "509c",
                "50a2",
                "50a3",
                "50a4",
            )
        }

    def _marker_window_snapshot(di: int) -> dict[str, list[int]]:
        base = 3 * int(di)
        out: dict[str, list[int]] = {}
        for k in ("5066", "5067", "5068"):
            arr = marker_506x.get(k, [])
            out[k] = [int(arr[i]) if 0 <= i < len(arr) else 0 for i in range(base, base + 3)]
        return out

    def apply_7d8c_topflag_sideeffects(
        di: int,
        side_arg: int,
        c4: int | None,
        local_coord_proxy: int | None,
        side_call_cell_exists: bool | None = None,
    ) -> None:
        # Partial emulation of 7D8C @ 7E54/7E7D -> 7ECA..7ED9.
        # The clear groups depend on `ax == side_arg` where side_arg in {-1,0,+1},
        # but only when the primary-mode path reaches 0x7E7D (handler 0x7E54 fallback).
        # For side calls (bp+0xE = -1/+1), 7D8C enters 7CA8 only when 7D0B returns 0
        # (success); nonzero return takes the early branch at 7DC2. Our proxy is side
        # cell existence, so skip side effects only when the side call likely fails.
        before_gate = _gate_snapshot(di)
        before_markers = _marker_window_snapshot(di)
        sideeffect_reason = "applied"
        if int(side_arg) != 0 and not bool(side_call_cell_exists):
            sideeffect_reason = "side_probe_failed_proxy"
            gate_trace.append(
                {
                    "event_type": "7d8c_topflag",
                    "depth_index": int(di),
                    "depth": int(di) + 1,
                    "side_arg": int(side_arg),
                    "c4": None if c4 is None else int(c4),
                    "local_coord_proxy": local_coord_proxy,
                    "side_call_cell_exists": bool(side_call_cell_exists),
                    "result": "skipped",
                    "skip_reason": sideeffect_reason,
                    "gate_before": before_gate,
                    "gate_after": _gate_snapshot(di),
                    "markers_before": before_markers,
                    "markers_after": _marker_window_snapshot(di),
                }
            )
            return
        # Primary switch appears c4-indexed; treat {4,5,12} as the current
        # disassembly-backed top-flag family. c4==0 was previously included here,
        # but that suppresses the visible center-wall pass on the live start scene.
        if c4 is None:
            sideeffect_reason = "missing_c4"
            gate_trace.append(
                {
                    "event_type": "7d8c_topflag",
                    "depth_index": int(di),
                    "depth": int(di) + 1,
                    "side_arg": int(side_arg),
                    "c4": None,
                    "local_coord_proxy": local_coord_proxy,
                    "side_call_cell_exists": bool(side_call_cell_exists) if side_call_cell_exists is not None else None,
                    "result": "skipped",
                    "skip_reason": sideeffect_reason,
                    "gate_before": before_gate,
                    "gate_after": _gate_snapshot(di),
                    "markers_before": before_markers,
                    "markers_after": _marker_window_snapshot(di),
                }
            )
            return
        c4i = int(c4)
        if c4i not in (4, 5, 12):
            sideeffect_reason = "c4_not_in_7e54_set"
            gate_trace.append(
                {
                    "event_type": "7d8c_topflag",
                    "depth_index": int(di),
                    "depth": int(di) + 1,
                    "side_arg": int(side_arg),
                    "c4": c4i,
                    "local_coord_proxy": local_coord_proxy,
                    "side_call_cell_exists": bool(side_call_cell_exists) if side_call_cell_exists is not None else None,
                    "result": "skipped",
                    "skip_reason": sideeffect_reason,
                    "gate_before": before_gate,
                    "gate_after": _gate_snapshot(di),
                    "markers_before": before_markers,
                    "markers_after": _marker_window_snapshot(di),
                }
            )
            return
        # 7E54 special-case bypass for dungeon/map mode 0x0C and [bp+0xC] < 9.
        # From the 7D0B -> 7B1B call mapping, 7D8C local [bp+0xC] is the block id.
        if int(map_id) == 0x0C and local_coord_proxy is not None and int(local_coord_proxy) < 9:
            sideeffect_reason = "map0c_local_block_bypass"
            gate_trace.append(
                {
                    "event_type": "7d8c_topflag",
                    "depth_index": int(di),
                    "depth": int(di) + 1,
                    "side_arg": int(side_arg),
                    "c4": c4i,
                    "local_coord_proxy": int(local_coord_proxy),
                    "side_call_cell_exists": bool(side_call_cell_exists) if side_call_cell_exists is not None else None,
                    "result": "skipped",
                    "skip_reason": sideeffect_reason,
                    "gate_before": before_gate,
                    "gate_after": _gate_snapshot(di),
                    "markers_before": before_markers,
                    "markers_after": _marker_window_snapshot(di),
                }
            )
            return
        # 7E7D writes byte [0x5067 + (3*depth + side_arg)] = 1.
        flat = 3 * int(di)
        if int(side_arg) < 0:
            marker_506x["5066"][flat] = 1
        elif int(side_arg) == 0:
            marker_506x["5067"][flat] = 1
        elif int(side_arg) > 0:
            marker_506x["5068"][flat] = 1
        gf = gate_flags.setdefault(di, {})
        if int(side_arg) < 0:
            gf["5072"] = False
            gf["507a"] = False
            gf["5082"] = False
        elif int(side_arg) == 0:
            gf["508a"] = False
        elif int(side_arg) > 0:
            gf["5092"] = False
            gf["509a"] = False
            gf["50a2"] = False
        gate_trace.append(
            {
                "event_type": "7d8c_topflag",
                "depth_index": int(di),
                "depth": int(di) + 1,
                "side_arg": int(side_arg),
                "c4": c4i,
                "local_coord_proxy": local_coord_proxy,
                "side_call_cell_exists": bool(side_call_cell_exists) if side_call_cell_exists is not None else None,
                "result": "applied",
                "gate_before": before_gate,
                "gate_after": _gate_snapshot(di),
                "markers_before": before_markers,
                "markers_after": _marker_window_snapshot(di),
            }
        )

    def pass_gate_key(pass_index: int) -> str | None:
        # Derived from corrected 0x91A0..0x9758 loop.
        if pass_index in (0, 1, 2):
            return "508a"
        if pass_index == 3:
            return "5082"
        if pass_index == 4:
            return "5072"
        if pass_index == 5:
            return "507a"
        if pass_index == 6:
            return "5092"
        if pass_index == 7:
            return "509a"
        if pass_index == 8:
            return "50a2"
        return None

    def _marker_check(base_key: str, di: int, class_idx: int) -> bool:
        arr = marker_506x.get(base_key)
        if arr is None:
            return False
        idx = 3 * int(di) + int(class_idx)
        return 0 <= idx < len(arr) and int(arr[idx]) == 1

    def _cleanup_pred_8df6_family(base_key: str, di: int, class_idx: int) -> bool:
        # Common predicate used by 8DF6 / 8EBB / 8EE8 / 8F1A / 8F4C.
        ci = int(class_idx)
        if ci == 2:
            return True
        if ci >= 5:
            return True
        return _marker_check(base_key, di, ci)

    def apply_cleanup_helper_effects(cleanup_target: str, di: int, class_idx: int, context: dict | None = None) -> None:
        nonlocal loop_depth_limit
        ct = str(cleanup_target or "")
        ci = int(class_idx)
        gf = gate_flags.setdefault(int(di), {})
        before_gate = _gate_snapshot(di)
        before_markers = _marker_window_snapshot(di)
        before_limit = int(loop_depth_limit)
        pred_detail: dict[str, object] = {}
        if ct == "0x8DF6":
            pred = _cleanup_pred_8df6_family("5067", di, ci)
            pred_detail["pred_8df6_family_5067"] = bool(pred)
            if pred:
                # 8DF6->8E17 clears a center-family block of per-depth flags and may
                # reduce 0x521E to (3*di+3) in byte-space; our `di` is already a
                # depth index so the effective loop cap remains `di + 3`.
                gf["508b"] = False
                gf["508c"] = False
                gf["508d"] = False
                gf["507b"] = False
                gf["5093"] = False
                gf["5074"] = False
                gf["507c"] = False
                gf["5094"] = False
                gf["509c"] = False
                loop_depth_limit = min(int(loop_depth_limit), int(di) + 3)
        elif ct == "0x8E59":
            # Clear when class!=0, or when class==0 and center marker byte is set.
            center_marker = _marker_check("5067", di, 0)
            pred = (ci != 0 or center_marker)
            pred_detail["class_nonzero"] = bool(ci != 0)
            pred_detail["center_marker_5067"] = bool(center_marker)
            if pred:
                gf["507a"] = False
                gf["5073"] = False
                gf["5084"] = False
        elif ct == "0x8E8A":
            # Same predicate as 8E59, but clears right-side top gate 0x5092.
            center_marker = _marker_check("5067", di, 0)
            pred = (ci != 0 or center_marker)
            pred_detail["class_nonzero"] = bool(ci != 0)
            pred_detail["center_marker_5067"] = bool(center_marker)
            if pred:
                gf["5092"] = False
                gf["509b"] = False
                gf["50a4"] = False
        elif ct == "0x8EBB":
            pred = _cleanup_pred_8df6_family("5066", di, ci)
            pred_detail["pred_8df6_family_5066"] = bool(pred)
            if pred:
                gf["5083"] = False
        elif ct == "0x8EE8":
            pred = _cleanup_pred_8df6_family("5066", di, ci)
            pred_detail["pred_8df6_family_5066"] = bool(pred)
            if pred:
                gf["5073"] = False
                gf["5084"] = False
        elif ct == "0x8F1A":
            pred = _cleanup_pred_8df6_family("5068", di, ci)
            pred_detail["pred_8df6_family_5068"] = bool(pred)
            if pred:
                gf["509b"] = False
                gf["50a4"] = False
        elif ct == "0x8F4C":
            pred = _cleanup_pred_8df6_family("5068", di, ci)
            pred_detail["pred_8df6_family_5068"] = bool(pred)
            if pred:
                gf["50a3"] = False
        gate_trace.append(
            {
                "event_type": "cleanup_helper",
                "depth_index": int(di),
                "depth": int(di) + 1,
                "cleanup_target": ct or None,
                "class_idx": ci,
                "loop_depth_limit_before": before_limit,
                "loop_depth_limit_after": int(loop_depth_limit),
                "gate_before": before_gate,
                "gate_after": _gate_snapshot(di),
                "markers_before": before_markers,
                "markers_after": _marker_window_snapshot(di),
                "predicates": pred_detail or None,
                "context": context or None,
            }
        )
    # WMAZE loop iterates depth index [0..3] and performs a fixed pass sequence.
    for di in range(4):
        if di >= int(loop_depth_limit):
            break
        if slot_wall.get((di, "center"), 0) == 0 and slot_wall.get((di, "left"), 0) == 0 and slot_wall.get((di, "right"), 0) == 0:
            continue
        # 0x90C0 loop computes 0x5220,0x5226,0x5228 via three separate 7D8C calls
        # (side args 0,-1,+1). Apply top-flag side effects per slot using that call's
        # own c4 value rather than reusing center c4 for all three.
        vd_by_orient: dict[str, dict] = {}
        for r in visible_details:
            if not isinstance(r, dict):
                continue
            try:
                if int(r.get("depth", -1)) != di + 1:
                    continue
            except Exception:
                continue
            orient_key = str(r.get("orient", ""))
            if orient_key and orient_key not in vd_by_orient:
                vd_by_orient[orient_key] = r

        for side_arg, orient_key in ((0, "center"), (-1, "left"), (1, "right")):
            vd = vd_by_orient.get(orient_key)
            if not isinstance(vd, dict):
                continue
            c4_val = vd.get("channel4_1f8")
            local_proxy = None
            side_exists = False
            if side_arg == 0:
                try:
                    cell_ref = vd.get("cell_ref", {}) or {}
                    if cell_ref.get("block") is not None:
                        local_proxy = int(cell_ref.get("block"))
                    side_exists = cell_ref.get("block") is not None
                    if cell_ref.get("block") is not None and last_block_cache_4fa6 is None:
                        last_block_cache_4fa6 = int(cell_ref.get("block"))
                except Exception:
                    local_proxy = None
                    side_exists = False
            else:
                cvd = vd_by_orient.get("center")
                if isinstance(cvd, dict):
                    try:
                        ccell = cvd.get("cell_ref", {}) or {}
                        cblock = ccell.get("block")
                        cwx = int((cvd.get("base_cell", {}) or {}).get("wx"))
                        cwy = int((cvd.get("base_cell", {}) or {}).get("wy"))
                        if cblock is not None:
                            probe = emulate_7d0b_side_probe(
                                origins,
                                int(facing_idx),
                                cwx,
                                cwy,
                                int(cblock),
                                int(side_arg),
                                last_block_cache=last_block_cache_4fa6,
                            )
                            side_exists = bool(probe.get("ok"))
                            if probe.get("ok"):
                                local_proxy = probe.get("block")
                                try:
                                    last_block_cache_4fa6 = int(probe.get("last_block_cache"))
                                except Exception:
                                    pass
                    except Exception:
                        pass
            apply_7d8c_topflag_sideeffects(di, side_arg, c4_val, local_proxy, side_exists)
        for p in passes:
            if not isinstance(p, dict):
                continue
            helper = str(p.get("draw_target", ""))
            pidx = int(p.get("pass_index", -1))
            slot = _choose_pass_slot(p)
            wallv = int(slot_wall.get((di, slot), 0))
            gate = p.get("gate")
            gate_key = pass_gate_key(pidx)
            gate_ok = True if gate_key is None else bool(gate_flags.get(di, {}).get(gate_key, True))
            if not gate_ok:
                gate_trace.append(
                    {
                        "event_type": "pass_skip",
                        "depth_index": di,
                        "depth": di + 1,
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "gate_skip_reason": "gate_flag_false",
                        "skipped_by_gate_flag": gate_key,
                        "wall_value": wallv,
                        "gate_before": _gate_snapshot(di),
                        "markers_before": _marker_window_snapshot(di),
                        "loop_depth_limit": int(loop_depth_limit),
                    }
                )
                continue
            if gate and wallv == 0:
                # Approximate gate using wall presence on the corresponding side slot.
                gate_trace.append(
                    {
                        "event_type": "pass_skip",
                        "depth_index": di,
                        "depth": di + 1,
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "gate_skip_reason": "wall_presence_gate_zero",
                        "wall_value": wallv,
                        "gate_before": _gate_snapshot(di),
                        "markers_before": _marker_window_snapshot(di),
                        "loop_depth_limit": int(loop_depth_limit),
                    }
                )
                continue
            draw_idx = int((drawidx_overrides or {}).get((di, helper, slot), _derive_draw_index_from_wall(wallv, fallback_seed_map)))
            helper_draw_modes = _helper_draw_modes_for_index(helper_draw_mode_doc or {}, helper, draw_idx)
            if respect_helper_draw_modes and helper_draw_modes:
                if "queue_84f1" in helper_draw_modes and "direct_36ac" not in helper_draw_modes:
                    cleanup_target = str(p.get("cleanup_target") or "")
                    drawn_passes.append(
                        {
                            "depth_index": di,
                            "depth": di + 1,
                            "slot_hint": slot,
                            "wall_value": wallv,
                            "draw_target": helper,
                            "draw_index": draw_idx,
                            "helper_draw_modes": helper_draw_modes,
                            "records": [],
                            "pass_index": pidx,
                            "call_site": p.get("draw_call_site"),
                            "cleanup_target": cleanup_target or None,
                            "suppressed_by_helper_draw_mode": "queue_84f1_only",
                        }
                    )
                    gate_trace.append(
                        {
                            "event_type": "pass_skip",
                            "depth_index": di,
                            "depth": di + 1,
                            "pass_index": pidx,
                            "draw_target": helper,
                            "draw_index": draw_idx,
                            "slot_hint": slot,
                            "gate_skip_reason": "helper_draw_mode_queue_only",
                            "skipped_by_helper_draw_mode": "queue_84f1_only",
                            "helper_draw_modes": helper_draw_modes,
                            "wall_value": wallv,
                            "gate_before": _gate_snapshot(di),
                            "markers_before": _marker_window_snapshot(di),
                            "loop_depth_limit": int(loop_depth_limit),
                        }
                    )
                    if cleanup_target:
                        apply_cleanup_helper_effects(
                            cleanup_target,
                            di,
                            int(draw_idx),
                            context={
                                "pass_index": pidx,
                                "draw_target": helper,
                                "slot_hint": slot,
                                "draw_index": draw_idx,
                                "wall_value": wallv,
                                "pass_result": "suppressed_by_helper_draw_mode",
                            },
                        )
                    continue
            if suppress_direct_36ac_primitive_fallback and helper_draw_modes:
                if "direct_36ac" in helper_draw_modes and "queue_84f1" not in helper_draw_modes:
                    cleanup_target = str(p.get("cleanup_target") or "")
                    drawn_passes.append(
                        {
                            "depth_index": di,
                            "depth": di + 1,
                            "slot_hint": slot,
                            "wall_value": wallv,
                            "draw_target": helper,
                            "draw_index": draw_idx,
                            "helper_draw_modes": helper_draw_modes,
                            "records": [],
                            "pass_index": pidx,
                            "call_site": p.get("draw_call_site"),
                            "cleanup_target": cleanup_target or None,
                            "suppressed_by_helper_draw_mode": "direct_36ac_only",
                        }
                    )
                    gate_trace.append(
                        {
                            "event_type": "pass_skip",
                            "depth_index": di,
                            "depth": di + 1,
                            "pass_index": pidx,
                            "draw_target": helper,
                            "draw_index": draw_idx,
                            "slot_hint": slot,
                            "gate_skip_reason": "helper_draw_mode_direct_36ac_only",
                            "skipped_by_helper_draw_mode": "direct_36ac_only",
                            "helper_draw_modes": helper_draw_modes,
                            "wall_value": wallv,
                            "gate_before": _gate_snapshot(di),
                            "markers_before": _marker_window_snapshot(di),
                            "loop_depth_limit": int(loop_depth_limit),
                        }
                    )
                    if cleanup_target:
                        apply_cleanup_helper_effects(
                            cleanup_target,
                            di,
                            int(draw_idx),
                            context={
                                "pass_index": pidx,
                                "draw_target": helper,
                                "slot_hint": slot,
                                "draw_index": draw_idx,
                                "wall_value": wallv,
                                "pass_result": "suppressed_by_direct_36ac_helper_mode",
                            },
                        )
                    continue
            call_rows = handler_call_map.get(helper, {}).get(draw_idx, [])
            selector_trace = None
            if helper == "0x8D07" and not call_rows:
                call_rows, selector_trace = _resolve_8d07_call_rows(
                    pass_rec=p,
                    depth_index=di,
                    visible_details=visible_details,
                    facing_idx=facing_idx,
                )
            if not call_rows:
                gate_trace.append(
                    {
                        "event_type": "pass_skip",
                        "depth_index": di,
                        "depth": di + 1,
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "draw_index": draw_idx,
                        "wall_value": wallv,
                        "gate_skip_reason": "no_handler_call_rows",
                        "selector_trace": selector_trace,
                        "gate_before": _gate_snapshot(di),
                        "markers_before": _marker_window_snapshot(di),
                        "loop_depth_limit": int(loop_depth_limit),
                    }
                )
                continue
            p_imms = p.get("immediate_by_bp_offset", {})
            recs: list[int] = []
            for cr in call_rows:
                bp_off = cr.get("bp_offset_primary")
                base_idx = None
                if isinstance(bp_off, str):
                    v = p_imms.get(bp_off)
                    if isinstance(v, int):
                        base_idx = v
                if base_idx is None:
                    iv = cr.get("imm_primary")
                    if isinstance(iv, int):
                        base_idx = iv
                if base_idx is None:
                    continue
                rec_idx = int(base_idx) + (di if bool(cr.get("depth_add", False)) else 0)
                recs.append(rec_idx)
            # Preserve order but avoid double-blitting identical primitive repeatedly in same pass.
            seen = set()
            kept = []
            for rix in recs:
                if rix in seen:
                    continue
                seen.add(rix)
                kept.append(rix)
            if not kept:
                gate_trace.append(
                    {
                        "event_type": "pass_skip",
                        "depth_index": di,
                        "depth": di + 1,
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "draw_index": draw_idx,
                        "wall_value": wallv,
                        "gate_skip_reason": "no_record_indices_resolved",
                        "selector_trace": selector_trace,
                        "gate_before": _gate_snapshot(di),
                        "markers_before": _marker_window_snapshot(di),
                        "loop_depth_limit": int(loop_depth_limit),
                    }
                )
                continue
            drew_any = False
            missing_imgs: list[int] = []
            for rec_idx in kept:
                img = primitive_img.get(rec_idx)
                if img is None:
                    missing_imgs.append(int(rec_idx))
                    continue
                canvas.alpha_composite(img, (0, 0))
                drew_any = True
            cleanup_target = str(p.get("cleanup_target") or "")
            if cleanup_target:
                apply_cleanup_helper_effects(
                    cleanup_target,
                    di,
                    int(draw_idx),
                    context={
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "draw_index": draw_idx,
                        "wall_value": wallv,
                        "records": kept,
                        "drew_any": bool(drew_any),
                    },
                )
            if not drew_any:
                gate_trace.append(
                    {
                        "event_type": "pass_skip",
                        "depth_index": di,
                        "depth": di + 1,
                        "pass_index": pidx,
                        "draw_target": helper,
                        "slot_hint": slot,
                        "draw_index": draw_idx,
                        "wall_value": wallv,
                        "cleanup_target": cleanup_target or None,
                        "gate_skip_reason": "all_records_missing_images",
                        "records": kept,
                        "missing_records": missing_imgs[:16],
                        "missing_records_count": len(missing_imgs),
                        "selector_trace": selector_trace,
                        "gate_before": _gate_snapshot(di),
                        "gate_after": _gate_snapshot(di),
                        "markers_before": _marker_window_snapshot(di),
                        "markers_after": _marker_window_snapshot(di),
                        "loop_depth_limit": int(loop_depth_limit),
                    }
                )
            if drew_any:
                drawn_passes.append(
                    {
                        "depth_index": di,
                        "depth": di + 1,
                        "slot_hint": slot,
                        "wall_value": wallv,
                        "draw_target": helper,
                        "draw_index": draw_idx,
                        "helper_draw_modes": helper_draw_modes or None,
                        "records": kept,
                        "pass_index": pidx,
                        "call_site": p.get("draw_call_site"),
                        "cleanup_target": cleanup_target or None,
                        "selector_trace": selector_trace,
                        "gate_skip_reason": None,
                    }
                )
    return (drawn_passes, gate_trace)


def emulate_7d8c_tail_switch(c4: int, base_idx: int, c2: int, facing_idx: int) -> int:
    # Exact logic from 0x8055..0x8156, excluding side-effect flag writes.
    c4 = int(c4)
    c2 = int(c2)
    idx = int(base_idx)
    if not (c2 == int(facing_idx) or c4 == 6 or c4 > 12):
        # c2 != facing and c4 in [7..12] keeps prior idx
        return idx
    if c4 < 0x10:
        tail_map = {
            1: 5,
            2: 6,
            3: 8,
            4: 9,
            5: 14,
            7: 4,
            8: 7,
            9: 10,
            10: 11,
            11: 12,
            12: 13,
        }
        return int(tail_map.get(c4, idx))
    return idx


def emulate_7d8c_draw_index_from_view(
    *,
    map_id: int,
    origins,
    visible_by_depth_slot: dict[int, dict[str, dict]],
    depth: int,
    slot: str,
    wallv: int,
    facing_idx: int,
    last_block_cache_ref: list[int | None] | None = None,
) -> int:
    # Approximate-exact emulation of 0x7D8C return for the values used in
    # 0x5220/0x5226/0x5228:
    # - base idx from local wall class (0..3)
    # - early side-neighbor shortcut for left/right calls
    # - tail-switch transform from c4/c2
    vd = (visible_by_depth_slot.get(depth) or {}).get(slot)
    if not vd and slot != "center":
        vd = (visible_by_depth_slot.get(depth) or {}).get("center")
    if not vd:
        return int(wallv)
    try:
        if slot == "center" and isinstance(last_block_cache_ref, list):
            bseed = (vd.get("cell_ref", {}) or {}).get("block")
            if bseed is not None:
                last_block_cache_ref[:] = [int(bseed)]
    except Exception:
        pass
    bx = int(vd.get("base_cell", {}).get("wx", 0))
    by = int(vd.get("base_cell", {}).get("wy", 0))
    side = 0
    if slot == "left":
        side = -1
    elif slot == "right":
        side = 1
    if side != 0:
        # In 7D8C, the early shortcut class (0 on maps 10/12, else 2) is returned
        # when 7D0B returns nonzero (branch at 7DBE/7DC0), i.e. when the side probe
        # does not resolve into a valid map block. Use a 7D0B-style rotated side probe
        # from the center cell when available (closer to the real call semantics).
        probe = None
        cvd = (visible_by_depth_slot.get(depth) or {}).get("center")
        if isinstance(cvd, dict):
            try:
                cblock = (cvd.get("cell_ref", {}) or {}).get("block")
                cwx = int((cvd.get("base_cell", {}) or {}).get("wx"))
                cwy = int((cvd.get("base_cell", {}) or {}).get("wy"))
                if cblock is not None:
                    probe = emulate_7d0b_side_probe(
                        origins,
                        int(facing_idx),
                        cwx,
                        cwy,
                        int(cblock),
                        int(side),
                        last_block_cache=(last_block_cache_ref[0] if isinstance(last_block_cache_ref, list) and last_block_cache_ref else None),
                    )
                    if bool(probe.get("ok")) and isinstance(last_block_cache_ref, list):
                        try:
                            last_block_cache_ref[:] = [int(probe.get("last_block_cache"))]
                        except Exception:
                            pass
            except Exception:
                probe = None
        if probe is None:
            try:
                sblock = int((vd.get("cell_ref", {}) or {}).get("block"))
            except Exception:
                sblock = 0
            probe = emulate_7b1b_probe(origins, sblock, int(bx), int(by), last_block_cache=None)
        if not bool(probe.get("ok")):
            return 0 if int(map_id) in (0x0A, 0x0C) else 2
    c4 = vd.get("channel4_1f8")
    c2 = vd.get("channel2_378")
    if c4 is None or c2 is None:
        return int(wallv)
    return emulate_7d8c_tail_switch(int(c4), int(wallv), int(c2), int(facing_idx))


