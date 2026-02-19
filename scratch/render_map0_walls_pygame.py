from pathlib import Path
import random

import pygame


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")
MAP_W = 16
MAP_H = 24

# Bytes identified for map-0 top-right wall channel edits.
OFF_TOP = 0x259     # adds bits 0x80 and 0x20
OFF_BOTTOM = 0x25D  # adds bits 0x80 and 0x20
OFF_LEFT_ANCHOR = 0x23E  # adds bit 0x02 for tested wall at x=0, y=7
OFF_LEFT_A = 0x31A  # adds bit 0x80
OFF_LEFT = 0x31B    # adds bits 0x80 and 0x08
OFF_RIGHT_A = 0x31C  # adds bit 0x80
OFF_RIGHT = 0x31D   # adds bits 0x80 and 0x08
OFF_VERT_ANCHOR = 0x220  # adds bit 0x02 for tested vertical wall at (x=1, y=7)
OFF_LOW_H_ANCHOR = 0x2FE  # adds bit 0x02 for tested horizontal wall at (x=0, y=14)
MAP0_WALL_BASE = 0x01C0


def load(path: Path) -> bytes:
    return path.read_bytes()


def decode_map0_baseline_walls(data: bytes):
    """Best-effort full-map wall decode from map-0 8-byte cells.

    This is the established baseline interpretation used in existing tools:
    - byte 3 bit 0x80: north wall
    - byte 3 bit 0x40: south wall
    - byte 5 bit 0x80: west wall
    - byte 5 bit 0x20: east wall
    """
    walls = []
    for idx in range(400):
        r = idx // 20
        c = idx % 20
        base = idx * 8
        b3 = data[base + 3]
        b5 = data[base + 5]
        walls.append(
            {
                "r": r,
                "c": c,
                "n": bool(b3 & 0x80),
                "s": bool(b3 & 0x40),
                "w": bool(b5 & 0x80),
                "e": bool(b5 & 0x20),
            }
        )
    return walls


def edge_flags(data: bytes):
    left_anchor = data[OFF_LEFT_ANCHOR]
    vert_anchor = data[OFF_VERT_ANCHOR]
    low_h_anchor = data[OFF_LOW_H_ANCHOR]
    top = data[OFF_TOP]
    bottom = data[OFF_BOTTOM]
    left_a = data[OFF_LEFT_A]
    left = data[OFF_LEFT]
    right_a = data[OFF_RIGHT_A]
    right = data[OFF_RIGHT]
    return {
        # Anchor from controlled edit: horizontal wall between rows 6 and 7 at column 0.
        "anchor_x0_y7": bool(left_anchor & 0x02),
        # Anchor from controlled edit: vertical wall between columns 0 and 1 on row 7.
        "anchor_v_x1_y7": bool(vert_anchor & 0x02),
        # Anchor from controlled edit: horizontal wall between rows 13 and 14 at column 0.
        "anchor_x0_y14": bool(low_h_anchor & 0x02),
        # Horizontal top edge segments at y=0 for x=[16,17,18,19].
        "top_x16": bool(top & 0x08),
        "top_x17": bool(top & 0x02),
        "top_x18": bool(top & 0x80),
        "top_x19": bool(top & 0x20),
        # Horizontal bottom edge segments at y=2 for x=[16,17,18,19].
        "bottom_x16": bool(bottom & 0x08),
        "bottom_x17": bool(bottom & 0x02),
        "bottom_x18": bool(bottom & 0x80),
        "bottom_x19": bool(bottom & 0x20),
        # Vertical edges for y segments [0,1]:
        # x=16 comes from OFF_LEFT_A/OFF_RIGHT_A, x=18 from OFF_LEFT, x=20 from OFF_RIGHT.
        "x16_y0": bool(left_a & 0x80),
        "x16_y1": bool(right_a & 0x80),
        "x18_y0": bool(left & 0x80),
        "x18_y1": bool(left & 0x08),
        "x20_y0": bool(right & 0x80),
        "x20_y1": bool(right & 0x08),
    }


