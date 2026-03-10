from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from bane.data.sprite_decoder import decode_mazedata_tiles
from PIL import Image


MAP_HEADER_SIZE = 0x019E
MAP_RECORD_SIZE = 0x0C0E
_WROOT_0882_BOOTSTRAP_CACHE: dict[str, dict[str, Any] | None] = {}
_TYPE_METADATA_13A_CACHE: dict[tuple[str, int], bytes | None] = {}


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
            return (b >> 4) & 0x0F if (idx & 1) else (b & 0x0F)
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


def wall_between(edges, wx: int, wy: int, dx: int, dy: int) -> int:
    if dx == 0 and dy == -1:
        return int(edges.get(("h", wx, wy), 0))
    if dx == 0 and dy == 1:
        return int(edges.get(("h", wx, wy + 1), 0))
    if dx == -1 and dy == 0:
        return int(edges.get(("v", wx, wy), 0))
    if dx == 1 and dy == 0:
        return int(edges.get(("v", wx + 1, wy), 0))
    return 0


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text())
    return obj if isinstance(obj, dict) else {}


def _load_wroot_0882_bootstrap(gamedata_dir: Path | None = None) -> dict[str, Any] | None:
    gd = (gamedata_dir or Path("gamedata")).resolve()
    key = str(gd)
    if key in _WROOT_0882_BOOTSTRAP_CACHE:
        return _WROOT_0882_BOOTSTRAP_CACHE[key]
    try:
        master = (gd / "MASTER.HDR").read_bytes()
        disk = (gd / "DISK.HDR").read_bytes()
        scen = (gd / "SCENARIO.DBS").read_bytes()
        if len(master) < 0x42 or len(disk) < 0x2BC:
            _WROOT_0882_BOOTSTRAP_CACHE[key] = None
            return None
        record_sizes = [int.from_bytes(master[i * 2 : i * 2 + 2], "little") for i in range(16)]
        flags = list(master[0x38 : 0x38 + 16])
        # DISK.HDR is loaded to 0x3044; offset table starts at shared 0x3048 => disk + 4.
        base_offsets = [int.from_bytes(disk[4 + i * 4 : 8 + i * 4], "little") for i in range(16)]
        st: dict[str, Any] = {
            "record_sizes": record_sizes,
            "flags": flags,
            "base_offsets": base_offsets,
            "scenario_dbs": scen,
        }
        _WROOT_0882_BOOTSTRAP_CACHE[key] = st
        return st
    except Exception:
        _WROOT_0882_BOOTSTRAP_CACHE[key] = None
        return None


def _load_type_metadata_record_13a(type_index: int, gamedata_dir: Path | None = None) -> bytes | None:
    gd = (gamedata_dir or Path("gamedata")).resolve()
    t = int(type_index) & 0xFF
    ck = (str(gd), t)
    if ck in _TYPE_METADATA_13A_CACHE:
        return _TYPE_METADATA_13A_CACHE[ck]
    st = _load_wroot_0882_bootstrap(gamedata_dir=gd)
    if not isinstance(st, dict):
        _TYPE_METADATA_13A_CACHE[ck] = None
        return None
    try:
        opcode = 8
        record_sizes = st.get("record_sizes", [])
        flags = st.get("flags", [])
        base_offsets = st.get("base_offsets", [])
        scen = st.get("scenario_dbs", b"")
        if not isinstance(scen, (bytes, bytearray)):
            _TYPE_METADATA_13A_CACHE[ck] = None
            return None
        if not (0 <= opcode < len(record_sizes) and 0 <= opcode < len(flags) and 0 <= opcode < len(base_offsets)):
            _TYPE_METADATA_13A_CACHE[ck] = None
            return None
        rec_size = int(record_sizes[opcode]) & 0xFFFF
        if rec_size < 0x13A:
            _TYPE_METADATA_13A_CACHE[ck] = None
            return None
        if int(flags[opcode]) != 0:
            _TYPE_METADATA_13A_CACHE[ck] = None
            return None
        off = int(base_offsets[opcode]) + (t * rec_size)
        if off < 0 or off + rec_size > len(scen):
            _TYPE_METADATA_13A_CACHE[ck] = None
            return None
        rec = bytes(scen[off : off + rec_size][:0x13A])
        _TYPE_METADATA_13A_CACHE[ck] = rec
        return rec
    except Exception:
        _TYPE_METADATA_13A_CACHE[ck] = None
        return None


@dataclass
class RuntimeInitState:
    startup_overlay_order: list[str]
    wmaze_overlay_init: dict[str, Any]
    wmaze_zero_state: dict[str, Any]
    winit_graphics_calls: list[dict[str, Any]]
    shared_viewport_rect_4fbc: dict[str, Any]
    bootstrap_tables: dict[str, Any]

    @classmethod
    def from_artifacts(cls, scratch_dir: Path) -> "RuntimeInitState":
        req = load_json(scratch_dir / "render_runtime_init_requirements.json")
        return cls(
            startup_overlay_order=[str(v) for v in req.get("startup_overlay_order", [])],
            wmaze_overlay_init=dict(req.get("wmaze_overlay_init", {})),
            wmaze_zero_state=dict(req.get("wmaze_zero_state", {})),
            winit_graphics_calls=[dict(v) for v in req.get("winit_graphics_calls", []) if isinstance(v, dict)],
            shared_viewport_rect_4fbc=dict(req.get("shared_viewport_rect_4fbc", {})),
            bootstrap_tables=dict(req.get("wroot_0882_bootstrap", {})),
        )


@dataclass
class VisibleSlot:
    orient: str
    depth: int
    wall_value: int
    block: int | None
    row: int | None
    col: int | None
    channel4: int | None
    channel2: int | None


@dataclass
class SceneState:
    map_id: int
    wx: int
    wy: int
    facing: str
    origins: list[tuple[int, int]]
    visible_slots: list[VisibleSlot] = field(default_factory=list)


@dataclass
class PassTemplate:
    pass_index: int
    draw_target: str
    cleanup_target: str | None
    gate_flag_addr: str | None
    arg_bp4_source: str
    arg_bp6_source: str
    class_state_word_addr: str | None
    slot_hint: str | None
    immediate_by_bp_offset: dict[str, int] = field(default_factory=dict)
    helper_mode_family: str = "non_helper_or_unresolved"
    classifier_family: str | None = None
    draw_index_map_family: str | None = None


@dataclass
class PassStateRow:
    depth: int
    pass_index: int
    draw_target: str
    cleanup_target: str | None
    gate_flag_addr: str | None
    gate_initial_value: int | None
    gate_predicted_enabled: bool | None
    arg_bp4_value: int
    class_state_word_addr: str | None
    class_state_initial_value: int | None
    predicted_class_state_value: int | None
    predicted_class_code: int | None
    predicted_draw_index: int | None
    slot_hint: str | None
    visible_slot: VisibleSlot | None
    helper_mode_family: str
    classifier_family: str | None
    draw_index_map_family: str | None
    possible_draw_indices: list[int] = field(default_factory=list)
    direct_36ac_draw_indices: list[int] = field(default_factory=list)
    queue_84f1_draw_indices: list[int] = field(default_factory=list)
    no_output_draw_indices: list[int] = field(default_factory=list)
    predicted_output_mode: str | None = None
    predicted_helper_events: list[dict[str, Any]] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


@dataclass
class Stage1PassState:
    pass_templates: list[PassTemplate] = field(default_factory=list)
    initial_gate_state: dict[str, int] = field(default_factory=dict)
    predicted_class_state_by_depth: dict[str, dict[str, int | None]] = field(default_factory=dict)
    predicted_gate_state_by_depth: dict[str, dict[str, bool]] = field(default_factory=dict)
    helper_mode_summary: dict[str, Any] = field(default_factory=dict)
    predicted_output_mode_counts: dict[str, int] = field(default_factory=dict)
    class_code_maps: dict[str, dict[str, int]] = field(default_factory=dict)
    classifier_tables: dict[str, dict[str, int | None]] = field(default_factory=dict)
    pass_rows: list[PassStateRow] = field(default_factory=list)


@dataclass
class Stage2HelperEmission:
    predicted_helper_event_counts: dict[str, int] = field(default_factory=dict)
    immediate_direct_36ac_events: list[dict[str, Any]] = field(default_factory=list)
    deferred_queue_emission_events: list[dict[str, Any]] = field(default_factory=list)
    runtime_dependencies: list[str] = field(default_factory=list)


@dataclass
class Stage3QueueState:
    predicted_queue_entries: list[dict[str, Any]] = field(default_factory=list)
    predicted_queue_consumer_events: list[dict[str, Any]] = field(default_factory=list)
    unresolved_runtime_dependencies: list[str] = field(default_factory=list)


@dataclass
class Stage4PrePresent:
    pre_present_draw_events: list[dict[str, Any]] = field(default_factory=list)
    event_counts: dict[str, int] = field(default_factory=dict)
    unresolved_runtime_dependencies: list[str] = field(default_factory=list)
    final_present_stage: dict[str, Any] = field(default_factory=dict)


@dataclass
class Stage5PresentContract:
    wrapper_target: str
    driver_target: str
    viewport_rect_4fbc: dict[str, Any]
    consumed_pre_present_event_count: int
    shadow_buffer_ops: list[dict[str, Any]] = field(default_factory=list)
    shadow_buffer_op_counts: dict[str, int] = field(default_factory=dict)
    required_inputs: list[str] = field(default_factory=list)
    unresolved_runtime_dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ShadowBufferSchema:
    width_px: int
    height_px: int
    plane_count: int
    viewport_rect_px: dict[str, int]
    op_kinds: list[str] = field(default_factory=list)
    pixel_format_note: str = ""


@dataclass
class Stage5ShadowBufferTarget:
    schema: ShadowBufferSchema
    planned_ops: list[dict[str, Any]] = field(default_factory=list)
    planned_op_counts: dict[str, int] = field(default_factory=dict)
    unresolved_runtime_dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class ShadowBufferReplayResult:
    width_px: int
    height_px: int
    plane_count: int
    shadow_state: dict[str, Any] = field(default_factory=dict)
    executed_op_counts: dict[str, int] = field(default_factory=dict)
    execution_log: list[dict[str, Any]] = field(default_factory=list)
    unresolved_runtime_dependencies: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class StageOutputs:
    runtime_init: RuntimeInitState
    scene: SceneState
    stage1_pass_state: Stage1PassState
    stage2_helper_emission: Stage2HelperEmission
    stage3_queue_state: Stage3QueueState
    stage4_pre_present: Stage4PrePresent
    stage5_present_contract: Stage5PresentContract
    stage5_shadow_buffer_target: Stage5ShadowBufferTarget
    stage5_shadow_buffer_replay: ShadowBufferReplayResult
    notes: list[str] = field(default_factory=list)


FACING_VECS = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}

ARG_BP6_CLASS_STATE_ADDRS = {
    "class_index_var_0x5220": "0x5220",
    "class_index_var_0x5222": "0x5222",
    "class_index_var_0x5224": "0x5224",
    "class_index_var_0x5226": "0x5226",
    "class_index_var_0x5228": "0x5228",
}

CLASS_STATE_SLOT_HINTS = {
    "0x5220": "center",
    "0x5222": "left",
    "0x5224": "right",
    "0x5226": "left",
    "0x5228": "right",
}

TOP_GATE_KEYS = ("5072", "507a", "5082", "508a", "5092", "509a", "50a2")


def build_scene_state(*, gamedata: Path, map_id: int, wx: int, wy: int, facing: str) -> SceneState:
    db = (gamedata / "NEWGAME.DBS").read_bytes()
    base = record_base(map_id)
    a_vals, b_vals = decode_wall_planes(db, base)
    c4_vals = decode_packed_plane(db, base, 0x1F8, 4)
    c2_vals = decode_packed_plane(db, base, 0x378, 2)
    origins = decode_origins(db, base)
    edges = collect_world_edge_values(a_vals, b_vals, origins, map_id)

    fdx, fdy = FACING_VECS[facing]
    ldx, ldy = -fdy, fdx
    rdx, rdy = fdy, -fdx

    visible_slots: list[VisibleSlot] = []
    for depth in range(1, 5):
        base_x = wx + fdx * (depth - 1)
        base_y = wy + fdy * (depth - 1)
        fw = wall_between(edges, base_x, base_y, fdx, fdy)
        lw = wall_between(edges, base_x, base_y, ldx, ldy)
        rw = wall_between(edges, base_x, base_y, rdx, rdy)
        slot_defs = [
            ("center", base_x, base_y, fw),
            ("left", base_x + ldx, base_y + ldy, lw),
            ("right", base_x + rdx, base_y + rdy, rw),
        ]
        for orient, sx, sy, wv in slot_defs:
            block = row = col = None
            c4 = c2 = None
            res = resolve_world_cell(origins, sx, sy)
            if res is not None:
                block, row, col = res
                c4 = int(c4_vals[block][row][col])
                c2 = int(c2_vals[block][row][col])
            visible_slots.append(
                VisibleSlot(
                    orient=orient,
                    depth=depth,
                    wall_value=int(wv),
                    block=block,
                    row=row,
                    col=col,
                    channel4=c4,
                    channel2=c2,
                )
            )
    return SceneState(
        map_id=int(map_id),
        wx=int(wx),
        wy=int(wy),
        facing=str(facing),
        origins=[(int(x), int(y)) for (x, y) in origins],
        visible_slots=visible_slots,
    )


def parse_zero_state_word(state: dict[str, Any], addr: str) -> int | None:
    entry = state.get(addr)
    if not isinstance(entry, dict):
        return None
    word = entry.get("word")
    if not isinstance(word, str):
        return None
    return int(word, 16)


def build_classifier_tables(scratch_dir: Path) -> dict[str, dict[str, int | None]]:
    raw = load_json(scratch_dir / "wmaze_classifier_class_maps.json")
    tables: dict[str, dict[str, int | None]] = {}
    for table in raw.get("tables", []):
        if not isinstance(table, dict):
            continue
        name = str(table.get("name", ""))
        mapping: dict[str, int | None] = {}
        for entry in table.get("entries", []):
            if not isinstance(entry, dict):
                continue
            idx = entry.get("index")
            if not isinstance(idx, int):
                continue
            class_code = entry.get("class_code")
            mapping[str(idx)] = int(class_code, 16) if isinstance(class_code, str) else None
        if name:
            tables[name] = mapping
    return tables


def facing_to_index(facing: str) -> int:
    return {"N": 0, "E": 1, "S": 2, "W": 3}.get(facing, 0)


def emulate_classifier_index(c4: int, c2: int, facing_idx: int, variant: str, seed_idx: int) -> int:
    if variant == "A":
        rem = (int(c2) + 1) % 4
    else:
        rem = (int(c2) + 3) % 4
    return int(c4) if rem == int(facing_idx) else int(seed_idx)


def emulate_7d8c_tail_switch(c4: int, base_idx: int, c2: int, facing_idx: int) -> int:
    c4 = int(c4)
    c2 = int(c2)
    idx = int(base_idx)
    if not (c2 == int(facing_idx) or c4 == 6 or c4 > 12):
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


