from __future__ import annotations

import json
from pathlib import Path


MAP_HEADER = 0x019E
MAP_RECORD_SIZE = 0x0C0E
MAP_STREAM_WINDOW = 0x01B0


def record_base(map_id: int) -> int:
    return MAP_HEADER + map_id * MAP_RECORD_SIZE


def read_stream0(db: bytes, map_id: int) -> list[int]:
    base = record_base(map_id)
    chunk = db[base : base + MAP_STREAM_WINDOW]
    out = []
    for b in chunk:
        if b == 0:
            break
        out.append(b)
    return out


def entry_byte(db: bytes, map_id: int, off: int) -> int:
    return db[record_base(map_id) + off]


def main() -> None:
    db = Path("gamedata/NEWGAME.DBS").read_bytes()
    n_maps = max(0, (len(db) - MAP_HEADER) // MAP_RECORD_SIZE)

    # Emulate the code picks visible in WMAZE:0x4AC4 / WBASE:0x5FAD:
    # - stream0 zero-term
    # - 3x3 block at stream index 0x48 + 3*slot_id (slot_id from global 0x43D0[])
    # We do not know runtime slot_id table here, so report all slot_id variants 0..5.
    rows = []
    for map_id in range(n_maps):
        s0 = read_stream0(db, map_id)
        if not s0:
            continue
        # Candidate panel block codes for each slot-id (global 0..5 in WBASE:0x50AC).
        by_slot = {}
        for sid in range(6):
            base = 0x48 + 3 * sid
            block = s0[base : base + 9] if base < len(s0) else []
            by_slot[str(sid)] = block
        rows.append(
            {
                "map_id": map_id,
                "stream0_len": len(s0),
                "stream0_head": s0[:24],
                "panel_3x3_by_slotid": by_slot,
                "b_4589": entry_byte(db, map_id, 0x4589) if record_base(map_id) + 0x4589 < len(db) else None,
                "b_4587": entry_byte(db, map_id, 0x4587) if record_base(map_id) + 0x4587 < len(db) else None,
            }
        )

    out = Path("scratch/shared_draw_code_emulation.json")
    out.write_text(json.dumps(rows, indent=2))
    print(f"Wrote {out}")
    for r in rows:
        if r["stream0_len"] >= 0x48 + 9:
            print(
                f"map {r['map_id']:02d} len={r['stream0_len']} slot0={r['panel_3x3_by_slotid']['0']} "
                f"slot1={r['panel_3x3_by_slotid']['1']}"
            )


if __name__ == "__main__":
    main()
