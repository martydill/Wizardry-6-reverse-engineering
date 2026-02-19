from __future__ import annotations

import argparse
from pathlib import Path

import pygame


ORIG_PATH = Path("gamedata/NEWGAME_original.DBS")
MOD_PATH = Path("gamedata/NEWGAME.DBS")

# Recovered from WBASE load path:
# - header read size: 0x019E
# - per-entry read sizes: 0x3304 + 0x3306 = 0x0C0E
MAP_HEADER_SIZE = 0x019E
MAP_RECORD_SIZE = 0x0C0E


def load(path: Path) -> bytes:
    return path.read_bytes()


def record_base(map_id: int) -> int:
    return MAP_HEADER_SIZE + map_id * MAP_RECORD_SIZE


def decode_wall_planes(data: bytes, base: int):
    """Decode WMAZE 2-bit wall planes for one map record."""
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
    # mode 0/1: local south/east.
    if mode == 0:
        return a_vals[block][row][col]
    if mode == 1:
        return b_vals[block][row][col]

    # mode 2/3: cross-block north/west via world resolver.
    ox, oy = origins[block]
    wx = ox + col
    wy = oy + row
    if mode == 2:
        res = resolve_world_cell(origins, wx, wy - 1, prefer_block=block)
    else:
        res = resolve_world_cell(origins, wx - 1, wy, prefer_block=block)

    # WMAZE fallback: for map IDs 0x0A/0x0C, OOB behaves as open; otherwise blocked.
    if res is None:
        return 0 if map_id in (0x0A, 0x0C) else 2

    rb, rr, rc = res
    return a_vals[rb][rr][rc] if mode == 2 else b_vals[rb][rr][rc]


def build_mode_boundaries(a_vals, b_vals, origins, map_id, block):
    h = [[False] * 8 for _ in range(9)]
    v = [[False] * 9 for _ in range(8)]
    for y in range(9):
        for x in range(8):
            if y == 0:
                h[y][x] = wall_mode_value(a_vals, b_vals, origins, map_id, block, 0, x, 2) != 0
            else:
                h[y][x] = wall_mode_value(a_vals, b_vals, origins, map_id, block, y - 1, x, 0) != 0
    for y in range(8):
        for x in range(9):
            if x == 0:
                v[y][x] = wall_mode_value(a_vals, b_vals, origins, map_id, block, y, 0, 3) != 0
            else:
                v[y][x] = wall_mode_value(a_vals, b_vals, origins, map_id, block, y, x - 1, 1) != 0
    return h, v


def draw_block_panel(screen, ox, oy, cell, boundaries, color, width):
    h, v = boundaries
    for i in range(9):
        x = ox + i * cell
        y = oy + i * cell
        pygame.draw.line(screen, (56, 56, 62), (x, oy), (x, oy + 8 * cell), 1)
        pygame.draw.line(screen, (56, 56, 62), (ox, y), (ox + 8 * cell, y), 1)

    for y in range(9):
        yy = oy + y * cell
        for x in range(8):
            if h[y][x]:
                x0 = ox + x * cell
                pygame.draw.line(screen, color, (x0, yy), (x0 + cell, yy), width)
    for y in range(8):
        y0 = oy + y * cell
        for x in range(9):
            if v[y][x]:
                xx = ox + x * cell
                pygame.draw.line(screen, color, (xx, y0), (xx, y0 + cell), width)


def block_enabled(origins, b):
    x, y = origins[b]
    return not (x == 0 and y == 0)


def stitched_bounds(origins):
    xs = [x for x, _ in origins]
    ys = [y for _, y in origins]
    return min(xs), min(ys), max(xs) + 8, max(ys) + 8


def draw_stitched(screen, ox, oy, cell, boundaries_by_block, origins, color, width, flip_x=False, flip_y=False):
    min_x, min_y, max_x, max_y = stitched_bounds(origins)
    surf_w = max(1, (max_x - min_x) * cell)
    surf_h = max(1, (max_y - min_y) * cell)
    tmp = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    for b in range(12):
        if b not in boundaries_by_block:
            continue
        if not block_enabled(origins, b):
            continue
        bx, by = origins[b]
        px = (bx - min_x) * cell
        py = (by - min_y) * cell
        draw_block_panel(tmp, px, py, cell, boundaries_by_block[b], color, width)

    if flip_x or flip_y:
        tmp = pygame.transform.flip(tmp, flip_x, flip_y)
    screen.blit(tmp, (ox, oy))