def load_classifier_index_policy(scratch_dir: Path, map_id: int) -> dict[int, dict[str, int | str]]:
    raw = load_json(scratch_dir / "map_owner_streams" / "inferred_classifier_index_policy.json")
    out: dict[int, dict[str, int | str]] = {}
    maps = raw.get("maps", {})
    if isinstance(maps, dict):
        per_map = maps.get(str(map_id), {})
        if isinstance(per_map, dict):
            pol = per_map.get("classifier_index_policy", {})
            if isinstance(pol, dict):
                for k, v in pol.items():
                    try:
                        wallv = int(k)
                    except Exception:
                        continue
                    if isinstance(v, dict):
                        out[wallv] = {
                            "variant": str(v.get("variant", "A")).upper(),
                            "seed_index": int(v.get("seed_index", 0)),
                        }
    if not out:
        gpol = raw.get("global_best_policy_by_wall", {})
        if isinstance(gpol, dict):
            for k, v in gpol.items():
                try:
                    wallv = int(k)
                except Exception:
                    continue
                if isinstance(v, dict):
                    out[wallv] = {
                        "variant": str(v.get("variant", "A")).upper(),
                        "seed_index": int(v.get("seed_index", 0)),
                    }
    return out


def helper_mode_family_for_pass(draw_target: str, helper_modes: dict[str, Any]) -> str:
    summary = helper_modes.get("summary", {})
    if draw_target == "0x85D0":
        pair = summary.get("85D0.class_draw_switch", {})
        if pair.get("direct_36ac_only") and pair.get("queue_84f1_only"):
            return "mixed_direct_36ac_or_queue_84f1"
    if draw_target == "0x8B18":
        pair = summary.get("8B18.class_draw_switch", {})
        if pair.get("direct_36ac_only") and pair.get("queue_84f1_only"):
            return "mixed_direct_36ac_or_queue_84f1"
    if draw_target == "0x8D07":
        return "immediate_non_helper_dispatch"
    return "non_helper_or_unresolved"


def classifier_family_for_target(draw_target: str) -> str | None:
    if draw_target == "0x85D0":
        return "8175.class_map_switch"
    if draw_target == "0x8B18":
        return "8332.class_map_switch"
    return None


def draw_index_map_family_for_target(draw_target: str) -> str | None:
    if draw_target == "0x85D0":
        return "A_8175_to_85D0"
    if draw_target == "0x8B18":
        return "B_8332_to_8B18"
    return None


def find_visible_slot(scene: SceneState, *, depth: int, orient: str | None) -> VisibleSlot | None:
    if orient is None:
        return None
    for slot in scene.visible_slots:
        if slot.depth == depth and slot.orient == orient:
            return slot
    return None


def scene_render_depth_limit(scene: SceneState) -> int:
    centers = sorted(
        (slot for slot in scene.visible_slots if slot.orient == "center"),
        key=lambda slot: int(slot.depth),
    )
    for slot in centers:
        if int(slot.wall_value) != 0:
            return int(slot.depth)
    return 4


def should_apply_7d8c_topflag(*, map_id: int, slot: VisibleSlot | None) -> bool:
    if slot is None or slot.channel4 is None:
        return False
    c4 = int(slot.channel4)
    # c4==0 was previously grouped into the 7E54 family, but that suppresses the
    # only visible center-wall pass on the live start scene. Keep the stricter set
    # until the 7F2C jump-table decode for zero is proven.
    if c4 not in (4, 5, 12):
        return False
    if int(map_id) == 0x0C and slot.block is not None and int(slot.block) < 9:
        return False
    return True


def init_depth_gate_state() -> dict[str, bool]:
    return {k: True for k in TOP_GATE_KEYS}


def apply_topflag_sideeffects_for_depth(*, map_id: int, center: VisibleSlot | None, left: VisibleSlot | None, right: VisibleSlot | None) -> dict[str, bool]:
    gates = init_depth_gate_state()
    if should_apply_7d8c_topflag(map_id=map_id, slot=left):
        gates["5072"] = False
        gates["507a"] = False
        gates["5082"] = False
    if should_apply_7d8c_topflag(map_id=map_id, slot=center):
        gates["508a"] = False
    if should_apply_7d8c_topflag(map_id=map_id, slot=right):
        gates["5092"] = False
        gates["509a"] = False
        gates["50a2"] = False
    return gates


def pass_gate_key(pass_index: int) -> str | None:
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


def marker_key_for_slot(slot_hint: str | None) -> str | None:
    if slot_hint == "left":
        return "5066"
    if slot_hint == "center":
        return "5067"
    if slot_hint == "right":
        return "5068"
    return None


def cleanup_pred_8df6_family(marker_set: set[str], class_idx: int, marker_key: str | None) -> bool:
    ci = int(class_idx)
    if ci == 2 or ci >= 5:
        return True
    return marker_key in marker_set if marker_key is not None else False


def apply_cleanup_to_gate_state(gates: dict[str, bool], cleanup_target: str | None, class_idx: int | None, slot_hint: str | None, marker_set: set[str]) -> None:
    if cleanup_target is None or class_idx is None:
        return
    ct = str(cleanup_target)
    ci = int(class_idx)
    mk = marker_key_for_slot(slot_hint)
    center_marker = "5067" in marker_set
    if ct == "0x8E59":
        if ci != 0 or center_marker:
            gates["507a"] = False
    elif ct == "0x8E8A":
        if ci != 0 or center_marker:
            gates["5092"] = False
    elif ct == "0x8DF6":
        if cleanup_pred_8df6_family(marker_set, ci, "5067"):
            pass
    elif ct == "0x8EBB":
        if cleanup_pred_8df6_family(marker_set, ci, "5066"):
            pass
    elif ct == "0x8EE8":
        if cleanup_pred_8df6_family(marker_set, ci, "5066"):
            pass
    elif ct == "0x8F1A":
        if cleanup_pred_8df6_family(marker_set, ci, "5068"):
            pass
    elif ct == "0x8F4C":
        if cleanup_pred_8df6_family(marker_set, ci, "5068"):
            pass


def helper_table_name_for_target(draw_target: str) -> str | None:
    if draw_target == "0x85D0":
        return "85D0.class_draw_switch"
    if draw_target == "0x8B18":
        return "8B18.class_draw_switch"
    return None


def bp_offset_key(offset: int) -> str:
    return f"0x{int(offset):02X}"


def resolve_helper_arg_value(arg: dict[str, Any], template: PassTemplate, depth: int) -> dict[str, Any]:
    if not isinstance(arg, dict):
        return {"kind": "unknown"}
    resolved = arg.get("resolved")
    if isinstance(resolved, dict):
        source_kind = resolved.get("source_kind")
        if source_kind == "imm":
            return {"kind": "imm", "value": int(resolved.get("value", 0))}
        if source_kind == "bp_offset":
            bp_offset = int(resolved.get("bp_offset", 0))
            return {
                "kind": "bp_immediate",
                "bp_offset": bp_offset,
                "value": template.immediate_by_bp_offset.get(bp_offset_key(bp_offset)),
            }
        if source_kind == "expr":
            source_text = str(resolved.get("source_text", ""))
            if source_text == "word ptr [bp + 4]":
                return {"kind": "depth_index", "value": int(depth)}
            return {"kind": "expr", "expr": source_text}
    kind = arg.get("kind")
    if kind == "bp_offset":
        bp_offset = int(arg.get("bp_offset", 0))
        return {
            "kind": "bp_immediate",
            "bp_offset": bp_offset,
            "value": template.immediate_by_bp_offset.get(bp_offset_key(bp_offset)),
        }
    text = str(arg.get("text", ""))
    if text == "word ptr [bp + 4]":
        return {"kind": "depth_index", "value": int(depth)}
    return {"kind": "expr", "expr": text}


def build_helper_call_tables(scratch_dir: Path) -> tuple[dict[str, dict[int, list[dict[str, Any]]]], dict[str, dict[int, list[dict[str, Any]]]]]:
    direct_doc = load_json(scratch_dir / "wmaze_helper_draw_calls.json")
    queue_doc = load_json(scratch_dir / "wmaze_84f1_handler_calls.json")
    direct_tables: dict[str, dict[int, list[dict[str, Any]]]] = {}
    queue_tables: dict[str, dict[int, list[dict[str, Any]]]] = {}

    for table_name, rows in dict(direct_doc.get("tables", {})).items():
        if not isinstance(rows, list):
            continue
        by_index: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            idx = row.get("index")
            if not isinstance(idx, int):
                continue
            by_index[idx] = [dict(v) for v in row.get("calls_36ac", []) if isinstance(v, dict)]
        direct_tables[str(table_name)] = by_index

    for table_name, rows in dict(queue_doc.get("tables", {})).items():
        if not isinstance(rows, list):
            continue
        by_index = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            idx = row.get("index")
            if not isinstance(idx, int):
                continue
            by_index[idx] = [dict(v) for v in row.get("calls_84f1", []) if isinstance(v, dict)]
        queue_tables[str(table_name)] = by_index

    return direct_tables, queue_tables


