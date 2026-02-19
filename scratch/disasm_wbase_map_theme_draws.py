from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WBASE = Path("gamedata/WBASE.OVR")
OVR_BASE = 0x4572
OVR_HDR = 0x00F2


def logical_to_file(addr: int) -> int:
    return (addr - OVR_BASE) + OVR_HDR


def disasm_window(data: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    code = data[logical_to_file(start) : logical_to_file(end)]
    return [f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}" for ins in md.disasm(code, start)]


def main() -> None:
    if not WBASE.exists():
        print(f"Missing: {WBASE}")
        return

    data = WBASE.read_bytes()

    print("== WBASE map-record themed draw windows (0x1B0 / 0x43E8 proximity) ==")
    for start, end, label in [
        (0x5FD0, 0x6040, "map ptr + 0x43E8 -> 0x2439/0x22FF"),
        (0x6A10, 0x6B50, "map ptr + 0x43E8 -> 0x2439"),
        (0x6C60, 0x6D20, "draw sequence with 0x0B32 / 0x2405"),
        (0x6D80, 0x6DB5, "map ptr + 0x43E8 -> 0x2405"),
    ]:
        print(f"\n-- {label} ({start:04X}..{end:04X}) --")
        for line in disasm_window(data, start, end):
            print(line)


if __name__ == "__main__":
    main()