def decode_wall_planes(data: bytes, base: int):
    """Decode full 2-bit wall planes (12 blocks x 8x8 cells).

    Runtime semantics recovered from WMAZE:
    - base+0x60: adjacency on +Y (south edge of local cell)
    - base+0x120: adjacency on +X (east edge of local cell)
    Non-zero field means blocked.
    """
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


def rotate_local_edge(kind, x, y, rot):
    """Rotate one local block edge in 8x8 cell space by 0/90/180/270 CW."""
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
    """Return per-block wall edge maps from decoded planes.

    Keys:
    - ("h", x, y): horizontal edge from (x,y) to (x+1,y)
    - ("v", x, y): vertical edge from (x,y) to (x,y+1)
    """
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
    overlap = 0
    conflict = 0
    for vals in seen.values():
        if len(vals) < 2:
            continue
        overlap += len(vals) - 1
        trues = sum(1 for v in vals if v)
        falses = len(vals) - trues
        # Reward only true-edge agreement; do not reward empty overlap.
        score += trues * (trues - 1) * 1.0
        score -= trues * falses * 3.0
        if trues and falses:
            conflict += 1

    # Penalize placements far outside known map extents (16x24).
    span_pen = 0.0
    for ox, oy in origins:
        if ox < -8:
            span_pen += (-8 - ox) * 2.0
        if oy < -8:
            span_pen += (-8 - oy) * 2.0
        if ox > MAP_W:
            span_pen += (ox - MAP_W) * 2.0
        if oy > MAP_H:
            span_pen += (oy - MAP_H) * 2.0

    # Small tie-breaker: prefer some overlap, but not enough to dominate.
    score += overlap * 0.05
    score -= span_pen
    return score, conflict


def infer_block_layout(fields, seed=1337, fixed_origins=None, block_rot=0):
    per_block = block_plane_maps(fields, block_rot=block_rot)
    rng = random.Random(seed)
    fixed_origins = fixed_origins or {}

    best_layout = None
    best_score = -1e18

    for _ in range(40):
        origins = [(rng.randint(-4, MAP_W), rng.randint(-4, MAP_H)) for _ in range(12)]
        for b, pos in fixed_origins.items():
            origins[b] = pos
        score, _ = score_layout(origins, per_block)

        for _step in range(4500):
            b = rng.randrange(12)
            if b in fixed_origins:
                continue
            ox, oy = origins[b]
            cand = (ox + rng.choice([-1, 0, 1]), oy + rng.choice([-1, 0, 1]))
            if cand == (ox, oy):
                continue
            trial = list(origins)
            trial[b] = cand
            tscore, _ = score_layout(trial, per_block)
            if tscore >= score:
                origins = trial
                score = tscore

        if score > best_score:
            best_score = score
            best_layout = origins

    return best_layout


def compose_edges(fields, origins, block_rot=0):
    per_block = block_plane_maps(fields, block_rot=block_rot)
    agg = {}
    for b in range(12):
        ox, oy = origins[b]
        for (kind, x, y), v in per_block[b].items():
            key = (kind, x + ox, y + oy)
            agg.setdefault(key, []).append(v)
    return agg


def diff_added_edges(orig_fields, mod_fields, origins, block_rot=0):
    o_maps = block_plane_maps(orig_fields, block_rot=block_rot)
    m_maps = block_plane_maps(mod_fields, block_rot=block_rot)
    out = set()
    for b in range(12):
        ox, oy = origins[b]
        all_keys = set(o_maps[b].keys()) | set(m_maps[b].keys())
        for key in all_keys:
            ov = o_maps[b].get(key, False)
            mv = m_maps[b].get(key, False)
            if mv and not ov:
                kind, x, y = key
                out.add((kind, x + ox, y + oy))
    return out


