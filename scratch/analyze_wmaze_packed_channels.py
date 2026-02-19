from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE_PATH = Path("gamedata/WMAZE.OVR")
BASE = 0x4572
HDR = 0x00F2


def load_insns():
    data = WMAZE_PATH.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    return list(md.disasm(data[HDR:], BASE))


def main() -> None:
    if not WMAZE_PATH.exists():
        print(f"Missing: {WMAZE_PATH}")
        return

    ins = load_insns()
    targets = {
        0x279D: "set_bit",
        0x27CB: "get_bit",
        0x27F6: "set_field",
        0x2841: "get_field",
    }

    print("Packed channel helper callsites in WMAZE:")
    for t, name in targets.items():
        hits = [i.address for i in ins if i.mnemonic == "call" and i.op_str == hex(t)]
        print(f"  {name:9s} {t:04X}: {len(hits)} calls -> {', '.join(f'{h:04X}' for h in hits)}")

    print("\nKey formulas seen near callsites:")
    print("  idx = (block << 6) + (row << 3) + col")
    print("  local coords normalized with mod 8 before indexing")

    print("\nDerived packed storage capacities:")
    print("  bitset: 12 * 8 * 8 = 768 bits = 0x60 bytes")
    print("  2-bit field: 768 entries = 0xC0 bytes")
    print("  3-bit field: 60 entries = 180 bits (~24-byte packed region)")

    print("\nNotable base+offset regions under [0x4FAA]:")
    for off, note in [
        (0x43A, "1-bit map A (get_bit)"),
        (0x49A, "1-bit map B (get_bit)"),
        (0x060, "2-bit field map A"),
        (0x120, "2-bit field map B"),
        (0x4FA, "3-bit field map A"),
        (0x512, "3-bit field map B"),
    ]:
        print(f"  +0x{off:03X}: {note}")


if __name__ == "__main__":
    main()
