from __future__ import annotations

import json
from pathlib import Path


MAP_HEADER = 0x019E
MAP_RECORD_SIZE = 0x0C0E
MAP_STREAM_WINDOW = 0x01B0


def record_base(map_id: int) -> int:
    return MAP_HEADER + map_id * MAP_RECORD_SIZE


def extract_stream_at_offset(db: bytes, map_id: int, start: int) -> list[int]:
    base = record_base(map_id)
    chunk = db[base : base + MAP_STREAM_WINDOW]
    if not chunk or start < 0 or start >= len(chunk):
        return []
    out: list[int] = []
    for i in range(start, len(chunk)):
        b = chunk[i]
        if b == 0:
            break
        out.append(b)
    return out


def split_sets(codes: list[int]) -> list[list[int]]:
    out: list[list[int]] = []
    for i in range(0, len(codes), 12):
        s = codes[i : i + 12]
        if len(s) < 12:
            break
        out.append(s)
    return out


def first_match_subseq(hay: list[int], needle: list[int]) -> int:
    if not needle or len(needle) > len(hay):
        return -1
    n = len(needle)
    for i in range(len(hay) - n + 1):
        if hay[i : i + n] == needle:
            return i
    return -1


def main() -> None:
    db = Path("gamedata/NEWGAME.DBS").read_bytes()
    n_maps = max(0, (len(db) - MAP_HEADER) // MAP_RECORD_SIZE)
    out = []
    for map_id in range(n_maps):
        s0 = extract_stream_at_offset(db, map_id, 0x00)
        s24 = extract_stream_at_offset(db, map_id, 0x24)
        s48 = extract_stream_at_offset(db, map_id, 0x48)
        off24_in_s0 = first_match_subseq(s0, s24)
        off48_in_s0 = first_match_subseq(s0, s48)
        out.append(
            {
                "map_id": map_id,
                "len0": len(s0),
                "len24": len(s24),
                "len48": len(s48),
                "sets0": len(split_sets(s0)),
                "sets24": len(split_sets(s24)),
                "sets48": len(split_sets(s48)),
                "off24_in_stream0": off24_in_s0,
                "off48_in_stream0": off48_in_s0,
                "stream0": s0,
                "stream24": s24,
                "stream48": s48,
            }
        )

    out_path = Path("scratch/map_owner_streams/offset_stream_analysis.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")
    for r in out:
        if r["len24"] or r["len48"]:
            print(
                f"map {r['map_id']:02d}: len0={r['len0']} len24={r['len24']} len48={r['len48']} "
                f"off24_in_s0={r['off24_in_stream0']} off48_in_s0={r['off48_in_stream0']}"
            )


if __name__ == "__main__":
    main()
