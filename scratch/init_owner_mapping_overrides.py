from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description="Initialize editable owner mapping overrides from slot candidates")
    ap.add_argument(
        "--slot-candidates",
        type=Path,
        default=Path("scratch/owner_slot_candidates/slot_candidates.json"),
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("scratch/owner_slot_candidates/mapping_overrides.json"),
    )
    args = ap.parse_args()

    data = json.loads(args.slot_candidates.read_text())
    by_val = data.get("slot_candidates_by_wall_value", {})
    generic = data.get("slot_candidates", {})

    out: dict[str, dict[str, int]] = {"1": {}, "2": {}, "3": {}}
    for ws in ("1", "2", "3"):
        src = by_val.get(ws, {})
        for slot_key, generic_ids in generic.items():
            ids = src.get(slot_key, generic_ids)
            if ids:
                out[ws][slot_key] = int(ids[0])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
