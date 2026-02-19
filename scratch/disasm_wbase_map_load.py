from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WBASE_PATH = Path("gamedata/WBASE.OVR")
OVR_BASE = 0x4572
OVR_HEADER = 0x00F2


def logical_to_file(addr: int) -> int:
    return (addr - OVR_BASE) + OVR_HEADER


def disasm_range(data: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    s = logical_to_file(start)
    e = logical_to_file(end)
    out: list[str] = []
    for ins in md.disasm(data[s:e], start):
        out.append(f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}".rstrip())
    return out


def find_calls(data: bytes, target: int) -> list[int]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    out: list[int] = []
    for ins in md.disasm(data[OVR_HEADER:], OVR_BASE):
        if ins.mnemonic == "call" and ins.op_str.strip().lower() == hex(target):
            out.append(ins.address)
    return out


def find_refs_43d(data: bytes) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    out: list[str] = []
    for ins in md.disasm(data[OVR_HEADER:], OVR_BASE):
        s = ins.op_str.lower()
        if "43d0" in s or "43d2" in s or "43dc" in s or "43de" in s:
            out.append(f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}".rstrip())
    return out


def main() -> None:
    if not WBASE_PATH.exists():
        print(f"Missing: {WBASE_PATH}")
        return

    data = WBASE_PATH.read_bytes()
    print(f"WBASE={WBASE_PATH} size={len(data)}")
    print(f"mapping: logical 0x{OVR_BASE:04X} -> file 0x{OVR_HEADER:04X}")

    print("\n== Callsite summary ==")
    for t in (0x3DA4, 0x423D, 0x41EF, 0x41F6, 0x4225):
        calls = find_calls(data, t)
        print(f"call 0x{t:04X}: {len(calls)} at {[f'0x{x:04X}' for x in calls]}")

    print("\n== Refs to 0x43D* arrays ==")
    for line in find_refs_43d(data):
        print(line)

    windows = [
        (0x500D, 0x50AB, "Indexed DB seek/read path"),
        (0x7CC9, 0x7D52, "Header open/seek/read/close path"),
        (0x69BA, 0x6B02, "0x43DC/0x43D0 population + remove path"),
    ]
    for a, b, title in windows:
        print(f"\n== {title} ({a:04X}..{b:04X}) ==")
        for line in disasm_range(data, a, b):
            print(line)


if __name__ == "__main__":
    main()
