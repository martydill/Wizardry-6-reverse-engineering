from __future__ import annotations

import json
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WBASE = Path("gamedata/WBASE.OVR")
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


def disasm_window(data: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    if start < BASE:
        start = BASE
    s = (start - BASE) + HDR
    e = (end - BASE) + HDR
    return [f"{i.address:04X}: {i.mnemonic} {i.op_str}" for i in md.disasm(data[s:e], start)]


def main() -> None:
    data = WBASE.read_bytes()
    code = data[HDR:]

    out: dict[str, list[dict]] = {"2439": [], "2405": [], "22ff": []}
    for tgt, key in [(0x2439, "2439"), (0x2405, "2405"), (0x22FF, "22ff")]:
        for a in raw_calls(code, tgt):
            ctx = disasm_window(data, a - 0x30, a + 0x12)
            out[key].append({"callsite": f"0x{a:04X}", "context": ctx})

    p = Path("scratch/wbase_draw_callsite_context.json")
    p.write_text(json.dumps(out, indent=2))
    print(f"Wrote: {p}")


if __name__ == "__main__":
    main()