def find_alignment_shift(added_edges):
    # Known map0 additions from controlled edits.
    target_h = {(0, 7), (0, 14), (16, 0), (17, 0), (18, 0), (19, 0), (16, 2), (17, 2), (18, 2), (19, 2)}
    target_v = {(1, 7), (16, 0), (16, 1), (18, 0), (18, 1), (20, 0), (20, 1)}

    best = (0, 0)
    best_score = -10**9
    for sx in range(-30, 31):
        for sy in range(-30, 31):
            hit = 0
            miss = 0
            for kind, x, y in added_edges:
                tx = x + sx
                ty = y + sy
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
            score = hit * 10 - miss
            if score > best_score:
                best_score = score
                best = (sx, sy)
    return best, best_score


def block_added_local_edges(orig_fields, mod_fields, block_rot=0):
    o_maps = block_plane_maps(orig_fields, block_rot=block_rot)
    m_maps = block_plane_maps(mod_fields, block_rot=block_rot)
    out = {}
    for b in range(12):
        s = set()
        all_keys = set(o_maps[b].keys()) | set(m_maps[b].keys())
        for key in all_keys:
            if m_maps[b].get(key, False) and not o_maps[b].get(key, False):
                s.add(key)
        out[b] = s
    return out


def infer_anchor_fixed_origins(orig_fields, mod_fields, block_rot=0):
    """Infer high-confidence fixed origins from known map0 edits.

    - Block with 14 added edges is anchored to top-right 2x2 region.
    - Remaining added blocks are fitted to left-column anchor edits.
    """
    adds = block_added_local_edges(orig_fields, mod_fields, block_rot=block_rot)

    fixed = {}
    # Known top-right edge set from controlled edits on map0 (20x20):
    # two adjacent 2x2 squares at x=16..19, y=0..1.
    top_h = {(16, 0), (17, 0), (18, 0), (19, 0), (16, 2), (17, 2), (18, 2), (19, 2)}
    top_v = {(16, 0), (16, 1), (18, 0), (18, 1), (20, 0), (20, 1)}

    # Find the block with the 14-edge edit signature.
    sig_block = None
    for b, s in adds.items():
        if len(s) == 14:
            sig_block = b
            break
    if sig_block is not None:
        best = None
        best_score = -10**9
        for ox in range(-10, 25):
            for oy in range(-10, 25):
                hit = 0
                miss = 0
                for kind, x, y in adds[sig_block]:
                    gx = x + ox
                    gy = y + oy
                    if kind == "h":
                        if (gx, gy) in top_h:
                            hit += 1
                        else:
                            miss += 1
                    else:
                        if (gx, gy) in top_v:
                            hit += 1
                        else:
                            miss += 1
                sc = hit * 20 - miss
                if sc > best_score:
                    best_score = sc
                    best = (ox, oy)
        fixed[sig_block] = best

    # Fit smaller anchor edits near left column.
    # Observed from controlled edits:
    # - one block contributes horizontal at x=0,y=14
    # - one block contributes horizontal at x=0,y=7 and vertical around x=1,y=6/7
    for b, s in adds.items():
        if not s or b in fixed:
            continue
        best = None
        best_score = -10**9
        for ox in range(-4, 6):
            for oy in range(-2, MAP_H + 1):
                hit = 0
                miss = 0
                for kind, x, y in s:
                    gx = x + ox
                    gy = y + oy
                    if len(s) == 1:
                        ok = kind == "h" and (gx, gy) == (0, 14)
                    else:
                        ok = (kind == "h" and (gx, gy) == (0, 7)) or (
                            kind == "v" and (gx, gy) in {(1, 6), (1, 7)}
                        )
                    if ok:
                        hit += 1
                    else:
                        miss += 1
                sc = hit * 12 - miss
                if sc > best_score:
                    best_score = sc
                    best = (ox, oy)
        fixed[b] = best

    return fixed