def collect_world_edges(boundaries_by_block, origins):
    out = set()
    for b in range(12):
        if b not in boundaries_by_block:
            continue
        if not block_enabled(origins, b):
            continue
        ox, oy = origins[b]
        h, v = boundaries_by_block[b]
        for y in range(9):
            for x in range(8):
                if h[y][x]:
                    out.add(("h", ox + x, oy + y))
        for y in range(8):
            for x in range(9):
                if v[y][x]:
                    out.add(("v", ox + x, oy + y))
    return out


def draw_world_edges(screen, ox, oy, cell, edges, origins, color, width, flip_x=False, flip_y=False):
    min_x, min_y, max_x, max_y = stitched_bounds(origins)
    surf_w = max(1, (max_x - min_x) * cell)
    surf_h = max(1, (max_y - min_y) * cell)
    tmp = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    for kind, x, y in edges:
        px = (x - min_x) * cell
        py = (y - min_y) * cell
        if kind == "h":
            pygame.draw.line(tmp, color, (px, py), (px + cell, py), width)
        else:
            pygame.draw.line(tmp, color, (px, py), (px, py + cell), width)

    if flip_x or flip_y:
        tmp = pygame.transform.flip(tmp, flip_x, flip_y)
    screen.blit(tmp, (ox, oy))


def collect_world_edge_values(a_vals, b_vals, origins, map_id):
    out = []
    for b, (ox, oy) in enumerate(origins):
        if not block_enabled(origins, b):
            continue
        for y in range(9):
            for x in range(8):
                if y == 0:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, 0, x, 2)
                else:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y - 1, x, 0)
                if val:
                    out.append(("h", ox + x, oy + y, val))
        for y in range(8):
            for x in range(9):
                if x == 0:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y, 0, 3)
                else:
                    val = wall_mode_value(a_vals, b_vals, origins, map_id, b, y, x - 1, 1)
                if val:
                    out.append(("v", ox + x, oy + y, val))
    return out


