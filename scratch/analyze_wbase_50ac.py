from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WBASE = Path("gamedata/WBASE.OVR")
BASE = 0x4572
HDR = 0x00F2


def main() -> None:
    data = WBASE.read_bytes()
    code = data[HDR:]
    md = Cs(CS_ARCH_X86, CS_MODE_16)

    start, end = 0x50AC, 0x5100
    lines = [f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}" for i in md.disasm(code[start - BASE : end - BASE], start)]
    out = Path("scratch/wbase_50ac_disasm.txt")
    out.write_text("\n".join(lines))
    print(f"Wrote {out}")
    for ln in lines:
        print(ln)

    print("\nRecovered behavior:")
    print("- Input: count n (word ptr [bp+4])")
    print("- Scans global table 0x43D0[0..n-1]")
    print("- Returns smallest candidate in 0..5 not already present")
    print("- If all 0..5 are present, returns 0")


if __name__ == "__main__":
    main()
