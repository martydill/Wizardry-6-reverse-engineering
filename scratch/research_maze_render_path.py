from __future__ import annotations

from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, CS_OP_IMM, Cs


OVR_BASE = 0x4572
OVR_HDR = 0x00F2


def parse_display_records(path: Path) -> tuple[int, int, bytes]:
    data = path.read_bytes()
    n = data[0] | (data[1] << 8)
    n2 = data[2] | (data[3] << 8)
    start = 4 + n * 5
    end = start + n2 * 5
    return n, n2, data[start:end]


def scan_overlay_calls(path: Path, targets: list[int]) -> dict[int, list[int]]:
    data = path.read_bytes()
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    md.detail = True
    out: dict[int, list[int]] = {t: [] for t in targets}
    for ins in md.disasm(data[OVR_HDR:], OVR_BASE):
        if ins.mnemonic != "call":
            continue
        if not ins.operands:
            continue
        op = ins.operands[0]
        if op.type != CS_OP_IMM:
            continue
        tgt = op.imm & 0xFFFF
        if tgt in out:
            out[tgt].append(ins.address)
    return out


def raw_e8_calls_to_target(path: Path, target: int) -> list[int]:
    data = path.read_bytes()[OVR_HDR:]
    out: list[int] = []
    for i in range(len(data) - 2):
        if data[i] != 0xE8:
            continue
        rel = int.from_bytes(data[i + 1 : i + 3], "little", signed=True)
        src = OVR_BASE + i
        dst = (src + 3 + rel) & 0xFFFF
        if dst == target:
            out.append(src)
    return out


def extract_ascii_strings(path: Path) -> list[tuple[int, str]]:
    data = path.read_bytes()
    out: list[tuple[int, str]] = []
    i = OVR_HDR
    while i < len(data):
        if 32 <= data[i] < 127:
            j = i
            while j < len(data) and 32 <= data[j] < 127:
                j += 1
            s = data[i:j].decode("ascii", errors="ignore")
            if len(s) >= 4:
                logical = OVR_BASE + (i - OVR_HDR)
                out.append((logical, s))
            i = j + 1
        else:
            i += 1
    return out


def main() -> None:
    overlays = sorted(Path("gamedata").glob("W*.OVR"))
    targets = [0x53AA, 0x7A37, 0x7B5D, 0x7BC2, 0x2841, 0x227, 0x22FF, 0x2405, 0x2439, 0x0B32]

    print("== Overlay call-map for maze/render primitives ==")
    for ov in overlays:
        calls = scan_overlay_calls(ov, targets)
        active = {k: v for k, v in calls.items() if v}
        if not active:
            continue
        summary = ", ".join(f"{k:04X}:{len(v)}" for k, v in sorted(active.items()))
        print(f"{ov.name}: {summary}")

    wmaze = Path("gamedata/WMAZE.OVR")
    c53 = raw_e8_calls_to_target(wmaze, 0x53AA)
    print("\n== WMAZE raw near-calls to 0x53AA ==")
    print(", ".join(f"0x{x:04X}" for x in c53) if c53 else "none")

    winit = Path("gamedata/WINIT.OVR")
    print("\n== WINIT strings related to MAZEDATA/fonts/title ==")
    for addr, s in extract_ascii_strings(winit):
        us = s.upper()
        if "MAZEDATA" in us or "WFONT" in us or "TITLEPAG" in us:
            print(f"0x{addr:04X}: {s}")

    ega = Path("gamedata/MAZEDATA.EGA")
    cga = Path("gamedata/MAZEDATA.CGA")
    t16 = Path("gamedata/MAZEDATA.T16")
    ne, ne2, re = parse_display_records(ega)
    nc, nc2, rc = parse_display_records(cga)
    nt, nt2, rt = parse_display_records(t16)
    same_ec = re == rc
    same_et = re == rt
    print("\n== MAZEDATA display-record table parity (EGA/CGA/T16) ==")
    print(f"EGA: N={ne}, N2={ne2}, table_bytes={len(re)}")
    print(f"CGA: N={nc}, N2={nc2}, table_bytes={len(rc)}")
    print(f"T16: N={nt}, N2={nt2}, table_bytes={len(rt)}")
    print(f"display_table_equal_ega_cga={same_ec}")
    print(f"display_table_equal_ega_t16={same_et}")


if __name__ == "__main__":
    main()
