from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WROOT_PATH = Path("gamedata/WROOT.EXE")


def read_load_module(path: Path) -> bytes:
    data = path.read_bytes()
    e_cparhdr = int.from_bytes(data[0x08:0x0A], "little")
    header_size = e_cparhdr * 16
    return data[header_size:]


def disasm_window(code: bytes, start: int, count: int = 40) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    lines = []
    for i, ins in enumerate(md.disasm(code[start : start + 0x200], start)):
        lines.append(f"{ins.address:04X}: {ins.mnemonic} {ins.op_str}".rstrip())
        if i + 1 >= count:
            break
    return lines


def main() -> None:
    if not WROOT_PATH.exists():
        print(f"Missing: {WROOT_PATH}")
        return

    code = read_load_module(WROOT_PATH)

    probes = [
        ("Startup open/read/close sequence", 0x1F42),
        ("Read wrapper (AH=3F)", 0x42C0),
        ("Write wrapper (AH=40)", 0x42C9),
        ("Close wrapper (AH=3E)", 0x4309),
        ("Seek wrapper (AH=42)", 0x4321),
    ]

    for title, addr in probes:
        print(f"\n== {title} @ {addr:04X} ==")
        for line in disasm_window(code, addr):
            print(line)


if __name__ == "__main__":
    main()
