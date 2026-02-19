from __future__ import annotations

import argparse
import importlib.util
import json
from collections import defaultdict
from pathlib import Path

import pygame
from PIL import Image


def load_proto():
    p = Path("scratch/render_map_3d_owner_prototype.py")
    spec = importlib.util.spec_from_file_location("render_map_3d_owner_prototype", p)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to import {p}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pil_to_surface(img: Image.Image) -> pygame.Surface:
    mode = img.mode
    data = img.tobytes()
    return pygame.image.fromstring(data, img.size, mode)


def try_step(mod, edges, wx: int, wy: int, facing: str, forward: bool = True) -> tuple[int, int]:
    dx, dy = mod.dir_vec(facing)
    if not forward:
        dx, dy = -dx, -dy
    w = mod.wall_between(edges, wx, wy, dx, dy)
    if w != 0:
        return wx, wy
    return wx + dx, wy + dy


def render_view(mod, edges, owner_img, slots_generic, pick_by_val, wx: int, wy: int, facing: str) -> Image.Image:
    dx, dy = mod.dir_vec(facing)
    lx, ly = mod.left_vec(dx, dy)
    rx, ry = -lx, -ly

    visible = []
    blocked_ahead = False
    for depth in range(1, 5):
        base_x = wx + dx * (depth - 1)
        base_y = wy + dy * (depth - 1)
        fw = mod.wall_between(edges, base_x, base_y, dx, dy)
        lw = mod.wall_between(edges, base_x, base_y, lx, ly)
        rw = mod.wall_between(edges, base_x, base_y, rx, ry)
        visible.append(("center", depth, fw))
        visible.append(("left", depth, lw))
        visible.append(("right", depth, rw))
        if fw != 0:
            blocked_ahead = True
        if blocked_ahead:
            break

    canvas = Image.new("RGBA", (200, 140), (10, 10, 14, 255))
    for orient, depth, wallv in sorted(visible, key=lambda t: t[1], reverse=True):
        if wallv == 0:
            continue
        slot_key = f"{orient}_d{depth}"
        picker = pick_by_val.get(wallv, pick_by_val[2])
        oid = picker.get(slot_key)
        if oid is None:
            ids = slots_generic.get(slot_key, [])
            oid = ids[0] if ids else None
        if oid is None:
            continue
        img = owner_img.get(oid)
        if img is None:
            continue
        canvas.alpha_composite(img, (0, 0))
    return canvas.crop((12, 14, 188, 126)).convert("RGB")


def main() -> None:
    ap = argparse.ArgumentParser(description="Interactive MAZEDATA 3D viewer using real wall/map streams.")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--map-id", type=int, default=11)
    ap.add_argument("--facing", choices=["N", "E", "S", "W"], default="N")
    ap.add_argument("--scale", type=int, default=4)
    ap.add_argument("--stream-high-mode", choices=["minus28", "highbit", "identity"], default="minus28")
    ap.add_argument("--stream-code-map-file", type=Path, default=None)
    ap.add_argument("--slot-candidates", type=Path, default=Path("scratch/owner_slot_candidates/slot_candidates.json"))
    args = ap.parse_args()

    mod = load_proto()
    db = (args.gamedata / "NEWGAME.DBS").read_bytes()
    base = mod.record_base(args.map_id)
    a_vals, b_vals = mod.decode_wall_planes(db, base)
    origins = mod.decode_origins(db, base)
    edges = mod.collect_world_edge_values(a_vals, b_vals, origins, args.map_id)

    active = [(x, y) for (x, y) in origins if not (x == 0 and y == 0)]
    if not active:
        raise RuntimeError("No active blocks for map")
    wx, wy = active[0][0] + 3, active[0][1] + 3
    facing = args.facing

    sprites = mod.decode_mazedata_tiles(args.gamedata / "MAZEDATA.EGA")
    all_records = mod.parse_display_records(args.gamedata / "MAZEDATA.EGA")
    by_owner = defaultdict(list)
    for r in all_records:
        by_owner[r["owner_id"]].append(r)
    owner_img = {oid: mod.render_owner(rs, sprites) for oid, rs in by_owner.items()}

    slot_data = json.loads(args.slot_candidates.read_text())
    slots_generic = slot_data["slot_candidates"]
    slots_by_val = slot_data.get("slot_candidates_by_wall_value", {})

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

    stream_code_map: dict[int, int] = {}
    if args.stream_code_map_file and args.stream_code_map_file.exists():
        raw = json.loads(args.stream_code_map_file.read_text())
        if isinstance(raw, dict):
            for k, v in raw.items():
                try:
                    stream_code_map[int(k, 0)] = int(v, 0)
                except Exception:
                    pass

    offset_map = {1: 0x24, 2: 0x00, 3: 0x48}
    slot_order = mod.slot_keys_depth_triplets()
    for wv in (1, 2, 3):
        wcodes = mod.extract_map_stream_at_offset(db, args.map_id, offset_map[wv])
        sets = mod.stream_sets_from_codes(wcodes)
        if not sets:
            sets = mod.stream_sets_from_codes(mod.extract_primary_map_stream(db, args.map_id))
        if not sets:
            continue
        codes12 = sets[0]
        for i, slot_key in enumerate(slot_order):
            if i >= len(codes12):
                break
            code = codes12[i]
            owner = stream_code_map.get(code)
            if owner is None:
                owner = mod.decode_stream_code_to_owner(code, args.stream_high_mode)
            if owner is not None:
                pick_by_val[wv][slot_key] = owner

    pygame.init()
    view_w, view_h = 176, 112
    w, h = view_w * args.scale, view_h * args.scale + 36
    screen = pygame.display.set_mode((w, h))
    pygame.display.set_caption(f"MAZEDATA 3D viewer map {args.map_id}")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                elif ev.key in (pygame.K_LEFT, pygame.K_a):
                    facing = {"N": "W", "W": "S", "S": "E", "E": "N"}[facing]
                elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                    facing = {"N": "E", "E": "S", "S": "W", "W": "N"}[facing]
                elif ev.key in (pygame.K_UP, pygame.K_w):
                    wx, wy = try_step(mod, edges, wx, wy, facing, True)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    wx, wy = try_step(mod, edges, wx, wy, facing, False)

        img = render_view(mod, edges, owner_img, slots_generic, pick_by_val, wx, wy, facing)
        surf = pil_to_surface(img)
        surf = pygame.transform.scale(surf, (view_w * args.scale, view_h * args.scale))

        screen.fill((8, 10, 16))
        screen.blit(surf, (0, 0))
        txt = f"map={args.map_id} pos=({wx},{wy}) facing={facing} mode={args.stream_high_mode}"
        screen.blit(font.render(txt, True, (220, 220, 220)), (8, view_h * args.scale + 8))
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
