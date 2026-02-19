from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WROOT = Path("gamedata/WROOT.EXE")


def load_module(path: Path) -> bytes:
    data = path.read_bytes()
    e_cparhdr = int.from_bytes(data[0x08:0x0A], "little")
    return data[e_cparhdr * 16 :]


def disasm_window(code: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    return [f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}" for i in md.disasm(code[start:end], start)]


def main() -> None:
    if not WROOT.exists():
        print(f"Missing: {WROOT}")
        return

    code = load_module(WROOT)

    print("== WROOT draw core: 0x22B7..0x23E3 ==")
    for line in disasm_window(code, 0x22B7, 0x23E3):
        print(line)

    print("\n== WROOT wrapper: 0x23E3..0x24E9 ==")
    for line in disasm_window(code, 0x23E3, 0x24E9):
        print(line)

    print("\n== WROOT wrappers: 0x24E9..0x2556 ==")
    for line in disasm_window(code, 0x24E9, 0x2556):
        print(line)


if __name__ == "__main__":
    main()
