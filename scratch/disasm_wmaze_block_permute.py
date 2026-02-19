from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE = Path("gamedata/WMAZE.OVR")
BASE = 0x4572
HDR = 0x00F2


def main() -> None:
    data = WMAZE.read_bytes()[HDR:]
    md = Cs(CS_ARCH_X86, CS_MODE_16)

    ranges = [
        (0x5F8B, 0x6114, "Block permutation and origin-array carry"),
        (0x63A4, 0x6500, "Periodic block updates calling 0x6114/0x4AC4"),
        (0x70A9, 0x70F3, "Movement-tick path calling 0x6114"),
    ]

    for start, end, title in ranges:
        print(f"\n== {title} ({start:04X}..{end:04X}) ==")
        for ins in md.disasm(data[start - BASE : end - BASE], start):
            print(f"{ins.address:04X}: {ins.mnemonic:<6} {ins.op_str}")


if __name__ == "__main__":
    main()