def draw_grid(screen, ox, oy, cell):
    color = (70, 70, 70)
    for i in range(21):
        x = ox + i * cell
        y = oy + i * cell
        pygame.draw.line(screen, color, (x, oy), (x, oy + 20 * cell), 1)
        pygame.draw.line(screen, color, (ox, y), (ox + 20 * cell, y), 1)


def draw_baseline_walls(screen, ox, oy, cell, walls, color, width=2):
    for t in walls:
        r = t["r"]
        c = t["c"]
        x0 = ox + c * cell
        x1 = x0 + cell
        y0 = oy + r * cell
        y1 = y0 + cell
        if t["n"]:
            pygame.draw.line(screen, color, (x0, y0), (x1, y0), width)
        if t["s"]:
            pygame.draw.line(screen, color, (x0, y1), (x1, y1), width)
        if t["w"]:
            pygame.draw.line(screen, color, (x0, y0), (x0, y1), width)
        if t["e"]:
            pygame.draw.line(screen, color, (x1, y0), (x1, y1), width)


def draw_perimeter(screen, ox, oy, cell, flags, color, width=4):
    if flags["anchor_x0_y7"]:
        xa = ox + 0 * cell
        xb = ox + 1 * cell
        y = oy + 7 * cell
        pygame.draw.line(screen, color, (xa, y), (xb, y), width)
    if flags["anchor_x0_y14"]:
        xa = ox + 0 * cell
        xb = ox + 1 * cell
        y = oy + 14 * cell
        pygame.draw.line(screen, color, (xa, y), (xb, y), width)
    if flags["anchor_v_x1_y7"]:
        x = ox + 1 * cell
        y0 = oy + 7 * cell
        y1 = oy + 8 * cell
        pygame.draw.line(screen, color, (x, y0), (x, y1), width)

    # Top-right local channel region with two adjacent 2x2 squares:
    # cells (16..19, 0..1), vertical boundaries x=16,18,20.
    xm = ox + 16 * cell
    x0 = ox + 18 * cell
    x1 = ox + 19 * cell
    x2 = ox + 20 * cell
    y0 = oy + 0 * cell
    y1 = oy + 1 * cell
    y2 = oy + 2 * cell

    if flags["top_x16"]:
        pygame.draw.line(screen, color, (xm, y0), (xm + cell, y0), width)
    if flags["top_x17"]:
        pygame.draw.line(screen, color, (xm + cell, y0), (x0, y0), width)
    if flags["top_x18"]:
        pygame.draw.line(screen, color, (x0, y0), (x1, y0), width)
    if flags["top_x19"]:
        pygame.draw.line(screen, color, (x1, y0), (x2, y0), width)

    if flags["bottom_x16"]:
        pygame.draw.line(screen, color, (xm, y2), (xm + cell, y2), width)
    if flags["bottom_x17"]:
        pygame.draw.line(screen, color, (xm + cell, y2), (x0, y2), width)
    if flags["bottom_x18"]:
        pygame.draw.line(screen, color, (x0, y2), (x1, y2), width)
    if flags["bottom_x19"]:
        pygame.draw.line(screen, color, (x1, y2), (x2, y2), width)

    if flags["x16_y0"]:
        pygame.draw.line(screen, color, (xm, y0), (xm, y1), width)
    if flags["x16_y1"]:
        pygame.draw.line(screen, color, (xm, y1), (xm, y2), width)

    if flags["x18_y0"]:
        pygame.draw.line(screen, color, (x0, y0), (x0, y1), width)
    if flags["x18_y1"]:
        pygame.draw.line(screen, color, (x0, y1), (x0, y2), width)

    if flags["x20_y0"]:
        pygame.draw.line(screen, color, (x2, y0), (x2, y1), width)
    if flags["x20_y1"]:
        pygame.draw.line(screen, color, (x2, y1), (x2, y2), width)