def build_predicted_helper_events(row: PassStateRow, template: PassTemplate, direct_tables: dict[str, dict[int, list[dict[str, Any]]]], queue_tables: dict[str, dict[int, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if row.draw_target == "0x8D07" and row.predicted_output_mode == "immediate_non_helper_dispatch":
        # Disassembly-grounded note:
        # WMAZE:0x8C23..0x8D11 calls WROOT:0x35C8, and WROOT:0x35B4..0x3618
        # is a string-scan helper (repne scasb), not a graphics wrapper.
        # Therefore this dispatch path is modeled as immediate non-draw logic.
        return out
    table_name = helper_table_name_for_target(row.draw_target)
    idx = row.predicted_draw_index
    if table_name is None or idx is None:
        return out
    if row.predicted_output_mode == "direct_36ac":
        for call in direct_tables.get(table_name, {}).get(int(idx), []):
            args = [resolve_helper_arg_value(arg, template, row.depth) for arg in call.get("args_callee_order", [])]
            call_addr = str(call.get("call_addr"))
            if (
                row.draw_target == "0x85D0"
                and row.slot_hint == "right"
                and int(row.pass_index) in (6, 7)
                and int(idx) == 2
                and call_addr in ("0x8A8E", "0x8B0E")
            ):
                depth_index = max(0, int(row.depth) - 1)
                if depth_index:
                    adjusted_args: list[dict[str, Any]] = []
                    for arg in args:
                        if (
                            isinstance(arg, dict)
                            and str(arg.get("kind")) == "bp_immediate"
                            and int(arg.get("bp_offset", -1)) in (0x42, 0x46)
                            and isinstance(arg.get("value"), int)
                        ):
                            adj = dict(arg)
                            adj["value"] = int(adj["value"]) + depth_index
                            adjusted_args.append(adj)
                        else:
                            adjusted_args.append(arg)
                    args = adjusted_args
            out.append(
                {
                    "event_kind": "direct_36ac",
                    "call_addr": call_addr,
                    "draw_index": int(idx),
                    "args": args,
                    "runtime_dependencies": unique_preserve_order(extract_runtime_dependencies(args)),
                }
            )
    elif row.predicted_output_mode == "queue_84f1":
        bp8_imm = template.immediate_by_bp_offset.get("0x08")
        depth_index = max(0, int(row.depth) - 1)
        for call in queue_tables.get(table_name, {}).get(int(idx), []):
            call_addr = str(call.get("call_addr"))
            # Disassembly-grounded gating for WMAZE 0x8665 handler family (draw_index 1 on 0x85D0):
            # - 0x869A only fires when bp+8 == 1 and bp+4 == 0 and [0x363E] > 0
            # - 0x86CA fires on the bp+8 == 1 path when (bp+4 > 0) or [0x363E] == 0
            # - 0x86F3 fires only on the bp+8 != 1 path and bp+4 > 0
            if row.draw_target == "0x85D0" and int(idx) == 1:
                if call_addr == "0x869A":
                    if not (int(depth_index) == 0 and int(bp8_imm or 0) == 1):
                        continue
                elif call_addr == "0x86CA":
                    if int(bp8_imm or 0) != 1:
                        continue
                elif call_addr == "0x86F3":
                    if int(bp8_imm or 0) == 1 or int(depth_index) <= 0:
                        continue
            args = [resolve_helper_arg_value(arg, template, row.depth) for arg in call.get("args_callee_order", [])]
            out.append(
                {
                    "event_kind": "queue_84f1",
                    "call_addr": call_addr,
                    "draw_index": int(idx),
                    "args": args,
                    "runtime_dependencies": unique_preserve_order(extract_runtime_dependencies(args)),
                }
            )
    return out


def _scalar_or_expr(arg: dict[str, Any]) -> Any:
    kind = str(arg.get("kind", ""))
    if kind in ("imm", "bp_immediate", "depth_index"):
        return arg.get("value")
    if kind == "expr":
        return {"expr": arg.get("expr")}
    return {"kind": kind}


def extract_runtime_dependencies(value: Any) -> list[str]:
    deps: list[str] = []
    if isinstance(value, dict):
        expr = value.get("expr")
        if isinstance(expr, str):
            deps.append(expr)
        for v in value.values():
            deps.extend(extract_runtime_dependencies(v))
    elif isinstance(value, list):
        for item in value:
            deps.extend(extract_runtime_dependencies(item))
    return deps


def unique_preserve_order(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def signed16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def clamp_int(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(v)))


def bbox_nonzero_rgba(img: Image.Image) -> dict[str, int] | None:
    px = img.load()
    min_x = img.width
    min_y = img.height
    max_x = -1
    max_y = -1
    count = 0
    for y in range(img.height):
        for x in range(img.width):
            if px[x, y][3] == 0:
                continue
            count += 1
            if x < min_x:
                min_x = x
            if y < min_y:
                min_y = y
            if x > max_x:
                max_x = x
            if y > max_y:
                max_y = y
    if count == 0:
        return None
    return {
        "x0": int(min_x),
        "y0": int(min_y),
        "x1": int(max_x),
        "y1": int(max_y),
        "w": int(max_x - min_x + 1),
        "h": int(max_y - min_y + 1),
        "pixels": int(count),
    }


def emulate_36a0_grid_state_from_rect(rect_px: dict[str, Any]) -> dict[str, int]:
    cx = int(rect_px.get("x_px", 0))
    dx = int(rect_px.get("y_px", 0))
    row_block = max(0, dx >> 3)
    # 36A0 screen offsets are addressed in bytes (8 px columns), not 16 px cells.
    col_block = max(0, cx >> 3)
    cell_base = row_block * 0x28 + col_block
    screen_base = row_block * 0x140 + col_block
    return {
        "rect_x_px": cx,
        "rect_y_px": dx,
        "row_block_8px": int(row_block),
        "col_block_16px": int(col_block),
        "state_117e": int(cx),
        "state_1180": int(dx),
        "state_11ad": int((0x19 - row_block) & 0xFF),
        "state_11ac": int((0x28 - col_block) & 0xFF),
        "state_1194_base": int(cell_base),
        "state_1194_triplet": [int(cell_base), int(cell_base + 1), int(cell_base + 2)],
        "state_11c0_base": int(screen_base),
        "state_11c0_triplet": [int(screen_base), int(screen_base + 1), int(screen_base + 2)],
    }


def emulate_36a0_marked_cells(prev_11aa: int, prev_11ab: int, base: int) -> list[int]:
    rows: list[int] = [0]
    if int(prev_11ab) != 1:
        rows.append(0x28)
    if int(prev_11ab) != 2:
        rows.append(0x50)
    cols: list[int] = [0]
    if int(prev_11aa) != 1:
        cols.append(1)
    if int(prev_11aa) != 2:
        cols.append(2)
    out: list[int] = []
    for roff in rows:
        for coff in cols:
            out.append(int(base + roff + coff))
    return out


def emulate_36a0_helper_copy_count(cur_11ac: int, cur_11ad: int) -> int:
    return len(emulate_36a0_overlay_call_plan(0, cur_11ac, cur_11ad))


def emulate_36a0_helper_copy_plan(prev_cell_base: int, cur_screen_base: int, marked_cells: list[int]) -> list[dict[str, Any]]:
    marked = {int(v) for v in marked_cells}
    plan: list[dict[str, Any]] = []
    for row in range(3):
        for col in range(3):
            cell_idx = int(prev_cell_base + row * 0x28 + col)
            dst_off = int(cur_screen_base + row * 0x140 + col)
            plan.append(
                {
                    "row": int(row),
                    "col": int(col),
                    "cell_index": cell_idx,
                    "dst_screen_off": dst_off,
                    "path": "tile_from_11a6" if cell_idx in marked else "copy_from_a000",
                }
            )
    return plan


def emulate_36a0_overlay_call_plan(cur_screen_base: int, cur_11ac: int, cur_11ad: int) -> list[dict[str, int]]:
    di = int(cur_screen_base)
    si = 0x1412
    out: list[dict[str, int]] = []

    def emit(row: int, col: int) -> None:
        nonlocal si
        out.append(
            {
                "row": int(row),
                "col": int(col),
                "dst_screen_off": int(di),
                "src_pattern_off": int(si),
            }
        )
        si += 0x08

    emit(0, 0)
    if int(cur_11ac) == 1:
        di += 0x140
        si += 0x10
    else:
        di += 1
        emit(0, 1)
        if int(cur_11ac) == 2:
            di += 0x13F
            si += 0x08
        else:
            di += 1
            emit(0, 2)
            di += 0x13E

    if int(cur_11ad) != 1:
        emit(1, 0)
        if int(cur_11ac) == 1:
            di += 0x140
            si += 0x10
        else:
            di += 1
            emit(1, 1)
            if int(cur_11ac) == 2:
                di += 0x13F
                si += 0x08
            else:
                di += 1
                emit(1, 2)
                di += 0x13E

    if int(cur_11ad) != 2:
        emit(2, 0)
        if int(cur_11ac) != 1:
            di += 1
            emit(2, 1)
            if int(cur_11ac) != 2:
                di += 1
                emit(2, 2)

    return out


EGA_DEFAULT_RGBA = [
    (0, 0, 0, 0),
    (0, 0, 170, 255),
    (0, 170, 0, 255),
    (0, 170, 170, 255),
    (170, 0, 0, 255),
    (170, 0, 170, 255),
    (170, 85, 0, 255),
    (170, 170, 170, 255),
    (85, 85, 85, 255),
    (85, 85, 255, 255),
    (85, 255, 85, 255),
    (85, 255, 255, 255),
    (255, 85, 85, 255),
    (255, 85, 255, 255),
    (255, 255, 85, 255),
    (255, 255, 255, 255),
]
EGA_RGBA_TO_INDEX = {tuple(c): i for i, c in enumerate(EGA_DEFAULT_RGBA)}


def _load_ega_drv_raw(gamedata: Path | None) -> bytes | None:
    if gamedata is None:
        return None
    path = Path(gamedata) / "EGA.DRV"
    if not path.exists():
        return None
    try:
        return path.read_bytes()
    except Exception:
        return None


def emulate_36a0_runtime_pattern_buffers(rect_px: dict[str, Any], ega_raw: bytes) -> dict[str, bytearray]:
    cx = int(rect_px.get("x_px", 0))
    dx = int(rect_px.get("y_px", 0))
    shift = (cx >> 1) & 0x07
    dy = dx & 0x07
    src_a = 0x169A - 0x100
    src_b = 0x171A - 0x100
    buf_1532 = bytearray(0x120)
    buf_1652 = bytearray(0x48)
    buf_1412 = bytearray(0x120)

    def op_1bf2(src_off: int, dst_off: int, dl: int) -> tuple[int, int]:
        si = int(src_off)
        di = int(dst_off)
        count = int(dl) & 0xFF
        while count > 0:
            ax = int.from_bytes(ega_raw[si : si + 2], "little")
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di] = (ax >> 8) & 0xFF
            buf_1532[di + 0x08] = ax & 0xFF

            ax = int.from_bytes(ega_raw[si + 0x20 : si + 0x22], "little")
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0x48] = (ax >> 8) & 0xFF
            buf_1532[di + 0x50] = ax & 0xFF

            ax = int.from_bytes(ega_raw[si + 0x40 : si + 0x42], "little")
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0x90] = (ax >> 8) & 0xFF
            buf_1532[di + 0x98] = ax & 0xFF

            ax = int.from_bytes(ega_raw[si + 0x60 : si + 0x62], "little")
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0xD8] = (ax >> 8) & 0xFF
            buf_1532[di + 0xE0] = ax & 0xFF

            ax = (ega_raw[si] << 8) & 0xFF00
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0x10] = ax & 0xFF
            ax = (ega_raw[si + 0x20] << 8) & 0xFF00
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0x58] = ax & 0xFF
            ax = (ega_raw[si + 0x40] << 8) & 0xFF00
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0xA0] = ax & 0xFF
            ax = (ega_raw[si + 0x60] << 8) & 0xFF00
            ax = (ax >> shift) & 0xFFFF
            buf_1532[di + 0xE8] = ax & 0xFF
            si += 2
            di += 1
            count -= 1
        return si, di

    def op_1c4e(src_off: int, dst_off: int, dl: int) -> tuple[int, int]:
        si = int(src_off)
        di = int(dst_off)
        count = int(dl) & 0xFF
        while count > 0:
            ax = int.from_bytes(ega_raw[si : si + 2], "little")
            ax = (ax >> shift) & 0xFFFF
            buf_1652[di] = (ax >> 8) & 0xFF
            buf_1652[di + 0x08] = ax & 0xFF
            ax = (ega_raw[si] << 8) & 0xFF00
            ax = (ax >> shift) & 0xFFFF
            buf_1652[di + 0x10] = ax & 0xFF
            si += 2
            di += 1
            count -= 1
        return si, di

    di = dy
    dh = dy
    dl = 8 - dh
    _, di = op_1bf2(src_a, di, dl)
    dl = 8
    di += 0x10
    _, di = op_1bf2(src_a, di, dl)
    if dh != 0:
        dl = dh
        di += 0x10
        op_1bf2(src_a, di, dl)

    di = dy
    dh = dy
    dl = 8 - dh
    _, di = op_1c4e(src_b, di, dl)
    dl = 8
    di += 0x10
    _, di = op_1c4e(src_b, di, dl)
    if dh != 0:
        dl = dh
        di += 0x10
        op_1c4e(src_b, di, dl)

    for plane in range(4):
        plane_base = plane * 0x48
        for i in range(0x48):
            al = buf_1532[plane_base + i]
            dl = buf_1652[i]
            dh2 = (~dl) & 0xFF
            buf_1412[plane_base + i] = ((buf_1412[plane_base + i] & dh2) | (al & dl)) & 0xFF
    return {"buf_1532": buf_1532, "buf_1652": buf_1652, "buf_1412": buf_1412}


def emulate_36a0_runtime_pattern_block(rect_px: dict[str, Any], ega_raw: bytes) -> bytearray:
    return emulate_36a0_runtime_pattern_buffers(rect_px, ega_raw)["buf_1412"]


def decode_36a0_overlay_tile_rgba(pattern_block: bytes, src_pattern_off: int) -> Image.Image:
    tile = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    base = int(src_pattern_off) - 0x1412
    px = tile.load()
    for y in range(8):
        plane_bytes = [
            pattern_block[base + y + 0x00],
            pattern_block[base + y + 0x40],
            pattern_block[base + y + 0x80],
            pattern_block[base + y + 0xC0],
        ]
        for x in range(8):
            bit = 7 - x
            idx = (
                (((plane_bytes[0] >> bit) & 1) << 0)
                | (((plane_bytes[1] >> bit) & 1) << 1)
                | (((plane_bytes[2] >> bit) & 1) << 2)
                | (((plane_bytes[3] >> bit) & 1) << 3)
            )
            px[x, y] = EGA_DEFAULT_RGBA[idx]
    return tile


def rgba_hex_to_plane_rows(rgba_hex: str) -> list[list[int]]:
    raw = bytes.fromhex(rgba_hex)
    planes = [[0] * 8 for _ in range(4)]
    for y in range(8):
        for x in range(8):
            off = (y * 8 + x) * 4
            rgba = (raw[off], raw[off + 1], raw[off + 2], raw[off + 3])
            idx = EGA_RGBA_TO_INDEX.get(rgba, 0)
            bit = 7 - x
            for p in range(4):
                if (idx >> p) & 1:
                    planes[p][y] |= (1 << bit)
    return planes


def plane_rows_to_rgba_hex(planes: list[list[int]]) -> str:
    raw = bytearray()
    for y in range(8):
        for x in range(8):
            bit = 7 - x
            idx = (
                (((planes[0][y] >> bit) & 1) << 0)
                | (((planes[1][y] >> bit) & 1) << 1)
                | (((planes[2][y] >> bit) & 1) << 2)
                | (((planes[3][y] >> bit) & 1) << 3)
            )
            raw.extend(EGA_DEFAULT_RGBA[idx])
    return raw.hex()


def merge_tile_with_0a2b_mask(saved_rgba_hex: str, *, pattern_1532: bytearray, mask_1652: bytearray, cx: int) -> str:
    dst = rgba_hex_to_plane_rows(saved_rgba_hex)
    cx = int(cx)
    for row in range(8):
        m = int(mask_1652[cx + row]) & 0xFF
        inv = (~m) & 0xFF
        for p in range(4):
            pat = int(pattern_1532[p * 0x48 + cx + row]) & 0xFF
            dst[p][row] = ((dst[p][row] & inv) | (pat & m)) & 0xFF
    return plane_rows_to_rgba_hex(dst)


def tile_image_to_rgba_hex(tile: Image.Image) -> str:
    tile = tile.convert("RGBA")
    px = tile.load()
    raw = bytearray()
    for y in range(tile.height):
        for x in range(tile.width):
            raw.extend(px[x, y])
    return raw.hex()


def capture_canvas_tile_rgba_hex(canvas: Image.Image, x_px: int, y_px: int) -> str:
    tile = canvas.crop((int(x_px), int(y_px), int(x_px) + 8, int(y_px) + 8)).convert("RGBA")
    return tile_image_to_rgba_hex(tile)


def extract_36a0_overlay_tiles(rect_px: dict[str, Any], overlay_call_plan: list[dict[str, Any]], ega_raw: bytes) -> list[dict[str, Any]]:
    pattern_block = emulate_36a0_runtime_pattern_block(rect_px, ega_raw)
    tiles: list[dict[str, Any]] = []
    for row in overlay_call_plan:
        if not isinstance(row, dict):
            continue
        dst_off = int(row.get("dst_screen_off", 0))
        src_off = int(row.get("src_pattern_off", 0))
        row_block = dst_off // 0x140
        x_byte = dst_off % 0x140
        if x_byte >= 0x28:
            continue
        x_px = x_byte * 8
        y_px = row_block * 8
        tile = decode_36a0_overlay_tile_rgba(pattern_block, src_off)
        nonzero = sum(1 for yy in range(8) for xx in range(8) if tile.getpixel((xx, yy))[3] != 0)
        tiles.append(
            {
                **dict(row),
                "x_px": int(x_px),
                "y_px": int(y_px),
                "rgba_hex": tile_image_to_rgba_hex(tile),
                "nonzero_pixels": int(nonzero),
            }
        )
    return tiles


def apply_36a0_overlay_call_plan(canvas: Image.Image, rect_px: dict[str, Any], overlay_call_plan: list[dict[str, Any]], ega_raw: bytes) -> dict[str, Any]:
    tiles = extract_36a0_overlay_tiles(rect_px, overlay_call_plan, ega_raw)
    count = 0
    for row in tiles:
        rgba_hex = row.get("rgba_hex")
        if not isinstance(rgba_hex, str):
            continue
        tile = Image.frombytes("RGBA", (8, 8), bytes.fromhex(rgba_hex))
        canvas.alpha_composite(tile, (int(row.get("x_px", 0)), int(row.get("y_px", 0))))
        count += 1
    return {"overlay_tiles_applied": int(count)}


def match_prior_11ae_offsets(current_offsets: list[int], prior_offsets: list[int]) -> list[dict[str, int]]:
    lookup = {int(v): idx for idx, v in enumerate(prior_offsets)}
    out: list[dict[str, int]] = []
    for idx, off in enumerate(current_offsets):
        if int(off) in lookup:
            out.append(
                {
                    "current_index": int(idx),
                    "dst_screen_off": int(off),
                    "prior_index": int(lookup[int(off)]),
                }
            )
    return out


