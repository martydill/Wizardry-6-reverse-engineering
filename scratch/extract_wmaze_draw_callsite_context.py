from __future__ import annotations

import json
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, CS_OP_IMM, Cs


WMAZE = Path("gamedata/WMAZE.OVR")
BASE = 0x4572
HDR = 0x00F2


def raw_calls(code: bytes, target: int) -> list[int]:
    out: list[int] = []
    for i in range(len(code) - 2):
        if code[i] != 0xE8:
            continue
        rel = int.from_bytes(code[i + 1 : i + 3], "little", signed=True)
        src = BASE + i
        dst = (src + 3 + rel) & 0xFFFF
        if dst == target:
            out.append(src)
    return out


def main() -> None:
    data = WMAZE.read_bytes()
    code = data[HDR:]
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    md.detail = True
    ins = list(md.disasm(code, BASE))
    by_addr = {i.address: n for n, i in enumerate(ins)}

    out = {"2439": [], "2405": [], "22ff": []}
    targets = [(0x2439, "2439"), (0x2405, "2405"), (0x22FF, "22ff")]

    for tgt, key in targets:
        for a in raw_calls(code, tgt):
            idx = by_addr.get(a)
            rec = {"callsite": f"0x{a:04X}", "linear": idx is not None, "context": []}
            if idx is not None:
                s = max(0, idx - 16)
                e = min(len(ins), idx + 2)
                rec["context"] = [f"{ins[j].address:04X}: {ins[j].mnemonic} {ins[j].op_str}" for j in range(s, e)]
            out[key].append(rec)

    out_path = Path("scratch/wmaze_draw_callsite_context.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