def draw_edge_markers(
    screen, ox, oy, cell, edge_vals, origins, color, radius=2, value_filter=(1, 3), flip_x=False, flip_y=False
):
    min_x, min_y, max_x, max_y = stitched_bounds(origins)
    surf_w = max(1, (max_x - min_x) * cell)
    surf_h = max(1, (max_y - min_y) * cell)
    tmp = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

    for kind, x, y, val in edge_vals:
        if val not in value_filter:
            continue
        px = (x - min_x) * cell
        py = (y - min_y) * cell
        if kind == "h":
            cx, cy = px + (cell // 2), py
        else:
            cx, cy = px, py + (cell // 2)
        pygame.draw.circle(tmp, color, (cx, cy), radius)

    if flip_x or flip_y:
        tmp = pygame.transform.flip(tmp, flip_x, flip_y)
    screen.blit(tmp, (ox, oy))


def main():
    ap = argparse.ArgumentParser(description="Render reconstructed maze walls from WBASE/WMAZE load model")
    ap.add_argument("--map-id", type=lambda s: int(s, 0), default=0, help="Map id (default 0)")
    args = ap.parse_args()

    orig = load(ORIG_PATH)
    mod = load(MOD_PATH)
    max_maps = max(1, (len(mod) - MAP_HEADER_SIZE) // MAP_RECORD_SIZE)

    def decode_for(map_id: int):
        base = record_base(map_id)
        if base + MAP_RECORD_SIZE > len(mod):
            raise ValueError(f"map-id {map_id} base 0x{base:X} outside NEWGAME.DBS")
        orig_a, orig_b = decode_wall_planes(orig, base)
        mod_a, mod_b = decode_wall_planes(mod, base)
        origins = decode_origins(mod, base)
        orig_bounds = {}
        mod_bounds = {}
        for b in range(12):
            orig_bounds[b] = build_mode_boundaries(orig_a, orig_b, origins, map_id, b)
            mod_bounds[b] = build_mode_boundaries(mod_a, mod_b, origins, map_id, b)
        orig_edge_vals = collect_world_edge_values(orig_a, orig_b, origins, map_id)
        mod_edge_vals = collect_world_edge_values(mod_a, mod_b, origins, map_id)
        return base, origins, orig_bounds, mod_bounds, orig_edge_vals, mod_edge_vals

    map_id = max(0, min(args.map_id, max_maps - 1))
    base, origins, orig_bounds, mod_bounds, orig_edge_vals, mod_edge_vals = decode_for(map_id)

    pygame.init()
    screen = pygame.display.set_mode((1700, 980))
    pygame.display.set_caption("Reconstructed Maze Walls")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 17)

    panel_cell = 14
    gap = 12
    p_w = 8 * panel_cell
    p_h = 8 * panel_cell
    atlas_x = 24
    atlas_y = 90

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_RIGHT:
                map_id = (map_id + 1) % max_maps
                base, origins, orig_bounds, mod_bounds, orig_edge_vals, mod_edge_vals = decode_for(map_id)
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_LEFT:
                map_id = (map_id - 1) % max_maps
                base, origins, orig_bounds, mod_bounds, orig_edge_vals, mod_edge_vals = decode_for(map_id)

        screen.fill((20, 20, 24))

        # 4x3 block atlas.
        for b in range(12):
            gx = b % 4
            gy = b // 4
            px = atlas_x + gx * (p_w + gap)
            py = atlas_y + gy * (p_h + gap)
            pygame.draw.rect(screen, (84, 84, 92), (px, py, p_w, p_h), 1)
            lab = f"B{b} ({origins[b][0]},{origins[b][1]})"
            screen.blit(font.render(lab, True, (180, 180, 190)), (px, py - 18))
            draw_block_panel(screen, px, py, panel_cell, orig_bounds[b], (100, 110, 140), 1)
            draw_block_panel(screen, px, py, panel_cell, mod_bounds[b], (230, 235, 245), 2)

        # Stitched composite.
        stitched_cell = 8
        min_x, min_y, max_x, max_y = stitched_bounds(origins)
        stitched_w = max(1, (max_x - min_x) * stitched_cell)
        stitched_h = max(1, (max_y - min_y) * stitched_cell)
        desired_x = atlas_x + 4 * (p_w + gap) + 24
        max_x_fit = screen.get_width() - stitched_w - 20
        st_x = max(20, min(desired_x, max_x_fit))
        st_y = atlas_y
        max_y_fit = screen.get_height() - stitched_h - 20
        st_y = max(20, min(st_y, max_y_fit))
        orig_edges = collect_world_edges(orig_bounds, origins)
        mod_edges = collect_world_edges(mod_bounds, origins)
        added_edges = mod_edges - orig_edges
        draw_stitched(
            screen, st_x, st_y, stitched_cell, orig_bounds, origins, (100, 110, 140), 1, flip_y=True
        )
        draw_stitched(
            screen, st_x, st_y, stitched_cell, mod_bounds, origins, (230, 235, 245), 2, flip_y=True
        )
        draw_world_edges(
            screen, st_x, st_y, stitched_cell, added_edges, origins, (255, 80, 80), 3, flip_y=True
        )
        # Value semantics (current best RE model):
        # - 1: passage-like special edge
        # - 3: door-like special edge
        draw_edge_markers(
            screen,
            st_x,
            st_y,
            stitched_cell,
            mod_edge_vals,
            origins,
            (80, 180, 220),
            radius=2,
            value_filter=(1,),
            flip_y=True,
        )
        draw_edge_markers(
            screen,
            st_x,
            st_y,
            stitched_cell,
            mod_edge_vals,
            origins,
            (170, 120, 60),
            radius=2,
            value_filter=(3,),
            flip_y=True,
        )

        lines = [
            f"Map {map_id} reconstructed from base=0x{base:X} (record stride 0x{MAP_RECORD_SIZE:X})",
            "Walls: mode-resolved 2-bit planes (+0x60/+0x120), stitched by +0x1E0/+0x1EC origin tables",
            f"Blue=original, White=modified, Red=added, Cyan=passages(v=1), Brown=doors(v=3), Left/Right=map prev/next, Esc=quit (0..{max_maps - 1})",
        ]
        for i, t in enumerate(lines):
            screen.blit(font.render(t, True, (220, 220, 225)), (24, 20 + i * 18))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
