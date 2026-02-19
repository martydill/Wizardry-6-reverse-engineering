from __future__ import annotations

import json
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE = Path("gamedata/WMAZE.OVR")
BASE = 0x4572
HDR = 0x00F2


def main() -> None:
    data = WMAZE.read_bytes()
    code = data[HDR:]
    md = Cs(CS_ARCH_X86, CS_MODE_16)

    start, end = 0x4AC4, 0x4DA5
    ins = list(md.disasm(code[start - BASE : end - BASE], start))
    lines = [f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}" for i in ins]

    calls = []
    targets = {"0x22ff", "0x2439", "0x2405", "0x227"}
    for idx, i in enumerate(ins):
        if i.mnemonic != "call":
            continue
        t = i.op_str.strip().lower()
        if t not in targets:
            continue
        ctx_lo = max(0, idx - 10)
        ctx = lines[ctx_lo : idx + 1]
        calls.append(
            {
                "callsite": f"0x{i.address:04X}",
                "target": t,
                "context": ctx,
            }
        )

    # Collect map-record field references used by this routine.
    refs = []
    for i in ins:
        s = i.op_str.lower()
        if "[bx + 0x" in s:
            refs.append(f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}")
    refs = sorted(set(refs))

    out = {
        "window": {"start": f"0x{start:04X}", "end": f"0x{end:04X}"},
        "draw_calls": calls,
        "bx_field_refs": refs,
    }
    out_path = Path("scratch/wmaze_4ac4_calls.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {out_path}")
    print(f"draw_calls={len(calls)}")
    print("field refs:")
    for r in refs:
        print(r)


if __name__ == "__main__":
    main()