def draw_block_atlas(screen, ox, oy, cell, fields, color, width=2, flip_v=False):
    """Render all decoded wall-plane fields in 12 block panels (4x3)."""
    panel_w = 8 * cell
    panel_h = 8 * cell
    gap = cell

    # Grid and walls per block.
    font = pygame.font.SysFont("consolas", 14)
    for block in range(12):
        bx = block % 4
        by = block // 4
        px = ox + bx * (panel_w + gap)
        py = oy + by * (panel_h + gap)

        # Panel frame
        pygame.draw.rect(screen, (80, 80, 90), (px, py, panel_w, panel_h), 1)
        label = font.render(f"B{block}", True, (180, 180, 190))
        screen.blit(label, (px + 2, py + 2))

        # Internal 8x8 grid
        for i in range(9):
            x = px + i * cell
            y = py + i * cell
            pygame.draw.line(screen, (55, 55, 60), (x, py), (x, py + panel_h), 1)
            pygame.draw.line(screen, (55, 55, 60), (px, y), (px + panel_w, y), 1)

    # Wall edges from planes.
    for t in fields:
        block = t["block"]
        bx = block % 4
        by = block // 4
        px = ox + bx * (panel_w + gap)
        py = oy + by * (panel_h + gap)
        dr = 7 - t["row"] if flip_v else t["row"]
        x0 = px + t["col"] * cell
        y0 = py + dr * cell
        x1 = x0 + cell
        y1 = y0 + cell

        if t["south"] != 0:
            hy = y0 if flip_v else y1
            pygame.draw.line(screen, color, (x0, hy), (x1, hy), width)
        if t["east"] != 0:
            pygame.draw.line(screen, color, (x1, y0), (x1, y1), width)


def draw_block_quad_2x2(screen, ox, oy, cell, fields, color, width=2):
    """Render blocks in a fixed inspection layout:
    top row: B2 B3
    bottom row: B0 B1
    """
    panel_w = 8 * cell
    panel_h = 8 * cell
    gap = cell
    font = pygame.font.SysFont("consolas", 14)

    layout = {2: (0, 0), 3: (1, 0), 0: (0, 1), 1: (1, 1), 10: (0, 2), 11: (1, 2)}

    for block, (gx, gy) in layout.items():
        px = ox + gx * (panel_w + gap)
        py = oy + gy * (panel_h + gap)
        pygame.draw.rect(screen, (80, 80, 90), (px, py, panel_w, panel_h), 1)
        label = font.render(f"B{block}", True, (180, 180, 190))
        screen.blit(label, (px + 2, py + 2))
        for i in range(9):
            x = px + i * cell
            y = py + i * cell
            pygame.draw.line(screen, (55, 55, 60), (x, py), (x, py + panel_h), 1)
            pygame.draw.line(screen, (55, 55, 60), (px, y), (px + panel_w, y), 1)

    # Use the same raw owner-edge rendering as the right-panel atlas, but subset layout.
    for t in fields:
        block = t["block"]
        if block not in layout:
            continue
        gx, gy = layout[block]
        px = ox + gx * (panel_w + gap)
        py = oy + gy * (panel_h + gap)
        dr = 7 - t["row"]
        x0 = px + t["col"] * cell
        y0 = py + dr * cell
        x1 = x0 + cell
        y1 = y0 + cell
        if t["south"] != 0:
            pygame.draw.line(screen, color, (x0, y0), (x1, y0), width)
        if t["east"] != 0:
            pygame.draw.line(screen, color, (x1, y0), (x1, y1), width)


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


def resolve_world_cell(origins, wx, wy, prefer_block=None):
    """Resolve world cell (wx,wy) -> (block,row,col) from block origins."""
    if prefer_block is not None:
        ox, oy = origins[prefer_block]
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return prefer_block, wy - oy, wx - ox
    for b, (ox, oy) in enumerate(origins):
        if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
            return b, wy - oy, wx - ox
    return None


