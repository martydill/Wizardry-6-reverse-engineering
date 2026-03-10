from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

from bane.engine.ega_driver import MAZEDATA_GRAYSCALE_PALETTE


def _signed16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if (v & 0x8000) else v


def _event_color(type_idx: int, attr: int) -> tuple[int, int, int, int]:
    # Stable debug colors (not game palette semantics).
    base = (int(type_idx) * 37 + int(attr) * 17) & 0xFF
    r = (64 + base) & 0xFF
    g = (96 + (base * 3)) & 0xFF
    b = (160 + (base * 5)) & 0xFF
    return (r, g, b, 200)


def _as_int(v):
    return v if isinstance(v, int) else None


def _u16le(buf: bytes, off: int) -> int:
    if off < 0 or off + 2 > len(buf):
        return 0
    return int.from_bytes(buf[off : off + 2], "little")


def _rol8_1(v: int) -> int:
    v &= 0xFF
    return ((v << 1) | (v >> 7)) & 0xFF


def _score_3670_replay_candidate(
    score_structural: int,
    replay_ok: int,
    replay_nonnoop: int,
    replay_pixels: int,
    replay_bad: Counter,
) -> int:
    # Candidate validity on real queue events matters more than overdraw.
    fatal = (
        int(replay_bad.get("frame_dims_implausible", 0))
        + int(replay_bad.get("first_record_oob", 0))
        + int(replay_bad.get("220c_compose_failed", 0))
    )
    other_bad = sum(
        int(v) for k, v in replay_bad.items() if k not in {"frame_dims_implausible", "first_record_oob", "220c_compose_failed"}
    )
    return (
        int(score_structural)
        + int(replay_ok) * 320
        + int(replay_nonnoop) * 140
        + int(min(8000, replay_pixels) // 12)
        - int(fatal) * 420
        - int(other_bad) * 120
    )


class _RGBACompositor:
    def __init__(self) -> None:
        self.img = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
        self.px = self.img.load()

    def blit_sprite(
        self,
        sprite_rgba: Image.Image,
        *,
        x: int,
        y: int,
        clip_left: int,
        clip_right: int,
    ) -> int:
        spx = sprite_rgba.load()
        w, h = sprite_rgba.size
        drawn = 0
        # Queue events frequently carry clip_left > clip_right and are observed to render
        # through a wrapped horizontal span in software replay.
        y0 = max(0, int(y))
        y1 = min(200, int(y) + h)
        if y0 >= y1:
            return 0
        cl = int(clip_left)
        cr = int(clip_right)
        clip_spans: list[tuple[int, int]]
        if cl <= cr:
            clip_spans = [(cl, cr)]
        else:
            # Wrapped interval: [cl,320) U [0,cr)
            clip_spans = [(cl, 320), (0, cr)]
        for span_l, span_r in clip_spans:
            x0 = max(0, int(span_l), int(x))
            x1 = min(320, int(span_r), int(x) + w)
            if x0 >= x1:
                continue
            for dy in range(y0, y1):
                sy = dy - int(y)
                for dx in range(x0, x1):
                    sx = dx - int(x)
                    rgba = spx[sx, sy]
                    if rgba[3] == 0:
                        continue
                    self.px[dx, dy] = rgba
                    drawn += 1
        return drawn


def _sprite_alpha_bbox(sprite_rgba: Image.Image) -> tuple[int, int, int, int] | None:
    bbox = sprite_rgba.getbbox()
    if bbox is None:
        return None
    return tuple(int(v) for v in bbox)


def _wrapped_horizontal_intersection_len(a0: int, a1: int, clip_left: int, clip_right: int, *, width: int = 320) -> int:
    if a1 <= a0:
        return 0
    if clip_left <= clip_right:
        spans = [(clip_left, clip_right)]
    else:
        spans = [(clip_left, width), (0, clip_right)]
    total = 0
    for l, r in spans:
        x0 = max(int(a0), int(l))
        x1 = min(int(a1), int(r))
        if x1 > x0:
            total += x1 - x0
    return int(max(0, total))


class _Scratch220C:
    def __init__(self, frame_w_cells: int, frame_h_cells: int) -> None:
        self.w = max(0, int(frame_w_cells))
        self.h = max(0, int(frame_h_cells))
        self.buf = bytearray([0xFF] * (self.w * self.h * 0x20))

    def _tile_off(self, tx: int, ty: int) -> int:
        return (ty * self.w + tx) * 0x20

    def compose_command(self, chunk: bytes, *, attr_cmd: int, flags1: int) -> dict:
        # Implemented for queue path target flags1=0; nonzero flags still attempt basic path.
        # EGA.DRV:0x220C starts with `dec al` and uses the resulting 8-bit value as the
        # descriptor selector, so attr_cmd==0 selects record 0xFF (record 256), not terminator.
        rec_idx = ((int(attr_cmd) & 0xFF) - 1) & 0xFF
        rec = rec_idx * 0x18
        if rec < 0 or rec + 0x18 > len(chunk):
            return {"ok": False, "reason": "record_oob", "record_off": rec, "record_index": rec_idx}
        src = _u16le(chunk, rec + 0)
        mask_ptr = rec + 4
        if mask_ptr + 20 > len(chunk):
            return {"ok": False, "reason": "mask_oob", "record_off": rec}

        # 220C local [bp-6] row base offset; vertical-flip path modifies this, but queue path uses flags1=0.
        rows_composed = 0
        tiles_composed = 0
        unsupported_flags = []
        if flags1 & 0x0003:
            if flags1 & 0x0001:
                unsupported_flags.append("hmirror")
            if flags1 & 0x0002:
                unsupported_flags.append("vflip")
        # Non-flipped path matches queue consumer usage (flags1=0).
        bx = mask_ptr
        dl = 1
        for ty in range(self.h):
            for tx in range(self.w):
                if bx >= len(chunk):
                    return {"ok": False, "reason": "mask_scan_oob", "mask_ptr": bx}
                occupied = (chunk[bx] & dl) != 0
                if occupied:
                    tile_off = self._tile_off(tx, ty)
                    if src + 0x20 > len(chunk):
                        return {
                            "ok": False,
                            "reason": "src_tile_oob",
                            "src": int(src),
                            "need": 0x20,
                            "chunk_len": len(chunk),
                        }
                    # 220C occupied-cell blend into scratch; each tile is 32 bytes: 8 rows * 4 planes.
                    for r in range(8):
                        p0 = chunk[src + r + 0x00]
                        p1 = chunk[src + r + 0x08]
                        p2 = chunk[src + r + 0x10]
                        p3 = chunk[src + r + 0x18]
                        bh = p0 & p1 & p2 & p3
                        inv = (~bh) & 0xFF
                        d0 = self.buf[tile_off + r + 0x00]
                        d1 = self.buf[tile_off + r + 0x08]
                        d2 = self.buf[tile_off + r + 0x10]
                        d3 = self.buf[tile_off + r + 0x18]
                        self.buf[tile_off + r + 0x00] = (p0 & inv) | (d0 & bh)
                        self.buf[tile_off + r + 0x08] = (p1 & inv) | (d1 & bh)
                        self.buf[tile_off + r + 0x10] = (p2 & inv) | (d2 & bh)
                        self.buf[tile_off + r + 0x18] = (p3 & inv) | (d3 & bh)
                    src += 0x20
                    tiles_composed += 1
                dl = _rol8_1(dl)
                if dl == 1:
                    bx += 1
            rows_composed += 1
        return {
            "ok": True,
            "record_off": rec,
            "rows_composed": rows_composed,
            "tiles_composed": tiles_composed,
            "unsupported_flags": unsupported_flags,
        }

    def to_rgba(self) -> Image.Image:
        out = Image.new("RGBA", (self.w * 8, self.h * 8), (0, 0, 0, 0))
        px = out.load()
        for ty in range(self.h):
            for tx in range(self.w):
                tile_off = self._tile_off(tx, ty)
                for r in range(8):
                    p0 = self.buf[tile_off + r + 0x00]
                    p1 = self.buf[tile_off + r + 0x08]
                    p2 = self.buf[tile_off + r + 0x10]
                    p3 = self.buf[tile_off + r + 0x18]
                    for bit in range(8):
                        m = 1 << bit
                        idx = (
                            (1 if (p0 & m) else 0)
                            | ((1 if (p1 & m) else 0) << 1)
                            | ((1 if (p2 & m) else 0) << 2)
                            | ((1 if (p3 & m) else 0) << 3)
                        )
                        # Scratch background is 0xFF in all planes => idx 15, used as transparency mask.
                        if idx == 15:
                            continue
                        x = tx * 8 + (7 - bit)
                        y = ty * 8 + r
                        rr, gg, bb = MAZEDATA_GRAYSCALE_PALETTE[idx & 0x0F]
                        px[x, y] = (rr, gg, bb, 255)
        return out


def _decode_1d25_rle_stream(data: bytes, off: int, *, max_out: int = 0x8000) -> tuple[bytes | None, int]:
    file_i = int(off)
    block = b""
    si = 0
    bytes_read = 0

    def _refill() -> bool:
        nonlocal file_i, block, si, bytes_read
        if file_i >= len(data):
            return False
        end = min(len(data), file_i + 0x1000)
        block = data[file_i:end]
        bytes_read += (end - file_i)
        file_i = end
        si = 0
        return len(block) > 0

    def _lodsb_checked_for_control() -> int | None:
        nonlocal si
        # EGA.DRV:1D6C refills when SI >= 0x0FFF, so byte 0x0FFF of each 0x1000 read block is not
        # consumed as a *control byte* by the top-level decode loop. Literal/repeat payload bytes can
        # still read through that position before the next top-level boundary check.
        if not block and not _refill():
            return None
        if si >= 0x0FFF:
            if not _refill():
                return None
        if si >= len(block):
            return None
        b = block[si]
        si += 1
        return int(b)

    def _read_data_bytes(cnt: int) -> bytes | None:
        nonlocal si
        if not block and not _refill():
            return None
        if si + int(cnt) > len(block):
            return None
        outb = bytes(block[si : si + int(cnt)])
        si += int(cnt)
        return outb

    out = bytearray()
    while len(out) < max_out:
        b = _lodsb_checked_for_control()
        if b is None:
            break
        if b == 0:
            return (bytes(out), int(bytes_read))
        if b & 0x80:
            cnt = ((0x100 - b) & 0xFF)
            repv_b = _read_data_bytes(1)
            if repv_b is None:
                return (None, 0)
            out.extend([repv_b[0]] * cnt)
        else:
            cnt = b
            lit = _read_data_bytes(cnt)
            if lit is None:
                return (None, 0)
            out.extend(lit)
    return (None, 0)


def _load_type_to_record_map_from_callmap(path_str: str) -> dict[int, int]:
    p = Path(path_str)
    try:
        obj = json.loads(p.read_text())
    except Exception:
        return {}
    out: dict[int, int] = {}
    for k, v in (obj.get("summary", {}) or {}).get("type_to_record_index_map", {}).items():
        try:
            out[int(k)] = int(v)
        except Exception:
            continue
    return out


def _load_overlay_startup_order() -> dict[str, int]:
    p = Path("scratch/wroot_overlay_startup_dispatch.json")
    try:
        obj = json.loads(p.read_text())
    except Exception:
        return {}
    out: dict[str, int] = {}
    for idx, row in enumerate((obj.get("startup_36dc_calls") or [])):
        if not isinstance(row, dict):
            continue
        base = row.get("base_name")
        if not isinstance(base, str):
            continue
        out[f"{base.upper()}.OVR"] = idx
    return out


def _load_mon_type_chunk_args() -> dict[int, dict]:
    p = Path("scratch/mon_loader_type_chunk_args.json")
    try:
        obj = json.loads(p.read_text())
    except Exception:
        return {}
    out: dict[int, dict] = {}
    for row in obj.get("types", []) or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("status")) != "ok":
            continue
        try:
            t = int(row.get("type_index"))
        except Exception:
            continue
        out[t] = row
    return out