def apply_36a0_temporal_replay_tiles(
    canvas: Image.Image,
    overlay_call_plan: list[dict[str, Any]],
    prior_temporal_state: dict[str, Any] | None,
    *,
    pattern_buffers: dict[str, bytearray] | None = None,
) -> dict[str, Any]:
    if not isinstance(prior_temporal_state, dict):
        return {
            "temporal_replay_tiles_applied": 0,
            "temporal_replay_nonzero_tiles": 0,
            "temporal_replay_lookup_misses": 0,
            "temporal_replay_masked_merges_applied": 0,
            "temporal_replay_tiles_changed_by_mask_merge": 0,
            "temporal_replay_tiles_changed_canvas": 0,
        }
    prior_tiles = prior_temporal_state.get("bank_11a6_saved_display_tiles", [])
    prior_offsets = prior_temporal_state.get("table_11ae_offsets", [])
    if not isinstance(prior_tiles, list):
        return {
            "temporal_replay_tiles_applied": 0,
            "temporal_replay_nonzero_tiles": 0,
            "temporal_replay_lookup_misses": 0,
            "temporal_replay_masked_merges_applied": 0,
            "temporal_replay_tiles_changed_by_mask_merge": 0,
            "temporal_replay_tiles_changed_canvas": 0,
        }
    if not isinstance(prior_offsets, list):
        prior_offsets = []
    pattern_1532 = None
    mask_1652 = None
    if isinstance(pattern_buffers, dict):
        if isinstance(pattern_buffers.get("buf_1532"), bytearray):
            pattern_1532 = pattern_buffers.get("buf_1532")
        if isinstance(pattern_buffers.get("buf_1652"), bytearray):
            mask_1652 = pattern_buffers.get("buf_1652")
    offset_to_idx: dict[int, int] = {}
    for i, off in enumerate(prior_offsets):
        if isinstance(off, int) and 0 <= i < len(prior_tiles):
            offset_to_idx[int(off)] = int(i)
    applied = 0
    nonzero_tiles = 0
    misses = 0
    masked_merges_applied = 0
    changed_by_merge = 0
    changed_canvas = 0
    for dst in overlay_call_plan:
        if not isinstance(dst, dict):
            continue
        dst_off = int(dst.get("dst_screen_off", 0))
        prior_idx = offset_to_idx.get(dst_off)
        if prior_idx is None or prior_idx < 0 or prior_idx >= len(prior_tiles):
            misses += 1
            continue
        src = prior_tiles[prior_idx]
        if not isinstance(src, dict):
            misses += 1
            continue
        rgba_hex = src.get("rgba_hex")
        if not isinstance(rgba_hex, str):
            misses += 1
            continue
        row_block = dst_off // 0x140
        x_byte = dst_off % 0x140
        if x_byte >= 0x28:
            misses += 1
            continue
        replay_hex = rgba_hex
        if pattern_1532 is not None and mask_1652 is not None:
            try:
                replay_hex = merge_tile_with_0a2b_mask(
                    rgba_hex,
                    pattern_1532=pattern_1532,
                    mask_1652=mask_1652,
                    cx=int(x_byte),
                )
                masked_merges_applied += 1
                if replay_hex != rgba_hex:
                    changed_by_merge += 1
            except Exception:
                replay_hex = rgba_hex
        try:
            tile = Image.frombytes("RGBA", (8, 8), bytes.fromhex(replay_hex))
        except Exception:
            misses += 1
            continue
        pre_hex = capture_canvas_tile_rgba_hex(canvas, x_byte * 8, row_block * 8)
        canvas.alpha_composite(tile, (x_byte * 8, row_block * 8))
        post_hex = capture_canvas_tile_rgba_hex(canvas, x_byte * 8, row_block * 8)
        if post_hex != pre_hex:
            changed_canvas += 1
        applied += 1
        if any(tile.getpixel((x, y))[3] != 0 for y in range(8) for x in range(8)):
            nonzero_tiles += 1
    return {
        "temporal_replay_tiles_applied": int(applied),
        "temporal_replay_nonzero_tiles": int(nonzero_tiles),
        "temporal_replay_lookup_misses": int(misses),
        "temporal_replay_masked_merges_applied": int(masked_merges_applied),
        "temporal_replay_tiles_changed_by_mask_merge": int(changed_by_merge),
        "temporal_replay_tiles_changed_canvas": int(changed_canvas),
    }


def _load_wroot_0x52_words(scratch_dir: Path | None) -> list[int]:
    if scratch_dir is None:
        return []
    try:
        obj = load_json(Path(scratch_dir) / "wroot_dgroup_low_projection_tables.json")
        rows = (((obj.get("tables") or {}).get("0x52_words")) or [])
        out: list[int] = []
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get("u16"), int):
                out.append(int(row["u16"]))
        return out
    except Exception:
        return []


def normalize_predicted_84f1_queue_entry(event: dict[str, Any], queue_index: int, *, scratch_dir: Path | None = None) -> dict[str, Any]:
    args = list(event.get("args", []))
    vals = [_scalar_or_expr(a) for a in args]
    while len(vals) < 7:
        vals.append(None)
    call_addr = str(event.get("call_addr", "")).lower()
    depth_index = int(event.get("depth", 0) or 0)
    if call_addr == "0x869a" and isinstance(vals[3], dict) and vals[3].get("expr") == "word ptr [0x363e]":
        vals[3] = 0x000F
    if isinstance(vals[1], dict) and vals[1].get("expr") == "word ptr [bx + 0x52]":
        bp8 = 0
        for arg in args:
            if isinstance(arg, dict) and str(arg.get("kind")) == "bp_immediate" and int(arg.get("bp_offset", -1)) == 0x08:
                if isinstance(arg.get("value"), int):
                    bp8 = int(arg.get("value"))
                    break
        words_52 = _load_wroot_0x52_words(scratch_dir)
        word_index = (3 * int(depth_index)) + int(bp8)
        if 0 <= word_index < len(words_52):
            vals[1] = int(words_52[word_index])
    if call_addr in ("0x873d", "0x87db") and isinstance(vals[0], int) and int(vals[0]) != 0xFF and isinstance(vals[3], int):
        # 84F1 queue rows from these callsites carry one-based attr seeds for 3670; consumer uses zero-based.
        vals[3] = max(0, int(vals[3]) - 1)
    if isinstance(vals[0], int):
        vals[0] = int(vals[0]) & 0xFF
    if isinstance(vals[3], int):
        vals[3] = int(vals[3]) & 0xFF
    if isinstance(vals[6], int):
        vals[6] = int(vals[6]) & 0xFF
    entry = {
        "queue_index": int(queue_index),
        "source": {
            "depth": int(event.get("depth", 0)),
            "pass_index": int(event.get("pass_index", 0)),
            "draw_target": str(event.get("draw_target", "")),
            "draw_index": event.get("draw_index"),
            "slot_hint": event.get("slot_hint"),
            "call_84f1": event.get("call_addr"),
        },
        "type": vals[0],
        "x0": vals[1],
        "y0": vals[2],
        "table_index": vals[3],
        "x1": vals[4],
        "y1": vals[5],
        "depth_tag": vals[6],
    }
    entry["attr"] = entry["table_index"]
    entry["x0_raw"] = entry["x0"]
    entry["y0_raw"] = entry["y0"]
    typ = entry.get("type")
    attr = entry.get("table_index")
    if isinstance(typ, int) and typ != 0xFF and isinstance(attr, int):
        tmeta = _load_type_metadata_record_13a(int(typ))
        if tmeta is not None:
            a = int(attr) & 0xFF
            x_off = 0x06 + (2 * a)  # 0x36E4 table: type*0x13A + 2*attr
            y_off = 0x39 + a        # 0x3717 table: type*0x13A + attr
            if x_off < len(tmeta):
                x_adj = int(tmeta[x_off])
                entry["x0_table_adjust"] = {
                    "dgroup_table": "0x36E4",
                    "index_formula": "type*0x13A + 2*attr",
                    "status": "resolved_via_winit_bootstrap_master_disk_scenario",
                    "value_u8": int(x_adj),
                    "value_s8": int(x_adj - 0x100) if (x_adj & 0x80) else int(x_adj),
                }
                if isinstance(entry.get("x0"), int):
                    entry["x0"] = (int(entry["x0"]) + int(x_adj)) & 0xFFFF
                    entry["x0_adjust_applied"] = True
            else:
                entry["x0_table_adjust"] = {
                    "dgroup_table": "0x36E4",
                    "index_formula": "type*0x13A + 2*attr",
                    "status": "metadata_record_present_but_x_adjust_oob",
                }
            if y_off < len(tmeta):
                y_adj = int(tmeta[y_off])
                entry["y0_table_adjust"] = {
                    "dgroup_table": "0x3717",
                    "index_formula": "type*0x13A + attr",
                    "status": "resolved_via_winit_bootstrap_master_disk_scenario",
                    "value_u8": int(y_adj),
                    "value_s8": int(y_adj - 0x100) if (y_adj & 0x80) else int(y_adj),
                }
                if isinstance(entry.get("y0"), int):
                    entry["y0"] = (int(entry["y0"]) + int(y_adj)) & 0xFFFF
                    entry["y0_adjust_applied"] = True
            else:
                entry["y0_table_adjust"] = {
                    "dgroup_table": "0x3717",
                    "index_formula": "type*0x13A + attr",
                    "status": "metadata_record_present_but_y_adjust_oob",
                }
        else:
            entry["x0_table_adjust"] = {
                "dgroup_table": "0x36E4",
                "index_formula": "type*0x13A + 2*attr",
                "status": "unresolved_table_bytes",
            }
            entry["y0_table_adjust"] = {
                "dgroup_table": "0x3717",
                "index_formula": "type*0x13A + attr",
                "status": "unresolved_table_bytes",
            }
    entry["w0"] = entry["x0"]
    entry["w2"] = entry["y0"]
    entry["w4"] = entry["x1"]
    entry["w6"] = entry["y1"]
    entry["b8_type"] = entry["type"]
    entry["b9_attr"] = entry["table_index"]
    entry["bA_depth"] = entry["depth_tag"]
    entry["runtime_dependencies"] = unique_preserve_order(extract_runtime_dependencies(entry))
    return entry