def wall_mode_value(a_vals, b_vals, origins, block, row, col, mode):
    """Approximate WMAZE:0x53AA directional read.

    mode 0: local south-edge plane (+0x60)
    mode 1: local east-edge plane (+0x120)
    mode 2: north neighbor via world resolve, then +0x60
    mode 3: west neighbor via world resolve, then +0x120
    """
    if mode == 0:
        return a_vals[block][row][col]
    if mode == 1:
        return b_vals[block][row][col]

    ox, oy = origins[block]
    wx = ox + col
    wy = oy + row
    if mode == 2:
        res = resolve_world_cell(origins, wx, wy - 1, prefer_block=block)
        if res is None:
            return 2
        rb, rr, rc = res
        return a_vals[rb][rr][rc]
    if mode == 3:
        res = resolve_world_cell(origins, wx - 1, wy, prefer_block=block)
        if res is None:
            return 2
        rb, rr, rc = res
        return b_vals[rb][rr][rc]
    return 0


def draw_block_quad_resolved(screen, ox, oy, cell, fields, origins, color, width=2):
    """Render inspection blocks using directional wall accessor semantics."""
    panel_w = 8 * cell
    panel_h = 8 * cell
    gap = cell
    font = pygame.font.SysFont("consolas", 14)
    layout = {2: (0, 0), 3: (1, 0), 0: (0, 1), 1: (1, 1), 10: (0, 2), 11: (1, 2)}

    for block, (gx, gy) in layout.items():
        px = ox + gx * (panel_w + gap)
        py = oy + gy * (panel_h + gap)
        pygame.draw.rect(screen, (80, 80, 90), (px, py, panel_w, panel_h), 1)
        label = font.render(f"B{block}", True, (180, 180, 190))
        screen.blit(label, (px + 2, py + 2))
        for i in range(9):
            x = px + i * cell
            y = py + i * cell
            pygame.draw.line(screen, (55, 55, 60), (x, py), (x, py + panel_h), 1)
            pygame.draw.line(screen, (55, 55, 60), (px, y), (px + panel_w, y), 1)

    a_vals, b_vals = build_plane_values(fields)
    for block, (gx, gy) in layout.items():
        px = ox + gx * (panel_w + gap)
        py = oy + gy * (panel_h + gap)
        for row in range(8):
            # Vertical flip: row 0 is at visual bottom (dr=7), row 7 at visual top (dr=0).
            dr = 7 - row
            for col in range(8):
                # Use local values whenever possible; only cross-resolve at true
                # top/left boundaries where WMAZE would query neighbor blocks.
                s = a_vals[block][row][col] != 0
                e = b_vals[block][row][col] != 0
                if row > 0:
                    n = a_vals[block][row - 1][col] != 0
                else:
                    n = wall_mode_value(a_vals, b_vals, origins, block, row, col, 2) != 0
                if col > 0:
                    w = b_vals[block][row][col - 1] != 0
                else:
                    w = wall_mode_value(a_vals, b_vals, origins, block, row, col, 3) != 0
                x0 = px + col * cell
                y0 = py + dr * cell
                x1 = x0 + cell
                y1 = y0 + cell
                # flipped vertically: source south appears at panel top.
                if s:
                    pygame.draw.line(screen, color, (x0, y0), (x1, y0), width)
                if n:
                    pygame.draw.line(screen, color, (x0, y1), (x1, y1), width)
                if w:
                    pygame.draw.line(screen, color, (x0, y0), (x0, y1), width)
                if e:
                    pygame.draw.line(screen, color, (x1, y0), (x1, y1), width)


def stitched_bounds(*aggs):
    # Determine dynamic bounds from present (true) edges.
    points = []
    for agg_edges in aggs:
        for (kind, x, y), vals in agg_edges.items():
            if sum(1 for v in vals if v) == 0:
                continue
            points.append((x, y))
            if kind == "h":
                points.append((x + 1, y))
            else:
                points.append((x, y + 1))

    if not points:
        return None

    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    return min_x, max_x, min_y, max_y