def _load_likely_premaze_mon_sources() -> dict[int, dict]:
    p = Path("scratch/mon_loader_type_slot_timeline.json")
    try:
        obj = json.loads(p.read_text())
    except Exception:
        return {}
    out: dict[int, dict] = {}
    for k, v in ((obj.get("likely_premaze_type_sources") or {}).items()):
        if not isinstance(v, dict):
            continue
        try:
            t = int(k)
        except Exception:
            try:
                t = int(v.get("type_index"))
            except Exception:
                continue
        out[t] = v
    return out


def _load_known_mon_loader_type_maps() -> dict[int, list[dict]]:
    startup_order = _load_overlay_startup_order()
    merged: dict[int, list[dict]] = {}
    # Preferred path: aggregate clone extractor with helper-level provenance.
    agg = Path("scratch/mon_loader_clone_call_maps.json")
    try:
        agg_obj = json.loads(agg.read_text())
    except Exception:
        agg_obj = None
    if isinstance(agg_obj, dict):
        for helper in agg_obj.get("helpers", []) or []:
            if not isinstance(helper, dict):
                continue
            mod_name = str(helper.get("module") or "").upper()
            helper_addr = str(helper.get("helper_addr") or "")
            label = f"{mod_name.replace('.OVR', '')}:{helper_addr}"
            order = startup_order.get(mod_name, 9999)
            tmap = ((helper.get("summary") or {}).get("type_to_record_index_map") or {})
            if not isinstance(tmap, dict):
                continue
            for k, v in tmap.items():
                try:
                    t_idx = int(k)
                    rec_idx = int(v)
                except Exception:
                    continue
                merged.setdefault(t_idx, []).append(
                    {
                        "source_helper": label,
                        "record_index": rec_idx,
                        "startup_order": int(order),
                    }
                )

    # Always merge explicit extracts too; the aggregate clone scan can miss helpers depending on pattern strictness.
    sources = [
        ("WINIT:0x4721", "scratch/winit_4721_call_map.json", startup_order.get("WINIT.OVR", 0)),
        ("WBASE:0x4BB2", "scratch/wbase_4bb2_call_map.json", startup_order.get("WBASE.OVR", 1)),
    ]
    existing_keys = {
        (int(ti), int(r.get("record_index", -1)), str(r.get("source_helper", "")))
        for ti, rows in merged.items()
        for r in rows
        if isinstance(r, dict)
    }
    for label, path_str, order in sources:
        tmap = _load_type_to_record_map_from_callmap(path_str)
        for t_idx, rec_idx in tmap.items():
            key = (int(t_idx), int(rec_idx), label)
            if key in existing_keys:
                continue
            merged.setdefault(int(t_idx), []).append(
                {
                    "source_helper": label,
                    "record_index": int(rec_idx),
                    "startup_order": int(order),
                }
            )
            existing_keys.add(key)
    for vals in merged.values():
        vals.sort(key=lambda r: (int(r.get("startup_order", 9999)), str(r.get("source_helper", ""))))
    return merged


