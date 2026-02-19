from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WROOT_PATH = Path("gamedata/WROOT.EXE")
THUNK_DELTA = 0x00E4


def load_wroot_module(path: Path) -> bytes:
    data = path.read_bytes()
    e_cparhdr = int.from_bytes(data[0x08:0x0A], "little")
    return data[e_cparhdr * 16 :]


def disasm_at(code: bytes, addr: int, count: int = 22) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    out = []
    start = max(0, addr - 10)
    for ins in md.disasm(code[start : start + 0x120], start):
        mark = ">>" if ins.address == addr else "  "
        out.append(f"{mark} {ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}".rstrip())
        if len(out) >= count:
            break
    return out


def main() -> None:
    if not WROOT_PATH.exists():
        print(f"Missing: {WROOT_PATH}")
        return

    code = load_wroot_module(WROOT_PATH)
    overlay_ids = [
        0x3DA4,
        0x423D,
        0x4225,
        0x41EF,
        0x41F6,
        0x435C,
        0x279D,
        0x27CB,
        0x27F6,
        0x2841,
        0x287E,
        0x0677,
        0x0BF2,
    ]

    print(f"Thunk delta: +0x{THUNK_DELTA:04X}")
    for oid in overlay_ids:
        rid = oid + THUNK_DELTA
        print(f"\n== overlay 0x{oid:04X} -> wroot 0x{rid:04X} ==")
        for line in disasm_at(code, rid):
            print(line)


if __name__ == "__main__":
    main()