def draw_stitched(screen, ox, oy, cell, agg_edges, color, width=2, bounds=None):
    if bounds is None:
        bounds = stitched_bounds(agg_edges)
    if bounds is None:
        return
    min_x, max_x, min_y, max_y = bounds

    # Draw dynamic reference grid.
    for i in range(max_x - min_x + 1):
        x = ox + i * cell
        pygame.draw.line(screen, (55, 55, 65), (x, oy), (x, oy + (max_y - min_y) * cell), 1)
    for i in range(max_y - min_y + 1):
        y = oy + i * cell
        pygame.draw.line(screen, (55, 55, 65), (ox, y), (ox + (max_x - min_x) * cell, y), 1)

    for (kind, x, y), vals in agg_edges.items():
        trues = sum(1 for v in vals if v)
        falses = len(vals) - trues
        if trues == 0:
            continue

        edge_color = (255, 80, 80) if (trues and falses) else color
        px = ox + (x - min_x) * cell
        py = oy + (y - min_y) * cell
        if kind == "h":
            pygame.draw.line(screen, edge_color, (px, py), (px + cell, py), width)
        else:
            pygame.draw.line(screen, edge_color, (px, py), (px, py + cell), width)

    # Draw canonical map bounds (16x24) in green when visible in this frame.
    map_min_x, map_max_x = 0, MAP_W
    map_min_y, map_max_y = 0, MAP_H
    if map_max_x >= min_x and map_min_x <= max_x and map_max_y >= min_y and map_min_y <= max_y:
        gx0 = ox + (map_min_x - min_x) * cell
        gy0 = oy + (map_min_y - min_y) * cell
        gw = (map_max_x - map_min_x) * cell
        gh = (map_max_y - map_min_y) * cell
        pygame.draw.rect(screen, (80, 170, 110), (gx0, gy0, gw, gh), 2)


def draw_block_origin_overlay(screen, ox, oy, cell, bounds, origins):
    if bounds is None:
        return
    min_x, max_x, min_y, max_y = bounds
    font = pygame.font.SysFont("consolas", 16)
    for b, (bx, by) in enumerate(origins):
        # 8x8 local block footprint in stitched coordinates.
        x0 = ox + (bx - min_x) * cell
        y0 = oy + (by - min_y) * cell
        w = 8 * cell
        h = 8 * cell
        # Skip fully off-screen in stitched panel.
        if x0 > ox + (max_x - min_x) * cell or y0 > oy + (max_y - min_y) * cell:
            continue
        if x0 + w < ox or y0 + h < oy:
            continue
        pygame.draw.rect(screen, (80, 220, 220), (x0, y0, w, h), 1)
        label = font.render(f"B{b}", True, (80, 240, 240))
        screen.blit(label, (x0 + 2, y0 + 2))


