from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE = Path("gamedata/WMAZE.OVR")
OVR_BASE = 0x4572
OVR_HDR = 0x00F2


def logical_to_file(addr: int) -> int:
    return (addr - OVR_BASE) + OVR_HDR


def raw_e8_calls_to_target(code: bytes, target: int) -> list[int]:
    out: list[int] = []
    for i in range(len(code) - 2):
        if code[i] != 0xE8:
            continue
        rel = int.from_bytes(code[i + 1 : i + 3], "little", signed=True)
        src = OVR_BASE + i
        dst = (src + 3 + rel) & 0xFFFF
        if dst == target:
            out.append(src)
    return out


def read_u16_table(data: bytes, start_addr: int, count: int) -> list[int]:
    off = logical_to_file(start_addr)
    out: list[int] = []
    for i in range(count):
        w = int.from_bytes(data[off + i * 2 : off + i * 2 + 2], "little")
        out.append(w)
    return out


def disasm_window(data: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    code = data[logical_to_file(start) : logical_to_file(end)]
    return [f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}" for ins in md.disasm(code, start)]


def main() -> None:
    if not WMAZE.exists():
        print(f"Missing: {WMAZE}")
        return

    data = WMAZE.read_bytes()
    code = data[OVR_HDR:]

    print("== Raw E8 callsites in WMAZE for draw helpers ==")
    for target in (0x0227, 0x22FF, 0x2405, 0x2439, 0x0B32, 0x53AA):
        hits = raw_e8_calls_to_target(code, target)
        joined = ", ".join(f"0x{x:04X}" for x in hits)
        print(f"target 0x{target:04X}: count={len(hits)}")
        print(f"  {joined}")

    print("\n== Dispatcher table at 0x6E13 (9 entries) ==")
    tbl_6e13 = read_u16_table(data, 0x6E13, 9)
    for idx, dst in enumerate(tbl_6e13):
        print(f"  case {idx}: 0x{dst:04X}")

    print("\n== Switch stub at 0x6E25..0x6E32 ==")
    for line in disasm_window(data, 0x6E25, 0x6E33):
        print(f"  {line}")

    print("\n== Core helper 0x6E4C (two-row, four-sprite blit) ==")
    for line in disasm_window(data, 0x6E4C, 0x6EBF):
        print(f"  {line}")

    print("\n== Core helper 0x6EBF (two-row, eight-sprite strip blit) ==")
    for line in disasm_window(data, 0x6EBF, 0x6F3C):
        print(f"  {line}")

    print("\n== Caller pattern around 0x73B8..0x74B2 ==")
    for line in disasm_window(data, 0x73B8, 0x74B3):
        print(f"  {line}")

    print("\n== 0x53AA callsite at 0x76E2 context ==")
    for line in disasm_window(data, 0x76C4, 0x7707):
        print(f"  {line}")


if __name__ == "__main__":
    main()
