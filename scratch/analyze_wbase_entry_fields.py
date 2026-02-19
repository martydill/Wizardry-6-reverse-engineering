from __future__ import annotations

import re
from pathlib import Path
from collections import Counter

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WBASE = Path("gamedata/WBASE.OVR")
BASE = 0x4572
HDR = 0x00F2


def main() -> None:
    data = WBASE.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    start, end = 0x5FAD, 0x628E
    lines = [f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}" for i in md.disasm(data[(start-BASE)+HDR:(end-BASE)+HDR], start)]

    pat = re.compile(r"\[bx \+ 0x([0-9a-f]+)\]", re.IGNORECASE)
    counts: Counter[int] = Counter()
    refs: dict[int, list[str]] = {}
    for line in lines:
        m = pat.search(line)
        if not m:
            continue
        off = int(m.group(1), 16)
        counts[off] += 1
        refs.setdefault(off, []).append(line)

    print("== WBASE 0x5FAD field references (entry-relative) ==")
    for off, cnt in sorted(counts.items()):
        print(f"0x{off:04X}: count={cnt}")
        for sample in refs[off][:3]:
            print(f"  {sample}")


if __name__ == "__main__":
    main()