def diff_flags(orig_flags, mod_flags):
    out = {}
    for k in mod_flags:
        out[k] = mod_flags[k] and not orig_flags[k]
    return out


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Render map0 walls from decoded wall planes")
    parser.add_argument("--stitched", action="store_true", help="Show experimental stitched global panel")
    parser.add_argument(
        "--block-rot",
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help="Rotate decoded 8x8 block edge coordinates before stitching",
    )
    args = parser.parse_args()
    block_rot = (args.block_rot // 90) % 4

    orig = load(ORIG_PATH)
    mod = load(MOD_PATH)
    orig_baseline = decode_map0_baseline_walls(orig)
    mod_baseline = decode_map0_baseline_walls(mod)
    orig_planes = decode_wall_planes(orig, MAP0_WALL_BASE)
    mod_planes = decode_wall_planes(mod, MAP0_WALL_BASE)
    fixed = infer_anchor_fixed_origins(orig_planes, mod_planes, block_rot=block_rot)
    layout = infer_block_layout(mod_planes, fixed_origins=fixed, block_rot=block_rot)
    orig_stitched = compose_edges(orig_planes, layout, block_rot=block_rot)
    mod_stitched = compose_edges(mod_planes, layout, block_rot=block_rot)
    orig_f = edge_flags(orig)
    mod_f = edge_flags(mod)
    add_f = diff_flags(orig_f, mod_f)

    pygame.init()
    screen_w = 1760 if args.stitched else 1320
    screen = pygame.display.set_mode((screen_w, 940))
    pygame.display.set_caption("Map 0 2x2 Top-Right Wall Parse")
    font = pygame.font.SysFont("consolas", 20)
    clock = pygame.time.Clock()

    ox, oy, cell = 60, 120, 32

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        screen.fill((26, 26, 30))
        draw_grid(screen, ox, oy, cell)

        # Full-map baseline decode first.
        draw_baseline_walls(screen, ox, oy, cell, orig_baseline, (70, 100, 130), 1)
        draw_baseline_walls(screen, ox, oy, cell, mod_baseline, (170, 200, 230), 2)

        # Original walls (dim) then modified walls (bright), then added walls (red).
        draw_perimeter(screen, ox, oy, cell, orig_f, (100, 100, 130), 3)
        draw_perimeter(screen, ox, oy, cell, mod_f, (210, 210, 240), 4)
        draw_perimeter(screen, ox, oy, cell, add_f, (255, 80, 80), 7)

        # Full wall-plane atlas (all original and modified walls, not just edited subset).
        atlas_x = ox + 20 * cell + 70
        atlas_y = oy
        draw_block_atlas(screen, atlas_x, atlas_y, 10, orig_planes, (100, 100, 130), 1, flip_v=True)
        draw_block_atlas(screen, atlas_x, atlas_y, 10, mod_planes, (220, 220, 240), 2, flip_v=True)

        # Focused 2x2 inspection panel: B2 B3 over B0 B1.
        quad_x = atlas_x
        quad_y = atlas_y + 3 * (8 * 10 + 10) + 28
        draw_block_quad_resolved(screen, quad_x, quad_y, 18, orig_planes, layout, (100, 100, 130), 1)
        draw_block_quad_resolved(screen, quad_x, quad_y, 18, mod_planes, layout, (220, 220, 240), 2)

        if args.stitched:
            # Auto-stitched global composite from block overlaps.
            stitched_x = atlas_x + 4 * (8 * 10 + 10) + 40
            stitched_y = oy
            bounds = stitched_bounds(orig_stitched, mod_stitched)
            draw_stitched(screen, stitched_x, stitched_y, 24, orig_stitched, (110, 110, 145), 1, bounds=bounds)
            draw_stitched(screen, stitched_x, stitched_y, 24, mod_stitched, (220, 220, 245), 2, bounds=bounds)
            draw_block_origin_overlay(screen, stitched_x, stitched_y, 24, bounds, layout)

        lines = [
            "Map 0 parse from NEWGAME.DBS vs NEWGAME_original.DBS",
            "Baseline all-wall decode: byte3/byte5 directional bits over 20x20 cells",
            "Offsets: 0x220, 0x23E, 0x259, 0x25D, 0x2FE, 0x31A, 0x31B, 0x31C, 0x31D",
            "Parsed top-right channel: two adjacent 2x2 squares (cells 16..19, rows 0..1)",
            "Right panel: full decoded 2-bit wall planes (12 blocks x 8x8), all walls",
            "Bottom-right panel: B2 B3 over B0 B1 over B10 B11 (0x53AA-style resolved)",
            "Use --stitched to show experimental global composite",
            f"Block local rotation: {args.block_rot} deg",
            f"Auto layout (true-edge overlap score): {layout}",
            f"Fixed block anchors: {fixed}",
            "Blue dim=original, white=modified, red=added",
            "Esc = quit",
        ]
        for i, text in enumerate(lines):
            surf = font.render(text, True, (220, 220, 220))
            screen.blit(surf, (80, 20 + i * 22))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
