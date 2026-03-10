from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from bane.data.sprite_decoder import DEFAULT_16_PALETTE, TITLEPAG_PALETTE


MAZEDATA_GRAYSCALE_PALETTE: list[tuple[int, int, int]] = [
    (i * 17, i * 17, i * 17) for i in range(16)
]


def _u16le(buf: bytes, off: int) -> int:
    return int.from_bytes(buf[off : off + 2], "little")


def _bit_reverse8(v: int) -> int:
    v &= 0xFF
    v = ((v & 0xF0) >> 4) | ((v & 0x0F) << 4)
    v = ((v & 0xCC) >> 2) | ((v & 0x33) << 2)
    v = ((v & 0xAA) >> 1) | ((v & 0x55) << 1)
    return v & 0xFF


def _parse_5byte_table(buf: bytes, off: int, count: int) -> list[tuple[int, int, int, int, int]]:
    out: list[tuple[int, int, int, int, int]] = []
    for i in range(count):
        p = off + i * 5
        if p + 5 > len(buf):
            break
        w = _u16le(buf, p)
        out.append((w, buf[p + 2], buf[p + 3], buf[p + 4], buf[p + 0]))  # include raw b0 alias in slot 4
    return out


@dataclass
class EGA36ACTables:
    source_path: str
    maze_bytes: bytes
    hdr_count: int
    hdr_table_18e_off: int
    hdr_table_190_off: int
    hdr_recs_18e_unpatched: list[tuple[int, int, int, int, int]]
    hdr_recs_190: list[tuple[int, int, int, int, int]]
    drv_recs_18e_patched: list[tuple[int, int, int, int, int]]
    hdr_recs_190_count_declared: int

    @classmethod
    def load(cls, *, mazedata_ega: Path, ega_drv: Path) -> "EGA36ACTables":
        maze = mazedata_ega.read_bytes()
        return cls.load_from_bytes(source_bytes=maze, source_path=str(mazedata_ega), ega_drv=ega_drv)

    @classmethod
    def load_from_descriptor_file(cls, *, descriptor_file: Path, ega_drv: Path) -> "EGA36ACTables":
        return cls.load_from_bytes(source_bytes=descriptor_file.read_bytes(), source_path=str(descriptor_file), ega_drv=ega_drv)

    @classmethod
    def load_from_bytes(cls, *, source_bytes: bytes, source_path: str, ega_drv: Path) -> "EGA36ACTables":
        maze = source_bytes
        drv = ega_drv.read_bytes()
        mem = bytearray(maze)
        count = _u16le(mem, 0x0000)
        word1 = _u16le(mem, 0x0002)
        hdr_table_190 = count * 5 + 4
        # EGA.DRV cs:[0x18E]/cs:[0x190] are pointer words into the MAZEDATA descriptor
        # header buffer (DS=cs:[0x149]) after 0x0731 loads it, not inline tables in EGA.DRV.
        ptr18e_off = int.from_bytes(drv[0x018E - 0x0100 : 0x0190 - 0x0100], "little")
        hdr_before_patch = bytes(mem[:0x800])
        ax = (word1 * 5 + hdr_table_190) & 0xFFFF
        low_nibble_adj = ax & 0x000F
        seg_add = (ax >> 4) & 0xFFFF
        for i in range(count):
            p = ptr18e_off + i * 5
            if p + 5 > len(mem):
                break
            al = (mem[p + 2] + low_nibble_adj) & 0xFF
            mem[p + 2] = al & 0x0F
            hi = (al >> 4) & 0xFF
            w = int.from_bytes(mem[p : p + 2], "little")
            w = (w + hi + seg_add) & 0xFFFF
            mem[p : p + 2] = w.to_bytes(2, "little")

        hdr_recs_18e_unpatched = _parse_5byte_table(hdr_before_patch, ptr18e_off, count)
        # 0x0B93 indexes table 0x190 without checking against header word0. Model this against the
        # full loaded descriptor buffer (not only the first 0x800 bytes) so high ids (e.g. 0x159)
        # can resolve when records spill past the header page.
        hdr_recs_190 = _parse_5byte_table(bytes(mem), hdr_table_190, max(0, (len(mem) - hdr_table_190) // 5))
        drv_recs_18e_patched = _parse_5byte_table(bytes(mem), ptr18e_off, count)
        return cls(
            source_path=source_path,
            maze_bytes=maze,
            hdr_count=count,
            hdr_table_18e_off=ptr18e_off,
            hdr_table_190_off=hdr_table_190,
            hdr_recs_18e_unpatched=hdr_recs_18e_unpatched,
            hdr_recs_190=hdr_recs_190,
            drv_recs_18e_patched=drv_recs_18e_patched,
            hdr_recs_190_count_declared=count,
        )


class EGA36ACPlanarBuffer:
    WIDTH = 320
    HEIGHT = 200
    BYTES_PER_ROW = 40
    PLANE_SIZE = BYTES_PER_ROW * HEIGHT
    TOTAL_SIZE = PLANE_SIZE * 4

    def __init__(self) -> None:
        self.buf = bytearray(self.TOTAL_SIZE)

    def _write_byte(self, off: int, val: int, *, or_mode: bool) -> None:
        if not (0 <= off < len(self.buf)):
            return
        if or_mode:
            self.buf[off] |= val & 0xFF
        else:
            self.buf[off] = val & 0xFF

    def to_rgba_image(self, *, transparent_zero: bool = True) -> Image.Image:
        out = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (0, 0, 0, 0))
        px = out.load()
        for y in range(self.HEIGHT):
            row = y * self.BYTES_PER_ROW
            for xb in range(self.BYTES_PER_ROW):
                p0 = self.buf[row + xb]
                p1 = self.buf[self.PLANE_SIZE + row + xb]
                p2 = self.buf[self.PLANE_SIZE * 2 + row + xb]
                p3 = self.buf[self.PLANE_SIZE * 3 + row + xb]
                for bit in range(8):
                    x = xb * 8 + (7 - bit)
                    mask = 1 << bit
                    idx = ((1 if (p0 & mask) else 0)
                           | ((1 if (p1 & mask) else 0) << 1)
                           | ((1 if (p2 & mask) else 0) << 2)
                           | ((1 if (p3 & mask) else 0) << 3))
                    if idx == 0 and transparent_zero:
                        continue
                    rr, gg, bb = MAZEDATA_GRAYSCALE_PALETTE[idx]
                    px[x, y] = (rr, gg, bb, 255)
        return out

def _resolve_file_src_segment_window(maze_bytes: bytes, seg_para: int) -> int | None:
    # 0x0B93 sets DS = cs:[0x149] (descriptor header segment), then DS += table.word0.
    # 0x0731 loads descriptor payload starting at header+0x800, i.e. segment delta +0x80.
    candidates = [0x800 + (((int(seg_para) & 0xFFFF) - 0x80) << 4)]
    # Fallbacks kept for robustness while broader runtime-state mapping is incomplete.
    candidates.extend(
        [
            (((int(seg_para) & 0xFFFF) << 4) - 0x800),
            ((int(seg_para) & 0xFFFF) << 4),
        ]
    )
    for base in candidates:
        if 0 <= int(base) < len(maze_bytes):
            return int(base)
    return None


def _emulate_36ac_single_desc(
    planar: EGA36ACPlanarBuffer,
    tables: EGA36ACTables,
    *,
    desc_idx: int,
    mode_or_attr: int,
) -> dict:
    if (int(desc_idx) & 0xFFFF) == 0xFFFF:
        return {"ok": True, "desc_idx": int(desc_idx) & 0xFFFF, "noop": "desc_idx_sentinel_minus1"}
    if not (0 <= int(desc_idx) < len(tables.hdr_recs_190)):
        return {"ok": False, "reason": "desc_idx_range", "desc_idx": int(desc_idx)}
    h_w, h_b2, h_b3, h_b4, _h_b0 = tables.hdr_recs_190[int(desc_idx)]
    # Header record fields as used by EGA.DRV:0x0B93 single-descriptor branch:
    # [si+0]=secondary descriptor table index, [si+1]=x byte, [si+2]=y row, [si+3]=x bias, [si+4]=repeat rows.
    tbl_idx = h_w & 0xFF
    x_byte = (h_w >> 8) & 0xFF
    y_row = int(h_b2)
    x_bias = int(h_b3)
    repeat_rows = int(h_b4)
    if repeat_rows <= 0:
        return {"ok": True, "desc_idx": int(desc_idx), "noop": "repeat_rows_zero"}
    if not (0 <= tbl_idx < len(tables.drv_recs_18e_patched)):
        return {"ok": False, "reason": "tbl_idx_range", "desc_idx": int(desc_idx), "tbl_idx": tbl_idx}

    p_w, p_b2, p_b3, p_b4, _ = tables.drv_recs_18e_patched[tbl_idx]
    seg_para = int(p_w)
    src_off_base = int(p_b2)
    width_bytes = int(p_b3)
    plane_rows = int(p_b4)
    if width_bytes <= 0 or plane_rows <= 0:
        return {"ok": True, "desc_idx": int(desc_idx), "noop": "width_or_plane_rows_zero"}

    plane_stride = width_bytes * plane_rows
    src_off = (src_off_base + x_bias) & 0xFFFF
    dst_off = x_byte + x_bias + y_row * planar.BYTES_PER_ROW
    # 0x0B93 uses header.byte4 as the per-row copy width and table.byte4 as the
    # outer row count. table.byte3 is the source row stride.
    copy_width_bytes = repeat_rows
    row_count = plane_rows
    max_span = max(0, row_count - 1) * width_bytes + max(0, 3) * plane_stride + max(0, copy_width_bytes)
    src_seg_window = _resolve_file_src_segment_window(tables.maze_bytes, seg_para)
    if src_seg_window is None:
        return {
            "ok": False,
            "reason": "src_segment_window_unmapped",
            "desc_idx": int(desc_idx),
            "seg_para": f"0x{seg_para:04X}",
            "src_off": int(src_off),
            "span": int(max_span),
        }

    or_mode = int(mode_or_attr) != 0
    rows_drawn = 0
    bytes_copied = 0
    for row_idx in range(row_count):
        dst_row_base = dst_off + row_idx * planar.BYTES_PER_ROW
        src_row_off = (src_off + row_idx * width_bytes) & 0xFFFF
        for plane in range(4):
            plane_src_off = (src_row_off + plane * plane_stride) & 0xFFFF
            plane_dst = dst_row_base + plane * planar.PLANE_SIZE
            for i in range(copy_width_bytes):
                src_addr = src_seg_window + ((plane_src_off + i) & 0xFFFF)
                if 0 <= src_addr < len(tables.maze_bytes):
                    planar._write_byte(plane_dst + i, tables.maze_bytes[src_addr], or_mode=or_mode)
                bytes_copied += 1
        rows_drawn += 1
    return {
        "ok": True,
        "desc_idx": int(desc_idx),
        "tbl_idx": int(tbl_idx),
        "mode_or_attr": int(mode_or_attr) & 0xFFFF,
        "or_mode": bool(or_mode),
        "repeat_rows": int(repeat_rows),
        "width_bytes": int(width_bytes),
        "plane_rows": int(plane_rows),
        "copy_width_bytes": int(copy_width_bytes),
        "row_count": int(row_count),
        "rows_drawn": int(rows_drawn),
        "bytes_copied": int(bytes_copied),
        "dst_off": int(dst_off),
        "src_seg_window_base": int(src_seg_window),
    }


def _emulate_36ac_two_desc(
    planar: EGA36ACPlanarBuffer,
    tables: EGA36ACTables,
    *,
    arg1_desc: int,
    mode_or_attr: int,
    arg3_desc: int,
) -> dict:
    if ((int(arg1_desc) & 0xFFFF) == 0xFFFF) or ((int(arg3_desc) & 0xFFFF) == 0xFFFF):
        return {
            "ok": True,
            "arg1_desc": int(arg1_desc) & 0xFFFF,
            "arg3_desc": int(arg3_desc) & 0xFFFF,
            "noop": "desc_idx_sentinel_minus1",
        }
    # Exact structure from EGA.DRV:0x0CC6..0x0E27:
    # - arg1 header selects the source descriptor-table entry (via header[arg1].byte0)
    # - arg3 header supplies placement/repeat fields (x/y/xbias/repeat)
    # - source bytes are read right-to-left with XLAT bit-reversal (xlat table at cs:0x192)
    if not (0 <= int(arg1_desc) < len(tables.hdr_recs_190)):
        return {"ok": False, "reason": "arg1_desc_idx_range", "arg1_desc": int(arg1_desc)}
    if not (0 <= int(arg3_desc) < len(tables.hdr_recs_190)):
        return {"ok": False, "reason": "arg3_desc_idx_range", "arg3_desc": int(arg3_desc)}

    h1_w, h1_b2, h1_b3, h1_b4, _ = tables.hdr_recs_190[int(arg1_desc)]
    h3_w, h3_b2, h3_b3, h3_b4, _ = tables.hdr_recs_190[int(arg3_desc)]
    tbl_idx = h1_w & 0xFF
    if not (0 <= tbl_idx < len(tables.drv_recs_18e_patched)):
        return {"ok": False, "reason": "tbl_idx_range", "arg1_desc": int(arg1_desc), "tbl_idx": tbl_idx}
    repeat_rows = int(h3_b4)
    if repeat_rows <= 0:
        return {"ok": True, "arg1_desc": int(arg1_desc), "arg3_desc": int(arg3_desc), "noop": "repeat_rows_zero"}

    p_w, p_b2, p_b3, p_b4, _ = tables.drv_recs_18e_patched[tbl_idx]
    seg_para = int(p_w)
    src_off_base = int(p_b2)
    width_bytes = int(p_b3)
    plane_rows = int(p_b4)
    if width_bytes <= 0 or plane_rows <= 0:
        return {"ok": True, "arg1_desc": int(arg1_desc), "arg3_desc": int(arg3_desc), "noop": "width_or_plane_rows_zero"}

    # Placement comes from arg3 header record.
    x_byte = (h3_w >> 8) & 0xFF
    y_row = int(h3_b2)
    x_bias = int(h3_b3)
    dst_off = x_byte + x_bias + y_row * planar.BYTES_PER_ROW

    plane_stride = width_bytes * plane_rows
    # 0D3E..0D4C: src start offset = table.byte2 + (table.byte3 - 1) - hdr3.byte3
    src_off = (src_off_base + (width_bytes - 1) - x_bias) & 0xFFFF
    copy_width_bytes = repeat_rows
    row_count = plane_rows
    src_seg_window = _resolve_file_src_segment_window(tables.maze_bytes, seg_para)
    if src_seg_window is None:
        return {
            "ok": False,
            "reason": "src_segment_window_unmapped",
            "arg1_desc": int(arg1_desc),
            "arg3_desc": int(arg3_desc),
            "seg_para": f"0x{seg_para:04X}",
            "src_off": int(src_off),
        }

    or_mode = int(mode_or_attr) != 0
    rows_drawn = 0
    bytes_copied = 0
    # Inner copy loops mirror single-branch structure, but per-byte source access is reversed
    # (SI decremented each byte) and transformed via xlat bit-reversal.
    for row_idx in range(row_count):
        dst_row_base = dst_off + row_idx * planar.BYTES_PER_ROW
        src_row_off = (src_off + row_idx * width_bytes) & 0xFFFF
        for plane in range(4):
            plane_src_off = (src_row_off + plane * plane_stride) & 0xFFFF
            plane_dst = dst_row_base + plane * planar.PLANE_SIZE
            for i in range(copy_width_bytes):
                # 0D66/0DC4 paths read [si], then dec si (right-to-left source traversal)
                cur_src_off = (plane_src_off - i) & 0xFFFF
                src_addr = src_seg_window + cur_src_off
                if 0 <= src_addr < len(tables.maze_bytes):
                    b = _bit_reverse8(tables.maze_bytes[src_addr])
                    planar._write_byte(plane_dst + i, b, or_mode=or_mode)
                bytes_copied += 1
        rows_drawn += 1

    return {
        "ok": True,
        "arg1_desc": int(arg1_desc),
        "arg3_desc": int(arg3_desc),
        "tbl_idx": int(tbl_idx),
        "mode_or_attr": int(mode_or_attr) & 0xFFFF,
        "or_mode": bool(or_mode),
        "repeat_rows": int(repeat_rows),
        "width_bytes": int(width_bytes),
        "plane_rows": int(plane_rows),
        "copy_width_bytes": int(copy_width_bytes),
        "row_count": int(row_count),
        "rows_drawn": int(rows_drawn),
        "bytes_copied": int(bytes_copied),
        "dst_off": int(dst_off),
        "src_seg_window_base": int(src_seg_window),
    }


def emulate_36ac_wrapper_call(
    planar: EGA36ACPlanarBuffer,
    tables: EGA36ACTables,
    *,
    arg1_desc: int,
    arg2_mode_or_attr: int,
    arg3_desc_or_minus1: int,
) -> dict:
    out = {
        "wrapper": "0x36AC",
        "arg1_desc": int(arg1_desc) & 0xFFFF,
        "arg2_mode_or_attr": int(arg2_mode_or_attr) & 0xFFFF,
        "arg3_desc_or_minus1": int(arg3_desc_or_minus1) & 0xFFFF,
        "two_desc_branch": False,
        "approx_two_desc_branch": False,
        "blits": [],
    }
    if (int(arg3_desc_or_minus1) & 0xFFFF) == 0xFFFF:
        r1 = _emulate_36ac_single_desc(
            planar,
            tables,
            desc_idx=int(arg1_desc) & 0xFFFF,
            mode_or_attr=int(arg2_mode_or_attr) & 0xFFFF,
        )
        out["blits"].append({"which": "arg1_single", **r1})
    else:
        out["two_desc_branch"] = True
        r = _emulate_36ac_two_desc(
            planar,
            tables,
            arg1_desc=int(arg1_desc) & 0xFFFF,
            mode_or_attr=int(arg2_mode_or_attr) & 0xFFFF,
            arg3_desc=int(arg3_desc_or_minus1) & 0xFFFF,
        )
        out["blits"].append({"which": "arg1_arg3_two_desc", **r})
    return out


def render_estimated_queue_36ac_events(
    *,
    events: list[dict],
    gamedata_dir: Path,
) -> tuple[Image.Image | None, dict]:
    mazedata_path = gamedata_dir / "MAZEDATA.EGA"
    ega_drv_path = gamedata_dir / "EGA.DRV"
    if not mazedata_path.exists() or not ega_drv_path.exists():
        return (
            None,
            {
                "ok": False,
                "reason": "missing_gamedata_files",
                "mazedata_ega": str(mazedata_path),
                "ega_drv": str(ega_drv_path),
            },
        )
    tables = EGA36ACTables.load(mazedata_ega=mazedata_path, ega_drv=ega_drv_path)
    planar = EGA36ACPlanarBuffer()
    trace: list[dict] = []
    total = 0
    rendered = 0
    approx_two_desc = 0
    two_desc_exact = 0
    for ev in events:
        if str(ev.get("driver_wrapper")) != "0x36AC":
            continue
        args = ev.get("driver_args_wrapper_order")
        if not (isinstance(args, list) and len(args) == 3 and all(isinstance(v, int) for v in args)):
            continue
        total += 1
        rec = emulate_36ac_wrapper_call(
            planar,
            tables,
            arg1_desc=int(args[0]),
            arg2_mode_or_attr=int(args[1]),
            arg3_desc_or_minus1=int(args[2]),
        )
        if rec.get("approx_two_desc_branch"):
            approx_two_desc += 1
        if rec.get("two_desc_branch"):
            two_desc_exact += 1
        blits = [b for b in (rec.get("blits", []) or []) if isinstance(b, dict)]
        event_nonnoop = any(bool(b.get("ok")) and not b.get("noop") and int(b.get("bytes_copied", 0) or 0) > 0 for b in blits)
        event_noop = (not event_nonnoop) and any(bool(b.get("ok")) and b.get("noop") for b in blits)
        event_ok = all(bool(b.get("ok")) for b in blits) if blits else False
        if event_nonnoop:
            rendered += 1
        fail_reasons = [str(b.get("reason")) for b in blits if not b.get("ok") and b.get("reason") is not None]
        noop_reasons = [str(b.get("noop")) for b in blits if b.get("ok") and b.get("noop") is not None]
        trace.append(
            {
                "event_phase": ev.get("phase"),
                "depth": ev.get("depth"),
                "queue_index": ev.get("queue_index"),
                "source": ev.get("source"),
                "event_ok": bool(event_ok),
                "event_nonnoop": bool(event_nonnoop),
                "event_noop": bool(event_noop),
                "event_fail_reasons": fail_reasons,
                "event_noop_reasons": noop_reasons,
                **rec,
            }
        )
    if total == 0:
        return (
            None,
            {
                "ok": True,
                "events_total_36ac": 0,
                "events_rendered": 0,
                "approx_two_desc_events": 0,
                "trace": [],
            },
        )
    img = planar.to_rgba_image(transparent_zero=True)
    meta = {
        "ok": True,
        "events_total_36ac": int(total),
        "events_rendered": int(rendered),
        "approx_two_desc_events": int(approx_two_desc),
        "two_desc_branch_events": int(two_desc_exact),
        "header_desc_count": int(tables.hdr_recs_190_count_declared),
        "header_desc_table2_parsed_count": int(len(tables.hdr_recs_190)),
        "descriptor_table_source": str(tables.source_path),
        "trace": trace,
        "notes": [
            "Software planar decode of EGA.DRV:0x0B93 single-descriptor branch is implemented from disassembly.",
            "arg3 != 0xFFFF translated/two-descriptor branch is modeled with arg1-source + arg3-placement and XLAT bit-reversal; remaining differences may still exist.",
            "`approx_two_desc_events` is retained for compatibility and should now remain 0.",
            "Output image is a 320x200 debug buffer (not yet mapped into the prototype viewport compositor).",
        ],
    }
    return (img, meta)


