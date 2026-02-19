from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
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


def decode_low_only(code: int) -> int | None:
    if 0 <= code <= 152:
        return code
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Infer stream_code->owner map from slot co-occurrence across map streams")
    ap.add_argument("--gamedata", type=Path, default=Path("gamedata"))
    ap.add_argument(
        "--offsets",
        default="0x0,0x24,0x48",
        help="Comma-separated stream entry offsets within map +0x1B0 window.",
    )
    ap.add_argument(
        "--prior-weight",
        type=float,
        default=0.7,
        help="Weight of code-28 gaussian prior term for high codes.",
    )
    ap.add_argument(
        "--prior-sigma",
        type=float,
        default=8.0,
        help="Sigma for code-28 gaussian prior distance.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("scratch/owner_slot_candidates/stream_code_map_inferred.json"),
    )
    args = ap.parse_args()

    offs: list[int] = []
    for part in args.offsets.split(","):
        p = part.strip()
        if not p:
            continue
        offs.append(int(p, 0))
    if not offs:
        offs = [0x00, 0x24, 0x48]

    db = (args.gamedata / "NEWGAME.DBS").read_bytes()
    n_maps = max(0, (len(db) - MAP_HEADER) // MAP_RECORD_SIZE)

    slot_low: dict[int, Counter[int]] = defaultdict(Counter)
    high_occ: dict[int, Counter[int]] = defaultdict(Counter)

    for map_id in range(n_maps):
        for off in offs:
            stream = extract_stream_at_offset(db, map_id, off)
            if not stream:
                continue
            for s in split_sets(stream):
                for i, c in enumerate(s):
                    lo = decode_low_only(c)
                    if lo is not None:
                        slot_low[i][lo] += 1
                    elif 153 <= c <= 255:
                        high_occ[c][i] += 1

    # Slot-conditioned probability with add-one smoothing.
    slot_totals = {i: sum(cnt.values()) for i, cnt in slot_low.items()}
    owner_domain = list(range(153))

    mapping: dict[int, int] = {}
    score_debug: dict[int, dict[str, float | int]] = {}
    for code, occ in sorted(high_occ.items()):
        best_owner = 0
        best_score = -1e18
        for owner in owner_domain:
            s = 0.0
            for slot_idx, n in occ.items():
                cnt = slot_low[slot_idx][owner]
                total = slot_totals.get(slot_idx, 0)
                p = (cnt + 1.0) / (total + len(owner_domain))
                s += n * math.log(p)
            prior_center = code - 28
            if 0 <= prior_center <= 152 and args.prior_weight > 0:
                dz = (owner - prior_center) / max(1e-6, args.prior_sigma)
                s += args.prior_weight * (-0.5 * dz * dz)
            if s > best_score:
                best_score = s
                best_owner = owner
        mapping[code] = best_owner
        score_debug[code] = {
            "owner": best_owner,
            "score": best_score,
            "occ_count": int(sum(occ.values())),
        }

    # Emit full map:
    # - low codes direct
    # - inferred high codes where seen
    out_map: dict[str, int] = {}
    for c in range(0, 153):
        out_map[str(c)] = c
    for c, o in mapping.items():
        out_map[str(c)] = o

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out_map, indent=2))

    dbg_path = args.out.with_name(args.out.stem + "_debug.json")
    dbg_path.write_text(
        json.dumps(
            {
                "offsets": offs,
                "high_codes_seen": sorted(mapping.keys()),
                "mapping": {str(k): v for k, v in mapping.items()},
                "score_debug": {str(k): v for k, v in score_debug.items()},
            },
            indent=2,
        )
    )

    print(f"Wrote {args.out}")
    print(f"Wrote {dbg_path}")
    print(f"high codes inferred: {sorted(mapping.keys())}")
    for c in sorted(mapping.keys()):
        print(f"{c} -> {mapping[c]}")


if __name__ == "__main__":
    main()