def build_predicted_queue_consumer_events(
    queue_entries: list[dict[str, Any]],
    *,
    scene_wx: int,
    scene_wy: int,
    facing_idx: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    emit_index = 0
    max_depth = -1
    for e in queue_entries:
        dt = e.get("depth_tag")
        if isinstance(dt, int):
            max_depth = max(max_depth, int(dt))
    if max_depth < 0:
        return events

    for depth in range(max_depth, -1, -1):
        # Queue depth tags are one-based in the traced 84F1 consumer path.
        # Convert to the visible depth index used by downstream stage rows.
        depth_out = max(0, int(depth) - 1)
        for e in reversed(queue_entries):
            if e.get("depth_tag") != depth:
                continue
            typ = e.get("type")
            if typ == 0xFF:
                src = dict(e.get("source", {})) if isinstance(e.get("source"), dict) else {}
                parity_521c = (int(depth) + int(scene_wx) + int(scene_wy) + (int(facing_idx) & 3)) & 1
                if parity_521c:
                    pair1_primary = e.get("x1")
                    pair1_alt = e.get("x0")
                    pair2_primary = e.get("y1")
                    pair2_alt = e.get("y0")
                else:
                    pair1_primary = e.get("x0")
                    pair1_alt = 0xFFFF
                    pair2_primary = e.get("y0")
                    pair2_alt = 0xFFFF
                events.append(
                    {
                        "_emit_index": int(emit_index),
                        "consumer_phase": "36ac_pair1",
                        "depth": int(depth_out),
                        "queue_index": int(e.get("queue_index", -1)),
                        "source": src,
                        "wrapper_target": "0x36AC",
                        "parity_521c": int(parity_521c),
                        "table_index": e.get("table_index"),
                        "x_primary": pair1_primary,
                        "x_alt": pair1_alt,
                        "x_alt_hint": e.get("x1"),
                        "runtime_dependencies": unique_preserve_order(extract_runtime_dependencies(e)),
                    }
                )
                emit_index += 1
                # WMAZE queue consumer does not emit the second 36AC call when y0 sentinel is -1.
                y0 = e.get("y0")
                y0_is_sentinel = isinstance(y0, int) and ((int(y0) & 0xFFFF) == 0xFFFF)
                if not y0_is_sentinel:
                    events.append(
                        {
                            "_emit_index": int(emit_index),
                            "consumer_phase": "36ac_pair2",
                            "depth": int(depth_out),
                            "queue_index": int(e.get("queue_index", -1)),
                            "source": src,
                            "wrapper_target": "0x36AC",
                            "parity_521c": int(parity_521c),
                            "table_index": e.get("table_index"),
                            "x_primary": pair2_primary,
                            "x_alt": pair2_alt,
                            "x_alt_hint": e.get("y1"),
                            "runtime_dependencies": unique_preserve_order(extract_runtime_dependencies(e)),
                        }
                    )
                    emit_index += 1
        for e in reversed(queue_entries):
            if e.get("depth_tag") != depth:
                continue
            typ = e.get("type")
            if typ == 0xFF:
                continue
            events.append(
                {
                    "_emit_index": int(emit_index),
                    "consumer_phase": "3670",
                    "depth": int(depth_out),
                    "queue_index": int(e.get("queue_index", -1)),
                    "source": dict(e.get("source", {})),
                    "wrapper_target": "0x3670",
                    "type": e.get("type"),
                    "x0": e.get("x0"),
                    "y0": e.get("y0"),
                    "x1": e.get("x1"),
                    "y1": e.get("y1"),
                    "table_index": e.get("table_index"),
                    "runtime_dependencies": unique_preserve_order(extract_runtime_dependencies(e)),
                }
            )
            emit_index += 1
    return events


def build_stage4_pre_present(
    runtime_init: RuntimeInitState,
    stage2: Stage2HelperEmission,
    stage3: Stage3QueueState,
) -> Stage4PrePresent:
    pre_present_draw_events: list[dict[str, Any]] = []

    for ev in stage2.immediate_direct_36ac_events:
        pre_present_draw_events.append(
            {
                "source_stage": "stage2_helper_emission",
                "event_family": "direct_36ac",
                "pipeline_phase": "immediate_pass_loop",
                "order_key": [0, int(ev.get("depth", 0)), int(ev.get("pass_index", 0)), 0, str(ev.get("call_addr", ""))],
                **dict(ev),
            }
        )

    phase_rank = {"36ac_pair1": 1, "36ac_pair2": 2, "3670": 3}
    for ev in stage3.predicted_queue_consumer_events:
        pre_present_draw_events.append(
            {
                "source_stage": "stage3_queue_state",
                "event_family": str(ev.get("consumer_phase", "unknown")),
                "pipeline_phase": "deferred_queue_consume",
                "order_key": [1, int(ev.get("depth", 0)), 1000 + int(ev.get("queue_index", -1)), int(phase_rank.get(str(ev.get("consumer_phase", "")), 9)), str(ev.get("wrapper_target", ""))],
                **dict(ev),
            }
        )

    pre_present_draw_events.sort(key=lambda e: tuple(e.get("order_key", [])))
    for ev in pre_present_draw_events:
        ev.pop("order_key", None)

    event_counts: dict[str, int] = {}
    for ev in pre_present_draw_events:
        key = str(ev.get("event_family", "unknown"))
        event_counts[key] = event_counts.get(key, 0) + 1

    unresolved = unique_preserve_order(
        list(stage2.runtime_dependencies)
        + list(stage3.unresolved_runtime_dependencies)
    )

    final_present_stage = {
        "wrapper_target": "0x36A0",
        "status": "unmodeled",
        "shared_viewport_rect_4fbc": runtime_init.shared_viewport_rect_4fbc,
        "notes": [
            "Pre-present events above are not final pixels.",
            "Real game still runs post-queue 0x36A0 using the driver shadow/present path.",
        ],
    }

    return Stage4PrePresent(
        pre_present_draw_events=pre_present_draw_events,
        event_counts=event_counts,
        unresolved_runtime_dependencies=unresolved,
        final_present_stage=final_present_stage,
    )


def build_stage5_present_contract(runtime_init: RuntimeInitState, stage4: Stage4PrePresent) -> Stage5PresentContract:
    shadow_buffer_ops: list[dict[str, Any]] = []
    viewport_rect = dict(runtime_init.shared_viewport_rect_4fbc)
    viewport_px = dict(viewport_rect.get("pixel_rect_estimate", {}))

    for idx, ev in enumerate(stage4.pre_present_draw_events):
        src = dict(ev.get("source", {})) if isinstance(ev.get("source"), dict) else {}
        family = str(ev.get("event_family", "unknown"))
        op_kind = "unknown"
        if family == "direct_36ac":
            op_kind = "shadow_draw_36ac_direct"
        elif family in ("36ac_pair1", "36ac_pair2"):
            op_kind = "shadow_draw_36ac_deferred"
        elif family == "3670":
            op_kind = "shadow_draw_3670_deferred"
        shadow_buffer_ops.append(
            {
                "shadow_op_index": idx,
                "op_kind": op_kind,
                "source_stage": ev.get("source_stage"),
                "event_family": family,
                "pipeline_phase": ev.get("pipeline_phase"),
                "depth": ev.get("depth"),
                "pass_index": ev.get("pass_index") if ev.get("pass_index") is not None else src.get("pass_index"),
                "queue_index": ev.get("queue_index"),
                "wrapper_target": ev.get("wrapper_target", "0x36AC" if "36ac" in family else "0x3670" if family == "3670" else None),
                "viewport_rect_px": viewport_px,
                "runtime_dependencies": list(ev.get("runtime_dependencies", [])),
                "args": [dict(a) for a in ev.get("args", []) if isinstance(a, dict)],
                "table_index": ev.get("table_index"),
                "x_primary": ev.get("x_primary"),
                "x_alt": ev.get("x_alt"),
                "type": ev.get("type"),
                "x0": ev.get("x0"),
                "y0": ev.get("y0"),
                "x1": ev.get("x1"),
                "y1": ev.get("y1"),
                "source_ref": {
                    "draw_target": ev.get("draw_target") if ev.get("draw_target") is not None else src.get("draw_target"),
                    "draw_index": ev.get("draw_index") if ev.get("draw_index") is not None else src.get("draw_index"),
                    "slot_hint": ev.get("slot_hint") if ev.get("slot_hint") is not None else src.get("slot_hint"),
                    "call_addr": ev.get("call_addr") if ev.get("call_addr") is not None else src.get("call_84f1"),
                    "consumer_phase": ev.get("consumer_phase"),
                },
            }
        )

    shadow_buffer_op_counts: dict[str, int] = {}
    for op in shadow_buffer_ops:
        key = str(op.get("op_kind", "unknown"))
        shadow_buffer_op_counts[key] = shadow_buffer_op_counts.get(key, 0) + 1

    return Stage5PresentContract(
        wrapper_target="0x36A0",
        driver_target="EGA.DRV:0x08B3",
        viewport_rect_4fbc=dict(runtime_init.shared_viewport_rect_4fbc),
        consumed_pre_present_event_count=len(stage4.pre_present_draw_events),
        shadow_buffer_ops=shadow_buffer_ops,
        shadow_buffer_op_counts=shadow_buffer_op_counts,
        required_inputs=[
            "driver shadow buffer backing store",
            "shared viewport rect descriptor [0x4FBC]",
            "ordered pre-present draw stream",
            "driver mode/table state used by 0x08B3",
        ],
        unresolved_runtime_dependencies=unique_preserve_order(
            list(stage4.unresolved_runtime_dependencies)
            + [
                "driver shadow buffer state (cs:[0x14D] backing path)",
                "0x08B3 helper tables/state (0x0974 / 0x0B03 users)",
            ]
        ),
        notes=[
            "This is the explicit final stage contract for the clean renderer.",
            "Stage 5 consumes the merged pre-present stream but does not itself resolve final pixels yet.",
            "Real parity still requires a software shadow/present implementation for 0x36A0.",
        ],
    )


def build_stage5_shadow_buffer_target(stage5: Stage5PresentContract) -> Stage5ShadowBufferTarget:
    rect = dict(stage5.viewport_rect_4fbc.get("pixel_rect_estimate", {}))
    width_px = int(rect.get("w_px", 0))
    height_px = int(rect.get("h_px", 0))
    schema = ShadowBufferSchema(
        width_px=width_px,
        height_px=height_px,
        plane_count=4,
        viewport_rect_px={
            "x_px": int(rect.get("x_px", 0)),
            "y_px": int(rect.get("y_px", 0)),
            "w_px": width_px,
            "h_px": height_px,
        },
        op_kinds=[
            "shadow_draw_36ac_direct",
            "shadow_draw_36ac_deferred",
            "shadow_draw_3670_deferred",
            "shadow_present_36a0",
        ],
        pixel_format_note="Planned target mirrors EGA-style 4-plane shadow composition before 0x36A0 present.",
    )

    planned_ops = [dict(op) for op in stage5.shadow_buffer_ops]
    planned_op_counts = dict(stage5.shadow_buffer_op_counts)
    planned_ops.append(
        {
            "shadow_op_index": len(planned_ops),
            "op_kind": "shadow_present_36a0",
            "wrapper_target": stage5.wrapper_target,
            "driver_target": stage5.driver_target,
            "viewport_rect_px": dict(schema.viewport_rect_px),
            "runtime_dependencies": list(stage5.unresolved_runtime_dependencies),
        }
    )
    planned_op_counts["shadow_present_36a0"] = planned_op_counts.get("shadow_present_36a0", 0) + 1

    return Stage5ShadowBufferTarget(
        schema=schema,
        planned_ops=planned_ops,
        planned_op_counts=planned_op_counts,
        unresolved_runtime_dependencies=list(stage5.unresolved_runtime_dependencies),
        notes=[
            "This is the concrete software target for future Stage 5 implementation.",
            "Ops are normalized but not executed yet.",
            "The final op is the explicit 0x36A0 present step.",
        ],
    )


def replay_stage5_shadow_buffer(
    target: Stage5ShadowBufferTarget,
    *,
    gamedata: Path | None = None,
    prior_present_temporal_state: dict[str, Any] | None = None,
) -> ShadowBufferReplayResult:
    executed_op_counts: dict[str, int] = {}
    execution_log: list[dict[str, Any]] = []
    coverage_regions: list[dict[str, Any]] = []
    coverage_row_spans: list[list[list[int]]] = [[] for _ in range(max(0, int(target.schema.height_px)))]
    direct_36ac_render_trace: list[dict[str, Any]] = []
    direct_36ac_tables = None
    direct_36ac_planar = None
    ega_36ac_emu = None
    deferred_canvas = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    present_overlay_canvas = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    ega_3670_emu = None
    ega_drv_raw = None
    viewport_rect_px = dict(target.schema.viewport_rect_px)
    if gamedata is not None:
        mazedata_ega = gamedata / "MAZEDATA.EGA"
        ega_drv = gamedata / "EGA.DRV"
        if mazedata_ega.exists() and ega_drv.exists():
            from bane.engine import ega_driver as ega_36ac_emu
            from bane.engine import ega_3670 as ega_3670_emu

            direct_36ac_tables = ega_36ac_emu.EGA36ACTables.load(mazedata_ega=mazedata_ega, ega_drv=ega_drv)
            direct_36ac_planar = ega_36ac_emu.EGA36ACPlanarBuffer()
            ega_drv_raw = _load_ega_drv_raw(gamedata)
    batched_3670_by_queue: dict[int, dict[str, Any]] = {}
    batched_3670_img = None
    if ega_3670_emu is not None and gamedata is not None:
        batch_events: list[dict[str, Any]] = []
        for op in target.planned_ops:
            if str(op.get("op_kind", "")) != "shadow_draw_3670_deferred":
                continue
            typ = op.get("type")
            x0v = op.get("x0")
            y0v = op.get("y0")
            x1v = op.get("x1")
            y1v = op.get("y1")
            table_index = op.get("table_index")
            if not all(isinstance(v, int) for v in (typ, x0v, y0v, x1v, y1v, table_index)):
                continue
            source_ref = dict(op.get("source_ref", {})) if isinstance(op.get("source_ref"), dict) else {}
            batch_events.append(
                {
                    "driver_wrapper": "0x3670",
                    "attr": int(table_index),
                    "depth": op.get("depth"),
                    "queue_index": op.get("queue_index"),
                    "source": {
                        "pass_index": op.get("pass_index"),
                        "draw_target": source_ref.get("draw_target"),
                        "draw_index": source_ref.get("draw_index"),
                        "slot_hint": source_ref.get("slot_hint"),
                        "call_addr": source_ref.get("call_addr"),
                    },
                    "likely_3670_semantics": {
                        "type_index": int(typ),
                        "x": int(x0v),
                        "y": int(y0v),
                        "clip_left": int(x1v),
                        "clip_right": int(y1v),
                        "flags1": 0,
                        "flags2": 0,
                    },
                }
            )
        if batch_events:
            batched_3670_img, batched_3670_meta = ega_3670_emu.render_estimated_queue_3670_events(
                events=batch_events,
                gamedata_dir=gamedata,
                prefer_exact_1d25_mon_seek0=True,
                allow_mon_runtime_sources=False,
                overlay_debug_markers=False,
            )
            for row in batched_3670_meta.get("real_trace", []) if isinstance(batched_3670_meta, dict) else []:
                if not isinstance(row, dict):
                    continue
                qi = row.get("queue_index")
                if isinstance(qi, int):
                    batched_3670_by_queue[int(qi)] = row
            if batched_3670_img is not None:
                deferred_canvas = Image.alpha_composite(deferred_canvas, batched_3670_img)
    shadow_state = {
        "initialized": True,
        "width_px": int(target.schema.width_px),
        "height_px": int(target.schema.height_px),
        "plane_count": int(target.schema.plane_count),
        "op_sequence_length": len(target.planned_ops),
        "family_counters": {
            "direct_36ac": 0,
            "deferred_36ac": 0,
            "deferred_3670": 0,
            "present_36a0": 0,
        },
        "last_present_rect": None,
        "coverage_regions": coverage_regions,
        "coverage_row_spans": coverage_row_spans,
        "coverage_pixels_estimate": 0,
        "direct_36ac_render_trace": direct_36ac_render_trace,
        "direct_36ac_tables_loaded": bool(direct_36ac_tables is not None and direct_36ac_planar is not None),
        "direct_36ac_events_total": 0,
        "direct_36ac_events_rendered": 0,
        "direct_36ac_events_noop": 0,
        "direct_36ac_events_failed": 0,
        "deferred_36ac_events_total": 0,
        "deferred_36ac_events_rendered": 0,
        "deferred_36ac_events_failed": 0,
        "deferred_3670_events_total": 0,
        "deferred_3670_events_replayed": 0,
        "deferred_3670_events_nonnoop": 0,
        "deferred_3670_events_noop": 0,
        "deferred_3670_events_failed": 0,
        "present_36a0_crop_nonzero_pixels": 0,
        "present_36a0_crop_bbox": None,
        "present_36a0_prior_state": None,
        "present_36a0_current_state": None,
        "present_36a0_marked_cells": [],
        "present_36a0_helper_copy_count": 0,
        "present_36a0_helper_copy_plan": [],
        "present_36a0_overlay_call_plan": [],
        "present_36a0_overlay_tiles_applied": 0,
        "present_36a0_temporal_replay_tiles_applied": 0,
        "present_36a0_temporal_replay_nonzero_tiles": 0,
        "present_36a0_temporal_replay_lookup_misses": 0,
        "present_36a0_temporal_replay_masked_merges_applied": 0,
        "present_36a0_temporal_replay_tiles_changed_by_mask_merge": 0,
        "present_36a0_temporal_replay_tiles_changed_canvas": 0,
        "present_36a0_requires_temporal_state": True,
        "present_36a0_temporal_buffers": {
            "uses_11a6_saved_display_tiles": True,
            "uses_11a8_sequential_shadow_tiles": True,
            "uses_11ae_indexed_cell_offsets": True,
        },
        "present_36a0_temporal_state": dict(prior_present_temporal_state)
        if isinstance(prior_present_temporal_state, dict)
        else {
            "frame_index": 0,
            "prior_present_state_available": False,
            "bank_11a6_saved_display_tiles": [],
            "bank_11a8_sequential_overlay_tiles": [],
            "table_11ae_offsets": [],
        },
        "present_36a0_temporal_state_input": dict(prior_present_temporal_state)
        if isinstance(prior_present_temporal_state, dict)
        else None,
        "present_36a0_prior_11ae_matches": [],
        "present_36a0_prior_saved_tile_matches": 0,
    }

    for op in target.planned_ops:
        op_kind = str(op.get("op_kind", "unknown"))
        executed_op_counts[op_kind] = executed_op_counts.get(op_kind, 0) + 1
        status = "recorded_only"
        viewport_rect_px = dict(op.get("viewport_rect_px", {}))
        region: dict[str, Any] | None = None
        if op_kind == "shadow_draw_36ac_direct":
            shadow_state["family_counters"]["direct_36ac"] += 1
            status = "shadow_state_updated"
            source_ref = dict(op.get("source_ref", {})) if isinstance(op.get("source_ref"), dict) else {}
            depth = int(op.get("depth", 0) or 0)
            slot_hint = str(source_ref.get("slot_hint") or "")
            full_w = int(viewport_rect_px.get("w_px", 0))
            full_h = int(viewport_rect_px.get("h_px", 0))
            args = list(op.get("args", []))
            arg_vals: list[int] = []
            for a in args:
                if isinstance(a, dict) and isinstance(a.get("value"), int):
                    arg_vals.append(int(a["value"]))
            x_seed = arg_vals[0] if arg_vals else 0
            x_seed_2 = arg_vals[2] if len(arg_vals) > 2 else x_seed
            attr_seed = arg_vals[1] if len(arg_vals) > 1 else 0
            width = max(10, full_w // max(3, depth + 1))
            height = max(12, full_h - min(full_h - 12, (depth - 1) * 20))
            x_norm = clamp_int((int(x_seed) - 120) // 2, 0, max(0, full_w - width))
            if int(x_seed_2) != 0xFFFF and int(x_seed_2) != int(x_seed):
                width = max(width, min(full_w, abs(int(x_seed_2) - int(x_seed)) // 2))
            if int(attr_seed) == 0:
                height = max(10, height // 2)
            x = int(viewport_rect_px.get("x_px", 0)) + x_norm
            y = int(viewport_rect_px.get("y_px", 0)) + max(0, (depth - 1) * 10)
            if slot_hint == "left":
                x = int(viewport_rect_px.get("x_px", 0)) + max(0, x_norm // 2)
            elif slot_hint == "right":
                x = int(viewport_rect_px.get("x_px", 0)) + min(max(0, full_w - width), max(x_norm, full_w // 2))
            region = {
                "shadow_op_index": int(op.get("shadow_op_index", -1)),
                "op_kind": op_kind,
                "x_px": x,
                "y_px": y,
                "w_px": width,
                "h_px": height,
                "reason": "arg_driven_direct_36ac_coverage",
            }
            coverage_regions.append(region)
            x0 = clamp_int(int(region["x_px"]) - int(viewport_rect_px.get("x_px", 0)), 0, max(0, int(target.schema.width_px)))
            y0 = clamp_int(int(region["y_px"]) - int(viewport_rect_px.get("y_px", 0)), 0, max(0, int(target.schema.height_px)))
            x1 = clamp_int(x0 + int(region["w_px"]), 0, int(target.schema.width_px))
            y1 = clamp_int(y0 + int(region["h_px"]), 0, int(target.schema.height_px))
            for ry in range(y0, y1):
                if x1 > x0:
                    coverage_row_spans[ry].append([x0, x1])
            shadow_state["coverage_pixels_estimate"] += max(0, (x1 - x0) * (y1 - y0))
            shadow_state["direct_36ac_events_total"] += 1
            if direct_36ac_tables is not None and direct_36ac_planar is not None:
                wrapper_args = [a.get("value") for a in args if isinstance(a, dict) and isinstance(a.get("value"), int)]
                if len(wrapper_args) == 3:
                    rec = ega_36ac_emu.emulate_36ac_wrapper_call(
                        direct_36ac_planar,
                        direct_36ac_tables,
                        arg1_desc=int(wrapper_args[0]),
                        arg2_mode_or_attr=int(wrapper_args[1]),
                        arg3_desc_or_minus1=int(wrapper_args[2]),
                    )
                    blits = [b for b in rec.get("blits", []) if isinstance(b, dict)]
                    event_nonnoop = any(bool(b.get("ok")) and not b.get("noop") and int(b.get("bytes_copied", 0) or 0) > 0 for b in blits)
                    event_noop = (not event_nonnoop) and any(bool(b.get("ok")) and b.get("noop") for b in blits)
                    if event_nonnoop:
                        shadow_state["direct_36ac_events_rendered"] += 1
                        status = "shadow_state_updated_real_36ac"
                    elif event_noop:
                        shadow_state["direct_36ac_events_noop"] += 1
                        status = "shadow_state_updated_real_36ac_noop"
                    else:
                        shadow_state["direct_36ac_events_failed"] += 1
                        status = "shadow_state_updated_real_36ac_failed"
                    direct_36ac_render_trace.append(
                        {
                            "shadow_op_index": int(op.get("shadow_op_index", -1)),
                            "call_addr": source_ref.get("call_addr"),
                            "depth": depth,
                            "args": wrapper_args,
                            "event_nonnoop": bool(event_nonnoop),
                            "event_noop": bool(event_noop),
                            "wrapper_record": rec,
                        }
                    )
        elif op_kind == "shadow_draw_36ac_deferred":
            shadow_state["family_counters"]["deferred_36ac"] += 1
            status = "shadow_state_updated"
            depth = int(op.get("depth", 0) or 0)
            full_w = int(viewport_rect_px.get("w_px", 0))
            full_h = int(viewport_rect_px.get("h_px", 0))
            width = max(8, full_w // max(2, depth + 1))
            height = max(8, full_h // max(2, depth + 1))
            source_ref = dict(op.get("source_ref", {})) if isinstance(op.get("source_ref"), dict) else {}
            phase = str(source_ref.get("consumer_phase") or "")
            x_primary = op.get("x_primary")
            x_alt = op.get("x_alt")
            x_seed = None
            if isinstance(x_primary, int):
                xp = signed16(int(x_primary))
                if xp != -1:
                    x_seed = xp
            if x_seed is None and isinstance(x_alt, int):
                xa = signed16(int(x_alt))
                if xa != -1:
                    x_seed = xa
            if x_seed is None:
                x_seed = 0
            x_norm = clamp_int((int(x_seed) + 32) // 2, 0, max(0, full_w - width))
            if phase == "36ac_pair2":
                y = int(viewport_rect_px.get("y_px", 0)) + max(0, full_h - height - depth * 4)
            else:
                y = int(viewport_rect_px.get("y_px", 0)) + depth * 4
            x = int(viewport_rect_px.get("x_px", 0)) + x_norm
            region = {
                "shadow_op_index": int(op.get("shadow_op_index", -1)),
                "op_kind": op_kind,
                "x_px": x,
                "y_px": y,
                "w_px": width,
                "h_px": height,
                "reason": "placeholder_deferred_36ac_coverage",
            }
            coverage_regions.append(region)
            x0 = clamp_int(int(region["x_px"]) - int(viewport_rect_px.get("x_px", 0)), 0, max(0, int(target.schema.width_px)))
            y0 = clamp_int(int(region["y_px"]) - int(viewport_rect_px.get("y_px", 0)), 0, max(0, int(target.schema.height_px)))
            x1 = clamp_int(x0 + int(region["w_px"]), 0, int(target.schema.width_px))
            y1 = clamp_int(y0 + int(region["h_px"]), 0, int(target.schema.height_px))
            for ry in range(y0, y1):
                if x1 > x0:
                    coverage_row_spans[ry].append([x0, x1])
            shadow_state["coverage_pixels_estimate"] += max(0, (x1 - x0) * (y1 - y0))
            shadow_state["deferred_36ac_events_total"] += 1
            if direct_36ac_tables is not None and direct_36ac_planar is not None:
                table_index = op.get("table_index")
                x_primary = op.get("x_primary")
                x_alt = op.get("x_alt")
                if all(isinstance(v, int) for v in (table_index, x_primary, x_alt)):
                    rec = ega_36ac_emu.emulate_36ac_wrapper_call(
                        direct_36ac_planar,
                        direct_36ac_tables,
                        arg1_desc=int(x_primary),
                        arg2_mode_or_attr=int(table_index),
                        arg3_desc_or_minus1=int(x_alt),
                    )
                    blits = [b for b in rec.get("blits", []) if isinstance(b, dict)]
                    event_nonnoop = any(bool(b.get("ok")) and not b.get("noop") and int(b.get("bytes_copied", 0) or 0) > 0 for b in blits)
                    event_noop = (not event_nonnoop) and any(bool(b.get("ok")) and b.get("noop") for b in blits)
                    if event_nonnoop:
                        shadow_state["deferred_36ac_events_rendered"] += 1
                        status = "shadow_state_updated_real_deferred_36ac"
                    elif event_noop:
                        status = "shadow_state_updated_real_deferred_36ac_noop"
                    else:
                        shadow_state["deferred_36ac_events_failed"] += 1
                        status = "shadow_state_updated_real_deferred_36ac_failed"
        elif op_kind == "shadow_draw_3670_deferred":
            shadow_state["family_counters"]["deferred_3670"] += 1
            status = "shadow_state_updated"
            depth = int(op.get("depth", 0) or 0)
            full_w = int(viewport_rect_px.get("w_px", 0))
            full_h = int(viewport_rect_px.get("h_px", 0))
            width = max(12, full_w // max(3, depth + 2))
            height = max(12, full_h // max(3, depth + 2))
            x0 = op.get("x0")
            y0 = op.get("y0")
            x_seed = signed16(int(x0)) if isinstance(x0, int) else 0
            y_seed = signed16(int(y0)) if isinstance(y0, int) else 0
            x_norm = clamp_int((x_seed + 32) // 2, 0, max(0, full_w - width))
            y_norm = clamp_int(y_seed // 2, 0, max(0, full_h - height))
            x = int(viewport_rect_px.get("x_px", 0)) + x_norm
            y = int(viewport_rect_px.get("y_px", 0)) + y_norm
            region = {
                "shadow_op_index": int(op.get("shadow_op_index", -1)),
                "op_kind": op_kind,
                "x_px": x,
                "y_px": y,
                "w_px": width,
                "h_px": height,
                "reason": "placeholder_deferred_3670_coverage",
            }
            coverage_regions.append(region)
            x0 = clamp_int(int(region["x_px"]) - int(viewport_rect_px.get("x_px", 0)), 0, max(0, int(target.schema.width_px)))
            y0 = clamp_int(int(region["y_px"]) - int(viewport_rect_px.get("y_px", 0)), 0, max(0, int(target.schema.height_px)))
            x1 = clamp_int(x0 + int(region["w_px"]), 0, int(target.schema.width_px))
            y1 = clamp_int(y0 + int(region["h_px"]), 0, int(target.schema.height_px))
            for ry in range(y0, y1):
                if x1 > x0:
                    coverage_row_spans[ry].append([x0, x1])
            shadow_state["coverage_pixels_estimate"] += max(0, (x1 - x0) * (y1 - y0))
            shadow_state["deferred_3670_events_total"] += 1
            if batched_3670_by_queue:
                shadow_state["deferred_3670_events_replayed"] += 1
                qi = op.get("queue_index")
                rec = batched_3670_by_queue.get(int(qi)) if isinstance(qi, int) else None
                if isinstance(rec, dict) and bool(rec.get("ok")):
                    if bool(rec.get("noop")):
                        shadow_state["deferred_3670_events_noop"] += 1
                        status = "shadow_state_updated_real_deferred_3670_noop"
                    else:
                        shadow_state["deferred_3670_events_nonnoop"] += 1
                        status = "shadow_state_updated_real_deferred_3670"
                elif isinstance(rec, dict):
                    shadow_state["deferred_3670_events_failed"] += 1
                    status = "shadow_state_updated_real_deferred_3670_failed"
        elif op_kind == "shadow_present_36a0":
            shadow_state["family_counters"]["present_36a0"] += 1
            rect_px = dict(op.get("viewport_rect_px", {}))
            prior = shadow_state.get("present_36a0_current_state")
            current = emulate_36a0_grid_state_from_rect(rect_px)
            current_for_next = dict(current)
            current_for_next["state_11aa"] = int(current["state_11ac"])
            current_for_next["state_11ab"] = int(current["state_11ad"])
            if not isinstance(prior, dict):
                prior = {
                    "state_11aa": int(current["state_11ac"]),
                    "state_11ab": int(current["state_11ad"]),
                    "state_1194_base": int(current["state_1194_base"]),
                }
            marked = emulate_36a0_marked_cells(
                int(prior.get("state_11aa", current["state_11ac"])),
                int(prior.get("state_11ab", current["state_11ad"])),
                int(prior.get("state_1194_base", current["state_1194_base"])),
            )
            helper_plan = emulate_36a0_helper_copy_plan(
                int(prior.get("state_1194_base", current["state_1194_base"])),
                int(current["state_11c0_base"]),
                marked,
            )
            overlay_call_plan = emulate_36a0_overlay_call_plan(
                int(current["state_11c0_base"]),
                int(current["state_11ac"]),
                int(current["state_11ad"]),
            )
            helper_copy_count = emulate_36a0_helper_copy_count(
                int(current["state_11ac"]),
                int(current["state_11ad"]),
            )
            shadow_state["last_present_rect"] = rect_px
            shadow_state["present_36a0_prior_state"] = dict(prior)
            shadow_state["present_36a0_current_state"] = dict(current_for_next)
            shadow_state["present_36a0_marked_cells"] = [int(v) for v in marked]
            shadow_state["present_36a0_helper_copy_count"] = int(helper_copy_count)
            shadow_state["present_36a0_helper_copy_plan"] = [dict(v) for v in helper_plan]
            shadow_state["present_36a0_overlay_call_plan"] = [dict(v) for v in overlay_call_plan]
            if ega_drv_raw is not None:
                pre_present_canvas = deferred_canvas.copy()
                if direct_36ac_planar is not None:
                    pre_present_canvas = Image.alpha_composite(
                        pre_present_canvas,
                        direct_36ac_planar.to_rgba_image(transparent_zero=True),
                    )
                overlay_tiles = extract_36a0_overlay_tiles(rect_px, overlay_call_plan, ega_drv_raw)
                pattern_buffers = emulate_36a0_runtime_pattern_buffers(rect_px, ega_drv_raw)
                overlay_meta = apply_36a0_overlay_call_plan(
                    present_overlay_canvas,
                    rect_px,
                    overlay_call_plan,
                    ega_drv_raw,
                )
                shadow_state["present_36a0_overlay_tiles_applied"] = int(overlay_meta.get("overlay_tiles_applied", 0))
                prior_temporal = shadow_state.get("present_36a0_temporal_state")
                shadow_state["present_36a0_temporal_state_input"] = dict(prior_temporal) if isinstance(prior_temporal, dict) else None
                frame_index = 1
                prior_available = False
                prior_offsets: list[int] = []
                if isinstance(prior_temporal, dict):
                    frame_index = int(prior_temporal.get("frame_index", 0) or 0) + 1
                    prior_available = bool(prior_temporal.get("frame_index", 0))
                    raw_offsets = prior_temporal.get("table_11ae_offsets", [])
                    if isinstance(raw_offsets, list):
                        prior_offsets = [int(v) for v in raw_offsets if isinstance(v, int)]
                current_offsets = [int(t.get("dst_screen_off", 0)) for t in overlay_tiles]
                prior_matches = match_prior_11ae_offsets(current_offsets, prior_offsets)
                temporal_meta = apply_36a0_temporal_replay_tiles(
                    present_overlay_canvas,
                    overlay_call_plan,
                    prior_temporal if isinstance(prior_temporal, dict) else None,
                    pattern_buffers=pattern_buffers,
                )
                shadow_state["present_36a0_temporal_state"] = {
                    "frame_index": int(frame_index),
                    "prior_present_state_available": bool(prior_available),
                    "bank_11a6_nonzero_tiles": 0,
                    "bank_11a8_nonzero_tiles": int(sum(1 for t in overlay_tiles if int(t.get("nonzero_pixels", 0)) > 0)),
                    "bank_11a6_saved_display_tiles": [],
                    "bank_11a8_sequential_overlay_tiles": [dict(t) for t in overlay_tiles],
                    "table_11ae_offsets": [int(t.get("dst_screen_off", 0)) for t in overlay_tiles],
                }
                shadow_state["present_36a0_prior_11ae_matches"] = [dict(v) for v in prior_matches]
                shadow_state["present_36a0_prior_saved_tile_matches"] = int(len(prior_matches))
                shadow_state["present_36a0_temporal_replay_tiles_applied"] = int(temporal_meta.get("temporal_replay_tiles_applied", 0))
                shadow_state["present_36a0_temporal_replay_nonzero_tiles"] = int(temporal_meta.get("temporal_replay_nonzero_tiles", 0))
                shadow_state["present_36a0_temporal_replay_lookup_misses"] = int(temporal_meta.get("temporal_replay_lookup_misses", 0))
                shadow_state["present_36a0_temporal_replay_masked_merges_applied"] = int(
                    temporal_meta.get("temporal_replay_masked_merges_applied", 0)
                )
                shadow_state["present_36a0_temporal_replay_tiles_changed_by_mask_merge"] = int(
                    temporal_meta.get("temporal_replay_tiles_changed_by_mask_merge", 0)
                )
                shadow_state["present_36a0_temporal_replay_tiles_changed_canvas"] = int(
                    temporal_meta.get("temporal_replay_tiles_changed_canvas", 0)
                )
            status = "present_contract_recorded_state_modeled"
        execution_log.append(
            {
                "shadow_op_index": int(op.get("shadow_op_index", -1)),
                "op_kind": op_kind,
                "status": status,
                "viewport_rect_px": viewport_rect_px,
                "runtime_dependencies": list(op.get("runtime_dependencies", [])),
                "source_ref": dict(op.get("source_ref", {})) if isinstance(op.get("source_ref"), dict) else None,
                "coverage_region": region,
            }
        )

    if direct_36ac_planar is not None:
        full_img = direct_36ac_planar.to_rgba_image(transparent_zero=True)
        # Queue 3670 consumer phase is emitted after deferred 36AC pair phases.
        # Composite deferred 3670 above 36AC planar output.
        combined_img = Image.alpha_composite(full_img, deferred_canvas)
        combined_img = Image.alpha_composite(combined_img, present_overlay_canvas)
        pts = shadow_state.get("present_36a0_temporal_state")
        overlay_plan = shadow_state.get("present_36a0_overlay_call_plan")
        if isinstance(pts, dict) and isinstance(overlay_plan, list):
            saved_tiles: list[dict[str, Any]] = []
            saved_nonzero = 0
            for tile in overlay_plan:
                if not isinstance(tile, dict):
                    continue
                x_px = int(tile.get("dst_screen_off", 0)) % 0x140
                y_px = int(tile.get("dst_screen_off", 0)) // 0x140
                if x_px >= 0x28:
                    continue
                sx = x_px * 8
                sy = y_px * 8
                saved_hex = capture_canvas_tile_rgba_hex(combined_img, sx, sy)
                saved_raw = bytes.fromhex(saved_hex)
                if any(saved_raw[i] != 0 for i in range(3, len(saved_raw), 4)):
                    saved_nonzero += 1
                saved_tiles.append(
                    {
                        "row": int(tile.get("row", 0)),
                        "col": int(tile.get("col", 0)),
                        "dst_screen_off": int(tile.get("dst_screen_off", 0)),
                        "x_px": int(sx),
                        "y_px": int(sy),
                        "rgba_hex": saved_hex,
                    }
                )
            pts["bank_11a6_saved_display_tiles"] = saved_tiles
            pts["bank_11a6_nonzero_tiles"] = int(saved_nonzero)
        full_bbox = bbox_nonzero_rgba(full_img)
        combined_bbox = bbox_nonzero_rgba(combined_img)
        crop_x = int(viewport_rect_px.get("x_px", 0))
        crop_y = int(viewport_rect_px.get("y_px", 0))
        crop_w = int(viewport_rect_px.get("w_px", 0))
        crop_h = int(viewport_rect_px.get("h_px", 0))
        crop = full_img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        combined_crop = combined_img.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
        px = crop.load()
        cpx = combined_crop.load()
        nonzero = 0
        combined_nonzero = 0
        for yy in range(crop.height):
            for xx in range(crop.width):
                if px[xx, yy][3] != 0:
                    nonzero += 1
                if cpx[xx, yy][3] != 0:
                    combined_nonzero += 1
        shadow_state["direct_36ac_crop_nonzero_pixels"] = int(nonzero)
        shadow_state["direct_36ac_full_bbox"] = dict(full_bbox) if isinstance(full_bbox, dict) else None
        shadow_state["combined_shadow_crop_nonzero_pixels"] = int(combined_nonzero)
        shadow_state["combined_shadow_full_bbox"] = dict(combined_bbox) if isinstance(combined_bbox, dict) else None
        shadow_state["present_36a0_crop_nonzero_pixels"] = int(combined_nonzero)
        shadow_state["present_36a0_crop_bbox"] = bbox_nonzero_rgba(combined_crop)
        shadow_state["direct_36ac_crop_rect"] = {
            "x_px": crop_x,
            "y_px": crop_y,
            "w_px": crop_w,
            "h_px": crop_h,
        }

    return ShadowBufferReplayResult(
        width_px=int(target.schema.width_px),
        height_px=int(target.schema.height_px),
        plane_count=int(target.schema.plane_count),
        shadow_state=shadow_state,
        executed_op_counts=executed_op_counts,
        execution_log=execution_log,
        unresolved_runtime_dependencies=list(target.unresolved_runtime_dependencies),
        notes=[
            "This is the first executable Stage 5 step.",
            "Replay now mutates high-level shadow-buffer family state and records placeholder spatial coverage.",
            "Direct 36AC ops also execute through the real 36AC software decoder when MAZEDATA.EGA and EGA.DRV are available.",
        ],
    )


def build_stage1_pass_state(
    *,
    gamedata: Path,
    scratch_dir: Path,
    runtime_init: RuntimeInitState,
    scene: SceneState,
    prior_present_temporal_state: dict[str, Any] | None = None,
) -> tuple[Stage1PassState, Stage2HelperEmission, Stage3QueueState, Stage4PrePresent, Stage5PresentContract, Stage5ShadowBufferTarget, ShadowBufferReplayResult]:
    pass_param_map = load_json(scratch_dir / "wmaze_render_pass_param_map.json")
    helper_modes = load_json(scratch_dir / "wmaze_helper_draw_mode_map.json")
    draw_index_maps_raw = load_json(scratch_dir / "wmaze_class_code_to_draw_index_map.json")
    classifier_tables = build_classifier_tables(scratch_dir)
    classifier_policy = load_classifier_index_policy(scratch_dir, scene.map_id)
    facing_idx = facing_to_index(scene.facing)
    class_code_maps = {
        str(name): {str(k): int(v) for k, v in mapping.items()}
        for name, mapping in draw_index_maps_raw.items()
        if isinstance(mapping, dict)
    }

    pass_templates: list[PassTemplate] = []
    pass_rows: list[PassStateRow] = []
    zero_state = runtime_init.wmaze_zero_state
    predicted_class_state_by_depth: dict[str, dict[str, int | None]] = {}
    predicted_gate_state_by_depth: dict[str, dict[str, bool]] = {}
    render_depth_limit = scene_render_depth_limit(scene)

    initial_gate_state: dict[str, int] = {}
    for addr in ("0x507A", "0x5082", "0x508A", "0x5092", "0x509A", "0x50A2", "0x521E", "0x5220", "0x5222", "0x5224", "0x5226", "0x5228"):
        val = parse_zero_state_word(zero_state, addr)
        if val is not None:
            initial_gate_state[addr] = val

    marker_set_by_depth: dict[int, set[str]] = {}
    current_gate_state_by_depth: dict[int, dict[str, bool]] = {}
    for depth in range(1, render_depth_limit + 1):
        center = find_visible_slot(scene, depth=depth, orient="center")
        left = find_visible_slot(scene, depth=depth, orient="left")
        right = find_visible_slot(scene, depth=depth, orient="right")
        marker_set: set[str] = set()
        if should_apply_7d8c_topflag(map_id=scene.map_id, slot=left):
            marker_set.add("5066")
        if should_apply_7d8c_topflag(map_id=scene.map_id, slot=center):
            marker_set.add("5067")
        if should_apply_7d8c_topflag(map_id=scene.map_id, slot=right):
            marker_set.add("5068")
        marker_set_by_depth[depth] = marker_set
        gates = apply_topflag_sideeffects_for_depth(
            map_id=scene.map_id,
            center=center,
            left=left,
            right=right,
        )
        current_gate_state_by_depth[depth] = dict(gates)
        predicted_gate_state_by_depth[str(depth)] = dict(gates)

    passes = pass_param_map.get("passes", [])
    for pass_info in passes:
        if not isinstance(pass_info, dict):
            continue
        draw_target = str(pass_info.get("draw_target"))
        arg_bp6_source = str(pass_info.get("arg_bp6_source"))
        class_state_word_addr = ARG_BP6_CLASS_STATE_ADDRS.get(arg_bp6_source)
        slot_hint = CLASS_STATE_SLOT_HINTS.get(class_state_word_addr) if class_state_word_addr else None
        template = PassTemplate(
            pass_index=int(pass_info.get("pass_index", 0)),
            draw_target=draw_target,
            cleanup_target=str(pass_info.get("cleanup_target")) if pass_info.get("cleanup_target") is not None else None,
            gate_flag_addr=str(pass_info.get("gate", {}).get("flag_disp")) if isinstance(pass_info.get("gate"), dict) else None,
            arg_bp4_source=str(pass_info.get("arg_bp4_source")),
            arg_bp6_source=arg_bp6_source,
            class_state_word_addr=class_state_word_addr,
            slot_hint=slot_hint,
            immediate_by_bp_offset={str(k): int(v) for k, v in dict(pass_info.get("immediate_by_bp_offset", {})).items()},
            helper_mode_family=helper_mode_family_for_pass(draw_target, helper_modes),
            classifier_family=classifier_family_for_target(draw_target),
            draw_index_map_family=draw_index_map_family_for_target(draw_target),
        )
        pass_templates.append(template)

        for depth in range(1, render_depth_limit + 1):
            unresolved: list[str] = []
            visible_slot = find_visible_slot(scene, depth=depth, orient=slot_hint)
            gate_initial_value = parse_zero_state_word(zero_state, template.gate_flag_addr) if template.gate_flag_addr else None
            gate_predicted_enabled = None
            class_state_initial_value = parse_zero_state_word(zero_state, template.class_state_word_addr) if template.class_state_word_addr else None
            predicted_class_state_value: int | None = None
            predicted_class_code: int | None = None
            predicted_draw_index: int | None = None

            if template.draw_target == "0x85D0" and visible_slot is not None:
                if visible_slot.channel4 is not None and visible_slot.channel2 is not None:
                    predicted_class_state_value = emulate_7d8c_tail_switch(
                        int(visible_slot.channel4),
                        int(visible_slot.wall_value),
                        int(visible_slot.channel2),
                        int(facing_idx),
                    )
                    predicted_draw_index = predicted_class_state_value
                else:
                    unresolved.append("missing channel4/channel2 for 7D8C-style draw index")
            elif template.draw_target == "0x8B18" and visible_slot is not None:
                if visible_slot.channel4 is not None and visible_slot.channel2 is not None:
                    pol = classifier_policy.get(int(visible_slot.wall_value), {"variant": "A", "seed_index": 0})
                    variant = str(pol.get("variant", "A")).upper()
                    seed_index = int(pol.get("seed_index", 0))
                    predicted_class_state_value = emulate_classifier_index(
                        int(visible_slot.channel4),
                        int(visible_slot.channel2),
                        int(facing_idx),
                        variant,
                        seed_index,
                    )
                    classifier_table = classifier_tables.get(template.classifier_family or "", {})
                    predicted_class_code = classifier_table.get(str(predicted_class_state_value))
                    draw_map = class_code_maps.get(template.draw_index_map_family or "", {})
                    if predicted_class_code is not None:
                        predicted_draw_index = draw_map.get(str(predicted_class_code))
                    else:
                        unresolved.append("classifier index did not map to a class code")
                else:
                    unresolved.append("missing channel4/channel2 for classifier emulation")
            elif template.class_state_word_addr is not None:
                unresolved.append("class state derivation not implemented for this draw target")

            if predicted_draw_index is None and template.draw_index_map_family is not None and template.draw_target != "0x8D07":
                unresolved.append("predicted draw index unresolved")
            if template.slot_hint is None and template.draw_target != "0x8D07":
                unresolved.append("slot_hint unresolved from arg_bp6_source")
            if visible_slot is None and template.slot_hint is not None:
                unresolved.append("visible_slot missing for slot/depth pair")
            if template.class_state_word_addr is not None:
                depth_state = predicted_class_state_by_depth.setdefault(str(depth), {})
                depth_state[template.class_state_word_addr] = predicted_class_state_value

            pass_rows.append(
                PassStateRow(
                    depth=depth,
                    pass_index=template.pass_index,
                    draw_target=template.draw_target,
                    cleanup_target=template.cleanup_target,
                    gate_flag_addr=template.gate_flag_addr,
                    gate_initial_value=gate_initial_value,
                    gate_predicted_enabled=gate_predicted_enabled,
                    arg_bp4_value=depth,
                    class_state_word_addr=template.class_state_word_addr,
                    class_state_initial_value=class_state_initial_value,
                    predicted_class_state_value=predicted_class_state_value,
                    predicted_class_code=predicted_class_code,
                    predicted_draw_index=predicted_draw_index,
                    slot_hint=template.slot_hint,
                    visible_slot=visible_slot,
                    helper_mode_family=template.helper_mode_family,
                    classifier_family=template.classifier_family,
                    draw_index_map_family=template.draw_index_map_family,
                    unresolved=unresolved,
                )
            )

    helper_mode_tables = {
        str(name): {
            int(k): dict(v)
            for k, v in table.items()
            if isinstance(v, dict)
        }
        for name, table in dict(helper_modes.get("tables", {})).items()
        if isinstance(table, dict)
    }
    direct_call_tables, queue_call_tables = build_helper_call_tables(scratch_dir)

    for row in pass_rows:
        possible_draw_indices: list[int] = []
        direct_36ac_draw_indices: list[int] = []
        queue_84f1_draw_indices: list[int] = []
        no_output_draw_indices: list[int] = []

        if row.draw_index_map_family in class_code_maps:
            possible_draw_indices = sorted(class_code_maps[row.draw_index_map_family].values())
        if row.draw_target == "0x85D0":
            table_name = "85D0.class_draw_switch"
        elif row.draw_target == "0x8B18":
            table_name = "8B18.class_draw_switch"
        else:
            table_name = ""

        if table_name and table_name in helper_mode_tables:
            for idx, info in sorted(helper_mode_tables[table_name].items()):
                modes = set(str(v) for v in info.get("modes", []))
                if "direct_36ac" in modes:
                    direct_36ac_draw_indices.append(idx)
                elif "queue_84f1" in modes:
                    queue_84f1_draw_indices.append(idx)
                else:
                    no_output_draw_indices.append(idx)

        row.possible_draw_indices = possible_draw_indices
        row.direct_36ac_draw_indices = direct_36ac_draw_indices
        row.queue_84f1_draw_indices = queue_84f1_draw_indices
        row.no_output_draw_indices = no_output_draw_indices

    # Apply gate evaluation and cleanup mutations in pass order, per depth.
    rows_by_depth: dict[int, list[PassStateRow]] = {}
    for row in pass_rows:
        rows_by_depth.setdefault(int(row.depth), []).append(row)
    for depth, depth_rows in rows_by_depth.items():
        current_gates = dict(current_gate_state_by_depth.get(depth, init_depth_gate_state()))
        depth_rows.sort(key=lambda r: int(r.pass_index))
        for row in depth_rows:
            gate_key = pass_gate_key(int(row.pass_index))
            row.gate_predicted_enabled = bool(current_gates.get(gate_key, True)) if gate_key is not None else None
            if row.gate_predicted_enabled is False:
                row.predicted_output_mode = "gated_off"
            elif (
                row.draw_target in ("0x85D0", "0x8B18")
                and row.visible_slot is not None
                and int(row.visible_slot.wall_value) == 0
            ):
                row.predicted_output_mode = "gated_off"
            elif row.draw_target == "0x8D07":
                if row.visible_slot is not None and int(row.visible_slot.wall_value) == 0:
                    row.predicted_output_mode = "gated_off"
                else:
                    row.predicted_output_mode = "immediate_non_helper_dispatch"
            elif row.predicted_draw_index is None:
                row.predicted_output_mode = "unresolved"
            elif row.predicted_draw_index in row.direct_36ac_draw_indices:
                row.predicted_output_mode = "direct_36ac"
            elif row.predicted_draw_index in row.queue_84f1_draw_indices:
                row.predicted_output_mode = "queue_84f1"
            elif row.predicted_draw_index in row.no_output_draw_indices:
                row.predicted_output_mode = "no_output"
            elif row.draw_target in ("0x85D0", "0x8B18"):
                row.predicted_output_mode = "unresolved"
            else:
                row.predicted_output_mode = "non_helper_or_unresolved"

            if row.predicted_output_mode != "gated_off":
                apply_cleanup_to_gate_state(
                    current_gates,
                    row.cleanup_target,
                    row.predicted_class_state_value,
                    row.slot_hint,
                    marker_set_by_depth.get(depth, set()),
                )
            predicted_gate_state_by_depth[str(depth)] = dict(current_gates)

    predicted_output_mode_counts: dict[str, int] = {}
    for row in pass_rows:
        key = str(row.predicted_output_mode or "unresolved")
        predicted_output_mode_counts[key] = predicted_output_mode_counts.get(key, 0) + 1
    template_by_pass_index = {t.pass_index: t for t in pass_templates}
    predicted_helper_event_counts: dict[str, int] = {}
    immediate_direct_36ac_events: list[dict[str, Any]] = []
    deferred_queue_emission_events: list[dict[str, Any]] = []
    for row in pass_rows:
        template = template_by_pass_index.get(row.pass_index)
        if template is None:
            continue
        row.predicted_helper_events = build_predicted_helper_events(row, template, direct_call_tables, queue_call_tables)
        for ev in row.predicted_helper_events:
            key = str(ev.get("event_kind", "unknown"))
            predicted_helper_event_counts[key] = predicted_helper_event_counts.get(key, 0) + 1
            normalized = {
                "depth": int(row.depth),
                "pass_index": int(row.pass_index),
                "draw_target": str(row.draw_target),
                "draw_index": row.predicted_draw_index,
                "slot_hint": row.slot_hint,
                "class_state_word_addr": row.class_state_word_addr,
                "predicted_class_state_value": row.predicted_class_state_value,
                "call_addr": ev.get("call_addr"),
                "args": ev.get("args", []),
                "runtime_dependencies": list(ev.get("runtime_dependencies", [])),
            }
            if ev.get("event_kind") == "direct_36ac":
                immediate_direct_36ac_events.append(normalized)
            elif ev.get("event_kind") == "queue_84f1":
                deferred_queue_emission_events.append(normalized)

    immediate_direct_36ac_events.sort(key=lambda e: (int(e.get("depth", 0)), int(e.get("pass_index", 0)), str(e.get("call_addr", ""))))
    deferred_queue_emission_events.sort(key=lambda e: (int(e.get("depth", 0)), int(e.get("pass_index", 0)), str(e.get("call_addr", ""))))
    predicted_queue_entries = [
        normalize_predicted_84f1_queue_entry(ev, idx, scratch_dir=scratch_dir)
        for idx, ev in enumerate(deferred_queue_emission_events)
    ]
    predicted_queue_consumer_events = build_predicted_queue_consumer_events(
        predicted_queue_entries,
        scene_wx=int(scene.wx),
        scene_wy=int(scene.wy),
        facing_idx=int(facing_idx),
    )

    stage1 = Stage1PassState(
        pass_templates=pass_templates,
        initial_gate_state=initial_gate_state,
        predicted_class_state_by_depth=predicted_class_state_by_depth,
        predicted_gate_state_by_depth=predicted_gate_state_by_depth,
        helper_mode_summary=dict(helper_modes.get("summary", {})),
        predicted_output_mode_counts=predicted_output_mode_counts,
        class_code_maps=class_code_maps,
        classifier_tables=classifier_tables,
        pass_rows=pass_rows,
    )
    stage2 = Stage2HelperEmission(
        predicted_helper_event_counts=predicted_helper_event_counts,
        immediate_direct_36ac_events=immediate_direct_36ac_events,
        deferred_queue_emission_events=deferred_queue_emission_events,
        runtime_dependencies=unique_preserve_order(
            extract_runtime_dependencies(immediate_direct_36ac_events)
            + extract_runtime_dependencies(deferred_queue_emission_events)
        ),
    )
    stage3 = Stage3QueueState(
        predicted_queue_entries=predicted_queue_entries,
        predicted_queue_consumer_events=predicted_queue_consumer_events,
        unresolved_runtime_dependencies=unique_preserve_order(
            extract_runtime_dependencies(predicted_queue_entries)
            + extract_runtime_dependencies(predicted_queue_consumer_events)
            + ["post-queue 0x36A0 present stage not yet modeled here"]
        ),
    )
    stage4 = build_stage4_pre_present(runtime_init, stage2, stage3)
    stage5 = build_stage5_present_contract(runtime_init, stage4)
    stage5_target = build_stage5_shadow_buffer_target(stage5)
    stage5_replay = replay_stage5_shadow_buffer(
        stage5_target,
        gamedata=gamedata,
        prior_present_temporal_state=prior_present_temporal_state,
    )
    return (stage1, stage2, stage3, stage4, stage5, stage5_target, stage5_replay)


def build_stage_reference(
    *,
    gamedata: Path,
    scratch_dir: Path,
    map_id: int,
    wx: int,
    wy: int,
    facing: str,
    prior_present_temporal_state: dict[str, Any] | None = None,
) -> StageOutputs:
    runtime_init = RuntimeInitState.from_artifacts(scratch_dir)
    scene = build_scene_state(gamedata=gamedata, map_id=map_id, wx=wx, wy=wy, facing=facing)
    stage1_pass_state, stage2_helper_emission, stage3_queue_state, stage4_pre_present, stage5_present_contract, stage5_shadow_buffer_target, stage5_shadow_buffer_replay = build_stage1_pass_state(
        gamedata=gamedata,
        scratch_dir=scratch_dir,
        runtime_init=runtime_init,
        scene=scene,
        prior_present_temporal_state=prior_present_temporal_state,
    )
    notes = [
        "This is a clean stage-boundary reference object, not a final renderer.",
        "Stage 1/2/3/4/5 are structural only: pass-state, helper emission, queue state, pre-present merge, and present contract.",
        "Immediate helper draws, deferred queue replay, and shadow/present are intentionally not implemented here yet.",
        "The purpose is to separate runtime prerequisites and scene-state extraction from the hybrid prototype.",
    ]
    # Touch MAZEDATA decode so stage skeleton carries the same asset prerequisite as the final renderer.
    decode_mazedata_tiles(gamedata / "MAZEDATA.EGA")
    return StageOutputs(
        runtime_init=runtime_init,
        scene=scene,
        stage1_pass_state=stage1_pass_state,
        stage2_helper_emission=stage2_helper_emission,
        stage3_queue_state=stage3_queue_state,
        stage4_pre_present=stage4_pre_present,
        stage5_present_contract=stage5_present_contract,
        stage5_shadow_buffer_target=stage5_shadow_buffer_target,
        stage5_shadow_buffer_replay=stage5_shadow_buffer_replay,
        notes=notes,
    )


def render_shadow_coverage_mask(replay: ShadowBufferReplayResult) -> Image.Image:
    width = int(replay.width_px)
    height = int(replay.height_px)
    img = Image.new("RGBA", (width, height), (6, 8, 14, 255))
    px = img.load()
    row_spans = replay.shadow_state.get("coverage_row_spans", [])
    for y, spans in enumerate(row_spans):
        if y < 0 or y >= height or not isinstance(spans, list):
            continue
        for span in spans:
            if not (isinstance(span, list) and len(span) == 2):
                continue
            x0 = clamp_int(int(span[0]), 0, width)
            x1 = clamp_int(int(span[1]), 0, width)
            for x in range(x0, x1):
                r, g, b, a = px[x, y]
                if (r, g, b) == (6, 8, 14):
                    px[x, y] = (220, 220, 220, 255)
                else:
                    # Accumulate overlap intensity to make repeated ops visible.
                    px[x, y] = (
                        min(255, r + 12),
                        min(255, g + 6),
                        min(255, b + 2),
                        a,
                    )
    return img


def render_stage5_shadow_image(
    target: Stage5ShadowBufferTarget,
    replay: ShadowBufferReplayResult,
    *,
    gamedata: Path,
    include_deferred_3670: bool = True,
    include_present_36a0: bool = True,
) -> Image.Image:
    width = int(replay.width_px)
    height = int(replay.height_px)
    img = Image.new("RGBA", (width, height), (6, 8, 14, 255))
    mazedata_ega = gamedata / "MAZEDATA.EGA"
    ega_drv = gamedata / "EGA.DRV"
    if not (mazedata_ega.exists() and ega_drv.exists()):
        return img
    from bane.engine import ega_driver as ega_36ac_emu
    from bane.engine import ega_3670 as ega_3670_emu

    tables = ega_36ac_emu.EGA36ACTables.load(mazedata_ega=mazedata_ega, ega_drv=ega_drv)
    full_canvas = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    present_overlay_canvas = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    ega_drv_raw = _load_ega_drv_raw(gamedata)
    prior_temporal_state = None
    if isinstance(replay.shadow_state, dict):
        pts = replay.shadow_state.get("present_36a0_temporal_state_input")
        if not isinstance(pts, dict):
            pts = replay.shadow_state.get("present_36a0_temporal_state")
        if isinstance(pts, dict):
            prior_temporal_state = pts
    for op in target.planned_ops:
        op_kind = str(op.get("op_kind", ""))
        if op_kind == "shadow_draw_36ac_direct":
            args = list(op.get("args", []))
            wrapper_args = [a.get("value") for a in args if isinstance(a, dict) and isinstance(a.get("value"), int)]
            if len(wrapper_args) != 3:
                continue
            planar = ega_36ac_emu.EGA36ACPlanarBuffer()
            ega_36ac_emu.emulate_36ac_wrapper_call(
                planar,
                tables,
                arg1_desc=int(wrapper_args[0]),
                arg2_mode_or_attr=int(wrapper_args[1]),
                arg3_desc_or_minus1=int(wrapper_args[2]),
            )
            full_canvas = Image.alpha_composite(full_canvas, planar.to_rgba_image(transparent_zero=True))
            continue
        if op_kind == "shadow_draw_36ac_deferred":
            table_index = op.get("table_index")
            x_primary = op.get("x_primary")
            x_alt = op.get("x_alt")
            if not all(isinstance(v, int) for v in (table_index, x_primary, x_alt)):
                continue
            planar = ega_36ac_emu.EGA36ACPlanarBuffer()
            ega_36ac_emu.emulate_36ac_wrapper_call(
                planar,
                tables,
                arg1_desc=int(x_primary),
                arg2_mode_or_attr=int(table_index),
                arg3_desc_or_minus1=int(x_alt),
            )
            full_canvas = Image.alpha_composite(full_canvas, planar.to_rgba_image(transparent_zero=True))
            continue
        if op_kind == "shadow_draw_3670_deferred":
            if not include_deferred_3670:
                continue
            typ = op.get("type")
            x0 = op.get("x0")
            y0 = op.get("y0")
            x1 = op.get("x1")
            y1 = op.get("y1")
            table_index = op.get("table_index")
            if not all(isinstance(v, int) for v in (typ, x0, y0, x1, y1, table_index)):
                continue
            source_ref = dict(op.get("source_ref", {})) if isinstance(op.get("source_ref"), dict) else {}
            ev = {
                "driver_wrapper": "0x3670",
                "attr": int(table_index),
                "depth": op.get("depth"),
                "queue_index": op.get("queue_index"),
                "source": {
                    "pass_index": op.get("pass_index"),
                    "draw_target": source_ref.get("draw_target"),
                    "draw_index": source_ref.get("draw_index"),
                    "slot_hint": source_ref.get("slot_hint"),
                    "call_addr": source_ref.get("call_addr"),
                },
                "likely_3670_semantics": {
                    "type_index": int(typ),
                    "x": int(x0),
                    "y": int(y0),
                    "clip_left": int(x1),
                    "clip_right": int(y1),
                    "flags1": 0,
                    "flags2": 0,
                },
            }
            ev_img, _ = ega_3670_emu.render_estimated_queue_3670_events(
                events=[ev],
                gamedata_dir=gamedata,
                prefer_exact_1d25_mon_seek0=True,
                allow_mon_runtime_sources=False,
                overlay_debug_markers=False,
            )
            if ev_img is not None:
                full_canvas = Image.alpha_composite(full_canvas, ev_img)
            continue
        if op_kind == "shadow_present_36a0" and ega_drv_raw is not None:
            if not include_present_36a0:
                continue
            rect_px = dict(op.get("viewport_rect_px", {}))
            current = emulate_36a0_grid_state_from_rect(rect_px)
            overlay_call_plan = emulate_36a0_overlay_call_plan(
                int(current["state_11c0_base"]),
                int(current["state_11ac"]),
                int(current["state_11ad"]),
            )
            pattern_buffers = emulate_36a0_runtime_pattern_buffers(rect_px, ega_drv_raw)
            apply_36a0_overlay_call_plan(present_overlay_canvas, rect_px, overlay_call_plan, ega_drv_raw)
            apply_36a0_temporal_replay_tiles(
                present_overlay_canvas,
                overlay_call_plan,
                prior_temporal_state,
                pattern_buffers=pattern_buffers,
            )
            continue
    full_canvas = Image.alpha_composite(full_canvas, present_overlay_canvas)
    viewport_rect = dict(target.schema.viewport_rect_px)
    crop_x = int(viewport_rect.get("x_px", 0))
    crop_y = int(viewport_rect.get("y_px", 0))
    crop_w = int(viewport_rect.get("w_px", width))
    crop_h = int(viewport_rect.get("h_px", height))
    full_canvas = Image.alpha_composite(Image.new("RGBA", (320, 200), (6, 8, 14, 255)), full_canvas)
    return full_canvas.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))


def load_prior_present_temporal_state(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        obj = json.loads(path.read_text())
        return (
            ((obj.get("stage5_shadow_buffer_replay") or {}).get("shadow_state") or {}).get("present_36a0_temporal_state")
            if isinstance(obj, dict)
            else None
        )
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a clean stage-based maze-render reference state object.")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument("--scratch-dir", type=Path, default=Path("scratch"))
    ap.add_argument("--map-id", type=int, required=True)
    ap.add_argument("--wx", type=int, required=True)
    ap.add_argument("--wy", type=int, required=True)
    ap.add_argument("--facing", choices=["N", "E", "S", "W"], required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--coverage-mask-out", type=Path, default=None)
    ap.add_argument("--shadow-image-out", type=Path, default=None)
    ap.add_argument("--prior-stage-reference", type=Path, default=None)
    args = ap.parse_args()

    prior_present_temporal_state = load_prior_present_temporal_state(args.prior_stage_reference)
    out = build_stage_reference(
        gamedata=args.gamedata,
        scratch_dir=args.scratch_dir,
        map_id=args.map_id,
        wx=args.wx,
        wy=args.wy,
        facing=args.facing,
        prior_present_temporal_state=prior_present_temporal_state,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(asdict(out), indent=2))
    if args.coverage_mask_out is not None:
        args.coverage_mask_out.parent.mkdir(parents=True, exist_ok=True)
        render_shadow_coverage_mask(out.stage5_shadow_buffer_replay).save(args.coverage_mask_out)
    if args.shadow_image_out is not None:
        args.shadow_image_out.parent.mkdir(parents=True, exist_ok=True)
        render_stage5_shadow_image(
            out.stage5_shadow_buffer_target,
            out.stage5_shadow_buffer_replay,
            gamedata=args.gamedata,
        ).save(args.shadow_image_out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
