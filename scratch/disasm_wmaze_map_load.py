from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE_PATH = Path("gamedata/WMAZE.OVR")
OVR_BASE = 0x4572
OVR_HEADER = 0x00F2


def logical_to_file(addr: int) -> int:
    return (addr - OVR_BASE) + OVR_HEADER


def disasm_range(data: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    s = logical_to_file(start)
    e = logical_to_file(end)
    out = []
    for ins in md.disasm(data[s:e], start):
        out.append(f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}".rstrip())
    return out


def main() -> None:
    if not WMAZE_PATH.exists():
        print(f"Missing: {WMAZE_PATH}")
        return

    data = WMAZE_PATH.read_bytes()
    print("== WMAZE map-load staging routine ==")
    print(f"file={WMAZE_PATH} size={len(data)}")
    print(f"mapping: logical 0x{OVR_BASE:04X} -> file 0x{OVR_HEADER:04X}")

    for a, b, title in [
        (0x66C0, 0x67FF, "Open + seek + 0x019E header read"),
        (0x681A, 0x693F, "Per-entry dual-buffer reads"),
        (0x69F4, 0x6AE7, "Tail struct + 0x1B0 block loop"),
    ]:
        print(f"\n-- {title} ({a:04X}..{b:04X}) --")
        for line in disasm_range(data, a, b):
            print(line)


if __name__ == "__main__":
    main()
