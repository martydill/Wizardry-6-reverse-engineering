from __future__ import annotations

import json
from pathlib import Path


def default_owner(code: int) -> int | None:
    if 0 <= code <= 152:
        return code
    if 153 <= code <= 180:
        return code - 28
    return None


def main() -> None:
    out = Path('scratch/owner_slot_candidates/stream_code_map_default.json')
    mapping = {}
    for c in range(0, 256):
        o = default_owner(c)
        if o is not None:
            mapping[str(c)] = o
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(mapping, indent=2))
    print(f'Wrote: {out}')


if __name__ == '__main__':
    main()