def _score_type_chunk_candidate(
    chunk: bytes,
    *,
    attrs: set[int],
) -> tuple[int, dict] | None:
    if not chunk:
        return None
    max_attr = max(attrs) if attrs else 0
    if max_attr <= 0 or len(chunk) < max_attr * 0x18:
        return None
    score = 0
    recs = {}
    rec_blobs: dict[int, bytes] = {}
    penalties: list[str] = []
    for a in sorted(attrs):
        if (int(a) & 0xFF) == 0:
            # attr byte 0 is valid in the 1D94/220C path (maps to record 0xFF after `dec al`),
            # but it is a poor structural signal for chunk candidate pruning because many plausible
            # chunks will have descriptor 255 values that look "junk" under the simple heuristics.
            # Keep attr0 for actual replay, but exclude it from structural candidate gating/scoring.
            continue
        rec = ((((int(a) & 0xFF) - 1) & 0xFF) * 0x18)
        if rec + 0x18 > len(chunk):
            return None
        rec_blob = bytes(chunk[rec : rec + 0x18])
        rec_blobs[a] = rec_blob
        src = _u16le(chunk, rec)
        w = chunk[rec + 2]
        h = chunk[rec + 3]
        occ = chunk[rec + 4 : rec + 0x18]
        # Queue scene uses small wall-slice records; keep bounds broad but reject obvious junk.
        if not (1 <= w <= 16 and 1 <= h <= 16):
            return None
        if src + 0x20 > len(chunk):
            return None
        tiles_upper = w * h
        if src + tiles_upper * 0x20 > len(chunk) + 0x2000:
            return None
        recs[a] = {"src": src, "w": w, "h": h, "occ_nonzero": sum(1 for b in occ if b)}
        score += 20
        score += min(10, recs[a]["occ_nonzero"])
        if any(b not in (0x00, 0xFF) for b in occ):
            score += 4
        if src != 0 and (src % 0x20) == 0:
            score += 2
        # Penalize obvious junk records (e.g., whole descriptor filled with one byte).
        uniq_rec = len(set(rec_blob))
        if uniq_rec <= 2:
            score -= 18
            penalties.append(f"attr{a}_low_record_entropy_{uniq_rec}")
        uniq_occ = len(set(occ)) if occ else 0
        if uniq_occ <= 1 and any(occ):
            score -= 10
            penalties.append(f"attr{a}_uniform_mask")
        used_mask_bytes = ((int(w) + 7) // 8) * int(h)
        if 0 < used_mask_bytes < len(occ):
            tail = occ[used_mask_bytes:]
            # Real records often leave padding zero; random nonzero padding across all tail bytes is suspicious.
            if tail and all(b != 0 for b in tail):
                score -= 8
                penalties.append(f"attr{a}_mask_tail_all_nonzero")
    # Penalize duplicate descriptors across attrs used in the same queue scene.
    duplicate_low_entropy = False
    if len(rec_blobs) >= 2:
        seen = {}
        for a, blob in rec_blobs.items():
            if blob in seen:
                score -= 24
                penalties.append(f"duplicate_record_attr{seen[blob]}_attr{a}")
                if len(set(blob)) <= 2:
                    duplicate_low_entropy = True
            else:
                seen[blob] = a
    if duplicate_low_entropy:
        return None
    # Additional plausibility: first 32 records have sane dims.
    plausible = 0
    for i in range(min(32, len(chunk) // 0x18)):
        rec = i * 0x18
        w = chunk[rec + 2]
        h = chunk[rec + 3]
        if 0 <= w <= 16 and 0 <= h <= 16:
            plausible += 1
    score += plausible
    return (
        score,
        {
            "attr_records": recs,
            "plausible_first32": plausible,
            "chunk_len": len(chunk),
            "penalties": penalties,
        },
    )


def _find_best_type_chunk_rle_offset(
    maze_bytes: bytes,
    *,
    attrs: set[int],
    sample_events: list[dict] | None = None,
    scan_start: int = 0x800,
) -> dict | None:
    candidates: list[dict] = []
    allow_replay_rescue = bool(sample_events) and any(((int(a) & 0xFF) == 0) for a in (attrs or set())) and int(scan_start) == 0
    rescue_offset_limit = 0x1000
    for off in range(max(0, int(scan_start)), len(maze_bytes) - 2):
        b0 = maze_bytes[off]
        if b0 == 0:
            continue
        chunk, consumed = _decode_1d25_rle_stream(maze_bytes, off)
        if chunk is None:
            continue
        scored = _score_type_chunk_candidate(chunk, attrs=attrs)
        if scored is None:
            if not (allow_replay_rescue and int(off) < rescue_offset_limit):
                continue
            score = -100000
            details = {
                "structural_rejected": True,
                "rescue_reason": "attr0_replay_probe_low_offset",
                "chunk_len": int(len(chunk)),
            }
        else:
            score, details = scored
        row = {
            "offset": int(off),
            "offset_hex": f"0x{off:X}",
            "score_structural": int(score),
            "score": int(score),
            "compressed_bytes_consumed": int(consumed),
            "chunk_len": int(len(chunk)),
            "details": details,
            "_chunk": chunk,
        }
        candidates.append(row)

    if not candidates:
        return None

    def _candidate_rank(row: dict) -> tuple[int, int, int, int, int]:
        rp = row.get("replay_probe") if isinstance(row, dict) else None
        if not isinstance(rp, dict):
            return (-1, -1, -1, 0, int(row.get("score", 0)))
        tested = int(rp.get("events_tested", 0) or 0)
        ok = int(rp.get("events_ok", 0) or 0)
        nonnoop = int(rp.get("events_nonnoop", 0) or 0)
        bad = rp.get("bad_reasons") or {}
        fatal = 0
        total_bad = 0
        if isinstance(bad, dict):
            fatal = (
                int(bad.get("frame_dims_implausible", 0) or 0)
                + int(bad.get("first_record_oob", 0) or 0)
                + int(bad.get("220c_compose_failed", 0) or 0)
            )
            total_bad = sum(int(v or 0) for v in bad.values())
        # Primary: more real queue events decoded; secondary: fewer fatal failures; tertiary: score.
        return (ok, nonnoop, tested, -fatal - total_bad, int(row.get("score", 0)))

    # Refine with actual 3670 queue-event replay score on top structural candidates.
    candidates.sort(key=lambda r: int(r["score_structural"]), reverse=True)
    if sample_events:
        probe_cap = 48
        if any((int(a) & 0xFF) == 0 for a in attrs):
            # attr=0 queue events are highly discriminative and can be missed by purely structural ranking;
            # probe a wider candidate set so early offsets like MONxx@0x12 are not pruned too early.
            probe_cap = 256
        probe_rows: list[dict] = []
        seen_ids: set[int] = set()

        def _add_probe_rows(rows: list[dict]) -> None:
            for r in rows:
                rid = id(r)
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                probe_rows.append(r)

        # Probe top structural candidates, but also preserve low-offset candidates which often represent
        # true 1D25 seek0(+small-header) chunks and can rank poorly structurally.
        _add_probe_rows(candidates[: min(probe_cap, len(candidates))])
        low_offset_rows = sorted(candidates, key=lambda r: int(r.get("offset", 0)))[: min(probe_cap, len(candidates))]
        _add_probe_rows(low_offset_rows)

        def _is_attr0_placeholder_event(ev: dict) -> bool:
            try:
                return (
                    (int(ev.get("attr", 0)) & 0xFF) == 0
                    and int(ev.get("x", 0)) <= -64
                    and int(ev.get("y", 0)) == 0
                )
            except Exception:
                return False

        for row in probe_rows:
            comp = _RGBACompositor()
            replay_ok = 0
            replay_nonnoop = 0
            replay_pixels = 0
            replay_bad = Counter()
            probe_events = [ev for ev in sample_events if isinstance(ev, dict) and not _is_attr0_placeholder_event(ev)]
            if not probe_events:
                probe_events = [ev for ev in sample_events if isinstance(ev, dict)]
            probe_events = probe_events[: min(24, len(probe_events))]
            for ev in probe_events:
                rr = _render_3670_event_real(
                    chunk=bytes(row["_chunk"]),
                    type_idx=int(ev["type_index"]),
                    attr=int(ev["attr"]),
                    x=int(ev["x"]),
                    y=int(ev["y"]),
                    clip_left=int(ev["clip_left"]),
                    clip_right=int(ev["clip_right"]),
                    flags1=int(ev["flags1"]),
                    flags2=int(ev["flags2"]),
                    compositor=comp,
                )
                if rr.get("ok"):
                    replay_ok += 1
                    if not rr.get("noop"):
                        replay_nonnoop += 1
                        replay_pixels += int(rr.get("pixels_drawn", 0))
                else:
                    replay_bad[str(rr.get("reason"))] += 1
            row["replay_probe"] = {
                "events_tested": int(len(probe_events)),
                "events_ok": int(replay_ok),
                "events_nonnoop": int(replay_nonnoop),
                "events_noop": int(max(0, replay_ok - replay_nonnoop)),
                "pixels_drawn": int(replay_pixels),
                "bad_reasons": dict(replay_bad),
            }
            # Prefer structural validity on real queue events over raw pixel count; bad frame/record
            # decodes are often junk chunks that happen to overdraw.
            row["score"] = _score_3670_replay_candidate(
                int(row["score_structural"]),
                int(replay_ok),
                int(replay_nonnoop),
                int(replay_pixels),
                replay_bad,
            )
    best = max(candidates, key=_candidate_rank)
    return best


def _render_3670_event_real(
    *,
    chunk: bytes,
    type_idx: int,
    attr: int,
    x: int,
    y: int,
    clip_left: int,
    clip_right: int,
    flags1: int,
    flags2: int,
    compositor: _RGBACompositor,
) -> dict:
    def _ctx(**extra) -> dict:
        base = {
            "type_index": int(type_idx),
            "attr": int(attr),
            "x": int(x),
            "y": int(y),
            "clip_left": int(clip_left),
            "clip_right": int(clip_right),
        }
        base.update(extra)
        return base
    # Current queue path target is flags1=0, flags2=0. We preserve trace for unsupported flags.
    if flags1 != 0 or flags2 != 0:
        return _ctx(
            **{
            "ok": False,
            "reason": "unsupported_flags",
            "flags1": int(flags1),
            "flags2": int(flags2),
        })
    attr_byte = int(attr) & 0xFF
    first_rec = (((attr_byte - 1) & 0xFF) * 0x18)
    if first_rec + 0x18 > len(chunk):
        if attr_byte == 0:
            # Queue consumer attr streams are packed as {attr,0}. For attr=0 the command stream
            # terminates immediately after the initial descriptor lookup, so the event is visually
            # a no-op even though 1D94 still probes descriptor 0xFF for frame dims first.
            # MON-backed chunks frequently have missing/garbage record 0xFF descriptors (see
            # scratch/analyze_mon_record255_descriptors.py), so treat this as a guarded no-op
            # instead of a hard failure during queue replay candidate scoring.
            return _ctx(ok=True, noop="attr0_record255_unavailable", record_off=int(first_rec))
        return _ctx(ok=False, reason="first_record_oob", record_off=int(first_rec))
    frame_w = int(chunk[first_rec + 2])
    frame_h = int(chunk[first_rec + 3])
    if frame_w > 64 or frame_h > 64:
        if attr_byte == 0:
            return _ctx(
                ok=True,
                noop="attr0_record255_implausible_dims",
                frame_w=int(frame_w),
                frame_h=int(frame_h),
                record_off=int(first_rec),
            )
        return _ctx(
            **{
            "ok": False,
            "reason": "frame_dims_implausible",
            "frame_w": int(frame_w),
            "frame_h": int(frame_h),
            "record_off": int(first_rec),
        })
    if frame_w <= 0 or frame_h <= 0:
        return _ctx(ok=True, noop="frame_zero_dims", frame_w=int(frame_w), frame_h=int(frame_h))

    scratch = _Scratch220C(frame_w, frame_h)
    # Queue consumer non-0xFF path passes a local one-byte attr + zero terminator.
    comp = scratch.compose_command(chunk, attr_cmd=int(attr), flags1=int(flags1))
    if not comp.get("ok"):
        return _ctx(ok=False, reason="220c_compose_failed", compose=comp)
    sprite = scratch.to_rgba()
    pixels = compositor.blit_sprite(
        sprite,
        x=int(x),
        y=int(y),
        clip_left=int(clip_left),
        clip_right=int(clip_right),
    )
    alpha_bbox = _sprite_alpha_bbox(sprite)
    out = _ctx(
        **{
        "ok": True,
        "frame_w_cells": int(frame_w),
        "frame_h_cells": int(frame_h),
        "sprite_size": [int(sprite.size[0]), int(sprite.size[1])],
        "alpha_bbox": list(alpha_bbox) if alpha_bbox else None,
        "pixels_drawn": int(pixels),
        "compose": comp,
    })
    if int(pixels) == 0:
        out["noop"] = "pixels_drawn_zero"
        if alpha_bbox is None:
            out["zero_reason_guess"] = "sprite_alpha_empty"
        else:
            ax0, ay0, ax1, ay1 = alpha_bbox
            wx0 = int(x) + ax0
            wy0 = int(y) + ay0
            wx1 = int(x) + ax1
            wy1 = int(y) + ay1
            x_overlap = _wrapped_horizontal_intersection_len(wx0, wx1, int(clip_left), int(clip_right))
            y_overlap = max(0, min(200, wy1) - max(0, wy0))
            out["alpha_world_bbox"] = [int(wx0), int(wy0), int(wx1), int(wy1)]
            out["zero_overlap_estimate"] = {"x_overlap": int(x_overlap), "y_overlap": int(y_overlap)}
            if x_overlap <= 0 or y_overlap <= 0:
                out["zero_reason_guess"] = "alpha_bbox_outside_clip_or_screen"
            else:
                out["zero_reason_guess"] = "alpha_bbox_inside_clip_but_no_visible_pixels"
    return out

def render_estimated_queue_3670_events(
    *,
    events: list[dict],
    gamedata_dir: Path | None = None,
    prefer_exact_1d25_mon_seek0: bool = False,
    allow_mon_runtime_sources: bool = True,
    overlay_debug_markers: bool = True,
) -> tuple[Image.Image | None, dict]:
    maze_bytes: bytes | None = None
    source_blobs: dict[str, bytes] = {}
    if gamedata_dir is not None:
        p = Path(gamedata_dir) / "MAZEDATA.EGA"
        if p.exists():
            try:
                maze_bytes = p.read_bytes()
                source_blobs["MAZEDATA.EGA"] = maze_bytes
            except Exception:
                maze_bytes = None
    mon_loader_type_maps = _load_known_mon_loader_type_maps()
    mon_type_chunk_args = _load_mon_type_chunk_args()
    likely_premaze_sources = _load_likely_premaze_mon_sources()
    img = Image.new("RGBA", (320, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    compositor = _RGBACompositor()

    total = 0
    resolved_scalar = 0
    marker_drawn = 0
    marker_x_out_of_view = 0
    real_rendered = 0
    real_ok_noop = 0
    real_nonnoop = 0
    real_pixels_drawn = 0
    unresolved = Counter()
    type_counts = Counter()
    trace: list[dict] = []
    real_trace: list[dict] = []
    type_chunks: dict[int, dict] = {}
    type_attrs_seen: dict[int, set[int]] = {}
    type_scalar_sample_events: dict[int, list[dict]] = {}

    # Pre-scan scalar 3670 events to build per-type attr sets for chunk recovery.
    for ev in events:
        if str(ev.get("driver_wrapper")) != "0x3670":
            continue
        sem = ev.get("likely_3670_semantics")
        if not isinstance(sem, dict):
            continue
        ti = _as_int(sem.get("type_index"))
        at = _as_int(ev.get("attr"))
        f1 = _as_int(sem.get("flags1"))
        f2 = _as_int(sem.get("flags2"))
        if None in (ti, at, f1, f2):
            continue
        if int(f1) != 0 or int(f2) != 0:
            continue
        tnorm = int(ti) & 0xFF
        type_attrs_seen.setdefault(tnorm, set()).add(int(at) & 0xFF)
        x = _as_int(sem.get("x"))
        y = _as_int(sem.get("y"))
        cl = _as_int(sem.get("clip_left"))
        cr = _as_int(sem.get("clip_right"))
        if None not in (x, y, cl, cr):
            type_scalar_sample_events.setdefault(tnorm, []).append(
                {
                    "type_index": tnorm,
                    "attr": int(at) & 0xFF,
                    "x": _signed16(int(x)),
                    "y": _signed16(int(y)),
                    "clip_left": _signed16(int(cl)),
                    "clip_right": _signed16(int(cr)),
                    "flags1": int(f1) & 0xFFFF,
                    "flags2": int(f2) & 0xFFFF,
                }
            )

    if source_blobs:
        def _cross_source_candidate_rank(row: dict) -> tuple[int, int, int, int, int, int]:
            rp = row.get("replay_probe") if isinstance(row, dict) else None
            if not isinstance(rp, dict):
                return (-1, -1, -1, 0, 0, int(row.get("score", 0)))
            tested = int(rp.get("events_tested", 0) or 0)
            ok = int(rp.get("events_ok", 0) or 0)
            nonnoop = int(rp.get("events_nonnoop", 0) or 0)
            bad = rp.get("bad_reasons") or {}
            fatal = 0
            total_bad = 0
            if isinstance(bad, dict):
                fatal = (
                    int(bad.get("frame_dims_implausible", 0) or 0)
                    + int(bad.get("first_record_oob", 0) or 0)
                    + int(bad.get("220c_compose_failed", 0) or 0)
                )
                total_bad = sum(int(v or 0) for v in bad.values())
            source_mode = str(row.get("source_mode", ""))
            exact_bonus = 1 if source_mode.startswith("direct_1d25_seek0_from_") else 0
            return (ok, nonnoop, tested, -fatal - total_bad, exact_bonus, int(row.get("score", 0)))

        for t_idx, attrs in sorted(type_attrs_seen.items()):
            candidates_across_sources: list[dict] = []
            # Baseline heuristic source.
            if maze_bytes is not None:
                cand = _find_best_type_chunk_rle_offset(
                    maze_bytes,
                    attrs=attrs,
                    sample_events=type_scalar_sample_events.get(t_idx),
                    scan_start=0x800,
                )
                if cand is not None:
                    cand = dict(cand)
                    cand["source_file"] = "MAZEDATA.EGA"
                    candidates_across_sources.append(cand)
            # Runtime-informed WINIT bridge: some driver `type`s are staged from MONxx.PIC via `0x4721 -> 0x3664`.
            mon_specs = mon_loader_type_maps.get(int(t_idx), [])
            if allow_mon_runtime_sources and mon_specs and gamedata_dir is not None:
                for mon_spec in mon_specs:
                    mon_rec = int(mon_spec.get("record_index", -1))
                    if mon_rec < 0:
                        continue
                    mon_name = f"MON{int(mon_rec):02d}.PIC"
                    mon_path = Path(gamedata_dir) / mon_name
                    if not mon_path.exists():
                        continue
                    try:
                        mon_bytes = source_blobs.get(mon_name)
                        if mon_bytes is None:
                            mon_bytes = mon_path.read_bytes()
                            source_blobs[mon_name] = mon_bytes
                        source_helper = str(mon_spec.get("source_helper", "unknown"))
                        source_helper_tag = source_helper.lower().replace(":", "_").replace("0x", "")
                        probe_events = type_scalar_sample_events.get(t_idx) or []

                        # Disassembly-faithful first attempt for *4721-like clone -> WROOT:0x3664 -> EGA:0x1D25:
                        # common EGA path seeks arg2/arg3 = 0, so decode the resource stream from file offset 0.
                        chunk0, consumed0 = _decode_1d25_rle_stream(mon_bytes, 0)
                        if chunk0 is not None:
                            scored0 = _score_type_chunk_candidate(chunk0, attrs=attrs)
                            if scored0 is not None:
                                score0, details0 = scored0
                                row0 = {
                                    "offset": 0,
                                    "offset_hex": "0x0",
                                    "score_structural": int(score0),
                                    "score": int(score0),
                                    "compressed_bytes_consumed": int(consumed0),
                                    "chunk_len": int(len(chunk0)),
                                    "details": details0,
                                    "_chunk": chunk0,
                                    "source_file": mon_name,
                                    "source_mode": f"direct_1d25_seek0_from_{source_helper_tag}",
                                    "source_helper": source_helper,
                                }
                                # Reuse replay probing logic by scoring this row inline when sample events exist.
                                if probe_events:
                                    comp = _RGBACompositor()
                                    replay_ok = 0
                                    replay_nonnoop = 0
                                    replay_pixels = 0
                                    replay_bad = Counter()
                                    max_probe_events = min(24, len(probe_events))
                                    for ev in probe_events[:max_probe_events]:
                                        rr = _render_3670_event_real(
                                            chunk=bytes(chunk0),
                                            type_idx=int(ev["type_index"]),
                                            attr=int(ev["attr"]),
                                            x=int(ev["x"]),
                                            y=int(ev["y"]),
                                            clip_left=int(ev["clip_left"]),
                                            clip_right=int(ev["clip_right"]),
                                            flags1=int(ev["flags1"]),
                                            flags2=int(ev["flags2"]),
                                            compositor=comp,
                                        )
                                        if rr.get("ok"):
                                            replay_ok += 1
                                            if not rr.get("noop"):
                                                replay_nonnoop += 1
                                                replay_pixels += int(rr.get("pixels_drawn", 0))
                                        else:
                                            replay_bad[str(rr.get("reason"))] += 1
                                    row0["replay_probe"] = {
                                        "events_tested": int(max_probe_events),
                                        "events_ok": int(replay_ok),
                                        "events_nonnoop": int(replay_nonnoop),
                                        "events_noop": int(max(0, replay_ok - replay_nonnoop)),
                                        "pixels_drawn": int(replay_pixels),
                                        "bad_reasons": dict(replay_bad),
                                    }
                                    row0["score"] = _score_3670_replay_candidate(
                                        int(row0["score_structural"]),
                                        int(replay_ok),
                                        int(replay_nonnoop),
                                        int(replay_pixels),
                                        replay_bad,
                                    )
                                candidates_across_sources.append(row0)
                        # Metadata-driven candidate from opcode-8 type record words 0x36E2/0x36E4.
                        tmeta = mon_type_chunk_args.get(int(t_idx))
                        if isinstance(tmeta, dict):
                            mw = tmeta.get("metadata_words") or {}
                            w36e2 = mw.get("36E2_word")
                            w36e4 = mw.get("36E4_word")
                            try:
                                lo = int(str(w36e2), 16) if isinstance(w36e2, str) else None
                                hi = int(str(w36e4), 16) if isinstance(w36e4, str) else None
                            except Exception:
                                lo = None
                                hi = None
                            if lo is not None and hi is not None:
                                off_meta = ((int(hi) & 0xFFFF) << 16) | (int(lo) & 0xFFFF)
                                if 0 <= off_meta < len(mon_bytes):
                                    chunkm, consumedm = _decode_1d25_rle_stream(mon_bytes, off_meta)
                                    if chunkm is not None:
                                        scoredm = _score_type_chunk_candidate(chunkm, attrs=attrs)
                                        if scoredm is not None:
                                            scorem, detailsm = scoredm
                                            rowm = {
                                                "offset": int(off_meta),
                                                "offset_hex": f"0x{int(off_meta):X}",
                                                "score_structural": int(scorem),
                                                "score": int(scorem),
                                                "compressed_bytes_consumed": int(consumedm),
                                                "chunk_len": int(len(chunkm)),
                                                "details": detailsm,
                                                "_chunk": chunkm,
                                                "source_file": mon_name,
                                                "source_mode": "direct_1d25_seek_from_opcode8_metadata_36e2_36e4",
                                                "source_helper": source_helper,
                                                "source_metadata_36e2": w36e2,
                                                "source_metadata_36e4": w36e4,
                                            }
                                            if probe_events:
                                                comp = _RGBACompositor()
                                                replay_ok = 0
                                                replay_nonnoop = 0
                                                replay_pixels = 0
                                                replay_bad = Counter()
                                                max_probe_events = min(24, len(probe_events))
                                                for ev in probe_events[:max_probe_events]:
                                                    rr = _render_3670_event_real(
                                                        chunk=bytes(chunkm),
                                                        type_idx=int(ev["type_index"]),
                                                        attr=int(ev["attr"]),
                                                        x=int(ev["x"]),
                                                        y=int(ev["y"]),
                                                        clip_left=int(ev["clip_left"]),
                                                        clip_right=int(ev["clip_right"]),
                                                        flags1=int(ev["flags1"]),
                                                        flags2=int(ev["flags2"]),
                                                        compositor=comp,
                                                    )
                                                    if rr.get("ok"):
                                                        replay_ok += 1
                                                        if not rr.get("noop"):
                                                            replay_nonnoop += 1
                                                            replay_pixels += int(rr.get("pixels_drawn", 0))
                                                    else:
                                                        replay_bad[str(rr.get("reason"))] += 1
                                                rowm["replay_probe"] = {
                                                    "events_tested": int(max_probe_events),
                                                    "events_ok": int(replay_ok),
                                                    "events_nonnoop": int(replay_nonnoop),
                                                    "events_noop": int(max(0, replay_ok - replay_nonnoop)),
                                                    "pixels_drawn": int(replay_pixels),
                                                    "bad_reasons": dict(replay_bad),
                                                }
                                                rowm["score"] = _score_3670_replay_candidate(
                                                    int(rowm["score_structural"]),
                                                    int(replay_ok),
                                                    int(replay_nonnoop),
                                                    int(replay_pixels),
                                                    replay_bad,
                                                )
                                            candidates_across_sources.append(rowm)
                        cand_mon = _find_best_type_chunk_rle_offset(
                            mon_bytes,
                            attrs=attrs,
                            sample_events=type_scalar_sample_events.get(t_idx),
                            scan_start=0,
                        )
                        if cand_mon is not None:
                            cand_mon = dict(cand_mon)
                            cand_mon["source_file"] = mon_name
                            cand_mon["source_mode"] = "heuristic_rle_scan"
                            cand_mon["source_helper"] = source_helper
                            candidates_across_sources.append(cand_mon)
                    except Exception:
                        pass
            cand = None
            if candidates_across_sources:
                cand = max(candidates_across_sources, key=_cross_source_candidate_rank)
                if prefer_exact_1d25_mon_seek0:
                    prem = likely_premaze_sources.get(int(t_idx))
                    prem_mon = None
                    prem_helper = None
                    if isinstance(prem, dict):
                        prem_mon = prem.get("mon_file")
                        prem_helper = prem.get("helper")
                    if isinstance(prem_mon, str):
                        exact_candidates = [
                            r
                            for r in candidates_across_sources
                            if str(r.get("source_file")) == prem_mon
                            and str(r.get("source_mode", "")).startswith("direct_1d25_seek0_from_")
                        ]
                        if exact_candidates:
                            exact_best = max(exact_candidates, key=_cross_source_candidate_rank)
                            cand_rank = _cross_source_candidate_rank(cand) if isinstance(cand, dict) else (-1, -1, 0, 0, -10**9)
                            exact_rank = _cross_source_candidate_rank(exact_best)
                            # Do not force the exact seek0 candidate if it materially degrades real queue replay.
                            # This preserves the debugging intent of the flag while avoiding known-bad underdraw paths.
                            if exact_rank >= cand_rank:
                                cand = dict(exact_best)
                                cand["_selection_override"] = {
                                    "reason": "prefer_exact_1d25_mon_seek0",
                                    "likely_premaze_source": prem_mon,
                                    "likely_premaze_helper": prem_helper,
                                }
                            else:
                                if isinstance(cand, dict):
                                    cand["_selection_override"] = {
                                        "reason": "prefer_exact_1d25_mon_seek0_suppressed_due_to_replay_validity",
                                        "likely_premaze_source": prem_mon,
                                        "likely_premaze_helper": prem_helper,
                                        "exact_candidate_rank": list(exact_rank),
                                        "selected_candidate_rank": list(cand_rank),
                                    }
            if cand is None:
                type_chunks[t_idx] = {"ok": False, "reason": "no_rle_candidate", "attrs": sorted(attrs)}
            else:
                type_chunks[t_idx] = {
                    "ok": True,
                    "attrs": sorted(attrs),
                    "best_offset": cand["offset"],
                    "best_offset_hex": cand["offset_hex"],
                    "score": cand["score"],
                    "source_file": cand.get("source_file", "MAZEDATA.EGA"),
                    "source_mode": cand.get("source_mode", "heuristic_rle_scan"),
                    "source_helper": cand.get("source_helper"),
                    "compressed_bytes_consumed": cand["compressed_bytes_consumed"],
                    "chunk_len": cand["chunk_len"],
                    "details": cand["details"],
                    "replay_probe": cand.get("replay_probe"),
                    "selection_override": cand.get("_selection_override"),
                    "_chunk": cand["_chunk"],
                }

    for ev in events:
        if str(ev.get("driver_wrapper")) != "0x3670":
            continue
        total += 1
        sem = ev.get("likely_3670_semantics")
        if not isinstance(sem, dict):
            unresolved.update(["missing_semantics"])
            trace.append({"queue_index": ev.get("queue_index"), "reason": "missing_semantics"})
            continue

        type_idx = _as_int(sem.get("type_index"))
        x = _as_int(sem.get("x"))
        y = _as_int(sem.get("y"))
        clip_left = _as_int(sem.get("clip_left"))
        clip_right = _as_int(sem.get("clip_right"))
        flags1 = _as_int(sem.get("flags1"))
        flags2 = _as_int(sem.get("flags2"))
        attr = _as_int(ev.get("attr"))

        missing = []
        if type_idx is None:
            missing.append("type_index")
        if x is None:
            missing.append("x")
        if y is None:
            missing.append("y")
        if clip_left is None:
            missing.append("clip_left")
        if clip_right is None:
            missing.append("clip_right")
        if flags1 is None:
            missing.append("flags1")
        if flags2 is None:
            missing.append("flags2")
        if attr is None:
            missing.append("attr")
        if missing:
            for m in missing:
                unresolved.update([f"symbolic_{m}"])
            trace.append(
                {
                    "queue_index": ev.get("queue_index"),
                    "phase": ev.get("phase"),
                    "status": "symbolic",
                    "missing": missing,
                    "raw_semantics": sem,
                    "raw_attr": ev.get("attr"),
                }
            )
            continue

        type_idx = int(type_idx) & 0xFF
        attr = int(attr) & 0xFF
        x_s = _signed16(int(x))
        y_s = _signed16(int(y))
        cl_s = _signed16(int(clip_left))
        cr_s = _signed16(int(clip_right))
        f1 = int(flags1) & 0xFFFF
        f2 = int(flags2) & 0xFFFF

        type_counts.update([f"type_{type_idx}"])
        resolved_scalar += 1

        # Queue consumer path currently expected to use flags1=0, flags2=0.
        if f1 != 0 or f2 != 0:
            unresolved.update(["nonzero_flags"])

        # Attempt a first real software 1D94/220C replay for the queue path (flags1=flags2=0).
        real_attempt = None
        tchunk_meta = type_chunks.get(type_idx)
        if f1 == 0 and f2 == 0 and isinstance(tchunk_meta, dict) and tchunk_meta.get("ok"):
            chunk_bytes = tchunk_meta.get("_chunk")
            if isinstance(chunk_bytes, (bytes, bytearray)):
                real_attempt = _render_3670_event_real(
                    chunk=bytes(chunk_bytes),
                    type_idx=type_idx,
                    attr=attr,
                    x=x_s,
                    y=y_s,
                    clip_left=cl_s,
                    clip_right=cr_s,
                    flags1=f1,
                    flags2=f2,
                    compositor=compositor,
                )
                real_trace.append(
                    {
                        "queue_index": ev.get("queue_index"),
                        "phase": ev.get("phase"),
                        "source": ev.get("source"),
                        **(real_attempt if isinstance(real_attempt, dict) else {"ok": False, "reason": "unknown"}),
                    }
                )
                if isinstance(real_attempt, dict) and real_attempt.get("ok"):
                    real_rendered += 1
                    if real_attempt.get("noop") or int(real_attempt.get("pixels_drawn", 0) or 0) <= 0:
                        real_ok_noop += 1
                    else:
                        real_nonnoop += 1
                        real_pixels_drawn += int(real_attempt.get("pixels_drawn", 0))
                elif isinstance(real_attempt, dict):
                    unresolved.update([f"real_{real_attempt.get('reason', 'failed')}"])
        elif f1 == 0 and f2 == 0 and type_idx in type_chunks:
            unresolved.update(["missing_type_chunk"])

        # Debug marker pass (not pixel-accurate 3670 rendering).
        color = _event_color(type_idx, attr)
        y_draw = max(0, min(199, y_s))
        x_draw = max(0, min(319, x_s))
        if not (0 <= x_s < 320):
            marker_x_out_of_view += 1
        a = max(0, min(319, cl_s))
        b = max(0, min(319, cr_s))
        if a > b:
            a, b = b, a
        if a != b:
            draw.line((a, y_draw, b, y_draw), fill=color, width=1)
            draw.line((a, max(0, y_draw - 1), a, min(199, y_draw + 1)), fill=(255, 255, 255, 160), width=1)
            draw.line((b, max(0, y_draw - 1), b, min(199, y_draw + 1)), fill=(255, 255, 255, 160), width=1)
        draw.line((x_draw, max(0, y_draw - 2), x_draw, min(199, y_draw + 2)), fill=(255, 220, 0, 200), width=1)
        marker_drawn += 1
        trace.append(
            {
                "queue_index": ev.get("queue_index"),
                "phase": ev.get("phase"),
                "status": "resolved_marker",
                "x_in_view": bool(0 <= x_s < 320),
                "type_index": type_idx,
                "attr": attr,
                "x": x_s,
                "y": y_s,
                "clip_left": cl_s,
                "clip_right": cr_s,
                "flags1": f1,
                "flags2": f2,
                "source": ev.get("source"),
                "real_replay": real_attempt,
            }
        )

    if total == 0:
        return (
            None,
            {
                "ok": True,
                "events_total_3670": 0,
                "events_resolved_scalar": 0,
                "events_marker_drawn": 0,
                "events_marker_x_out_of_view": 0,
                "events_real_replayed": 0,
                "events_real_nonnoop": 0,
                "events_real_noop": 0,
                "real_pixels_drawn": 0,
                "unresolved_breakdown": {},
                "type_counts": {},
                "notes": [
                    "No deferred queue 0x3670 events were present.",
                ],
            },
        )

    out_img = compositor.img if real_pixels_drawn > 0 else img
    # If both exist, optionally overlay markers on top of real replay for debugging.
    if real_pixels_drawn > 0 and overlay_debug_markers:
        try:
            out_img = Image.alpha_composite(compositor.img, img)
        except Exception:
            out_img = compositor.img

    for meta in type_chunks.values():
        if isinstance(meta, dict) and "_chunk" in meta:
            meta.pop("_chunk", None)

    return (
        out_img,
        {
            "ok": True,
            "events_total_3670": int(total),
            "events_resolved_scalar": int(resolved_scalar),
            "events_marker_drawn": int(marker_drawn),
            "events_marker_x_out_of_view": int(marker_x_out_of_view),
            "events_real_replayed": int(real_rendered),
            "events_real_nonnoop": int(real_nonnoop),
            "events_real_noop": int(real_ok_noop),
            "real_pixels_drawn": int(real_pixels_drawn),
            "unresolved_breakdown": {k: int(v) for k, v in sorted(unresolved.items())},
            "type_counts": {k: int(v) for k, v in sorted(type_counts.items())},
            "type_chunk_candidates": {f"type_{k}": v for k, v in sorted(type_chunks.items())},
            "trace": trace,
            "real_trace": real_trace,
            "notes": [
                "Hybrid deferred queue 0x3670 replay: attempts a first software 1D94/220C-style decode for flags1=0/flags2=0 events using heuristic 1D25 RLE chunk recovery from MAZEDATA.EGA, with marker fallback retained.",
                "Markers show y row + clip span (white clip ticks) + x anchor (yellow tick) for scalar events and are overlaid on the real replay image when real replay succeeds.",
                "Current queue reconstruction may recover some x values from static WROOT image tables for specific 0x85D0/0x84F1 callsites; runtime-initialized table differences can still shift these.",
                "The 3670 real replay path currently targets queue-consumer usage (single-byte attr stream, flags1=0, flags2=0) and does not yet emulate all 1D94 transforms/hardware modes exactly.",
                "Optional strict mode (`prefer_exact_1d25_mon_seek0`) prefers disassembly-faithful MONxx seek=0 loader candidates for likely pre-maze type slots over heuristic intra-file RLE rescans.",
                "Optional `allow_mon_runtime_sources=False` limits chunk recovery to MAZEDATA-only heuristics, which is safer for live WMAZE rendering while MON-backed overwrite timing remains unresolved.",
                "Optional `overlay_debug_markers=False` returns only the real replay layer (no marker overlay), which is preferred for compositing into prototype viewport output.",
            ],
        },
    )


