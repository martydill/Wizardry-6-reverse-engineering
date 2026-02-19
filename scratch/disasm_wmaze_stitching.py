from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


WMAZE = Path("gamedata/WMAZE.OVR")
BASE = 0x4572
HDR = 0x00F2


def load_code() -> bytes:
    return WMAZE.read_bytes()[HDR:]


def raw_call_sites(code: bytes, targets: list[int]) -> dict[int, list[int]]:
    """Scan for E8 rel16 calls regardless of decode alignment."""
    out = {t: [] for t in targets}
    start = BASE
    end = BASE + len(code)
    tset = set(targets)
    for a in range(start, end - 2):
        off = a - BASE
        if code[off] != 0xE8:
            continue
        rel = int.from_bytes(code[off + 1 : off + 3], "little", signed=True)
        tgt = (a + 3 + rel) & 0xFFFF
        if tgt in tset:
            out[tgt].append(a)
    return out


def disasm_window(code: bytes, start: int, end: int) -> list[str]:
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    return [f"{i.address:04X}: {i.mnemonic:<6} {i.op_str}" for i in md.disasm(code[start - BASE : end - BASE], start)]


def main() -> None:
    if not WMAZE.exists():
        print(f"Missing: {WMAZE}")
        return

    code = load_code()
    targets = [0x5F8B, 0x6114, 0x4E48, 0x4AC4, 0x7A37]
    calls = raw_call_sites(code, targets)

    print("== Raw near-call sites (E8 rel16) ==")
    for t in targets:
        arr = calls[t]
        print(f"target {t:04X}: count={len(arr)} -> {', '.join(f'{x:04X}' for x in arr)}")

    windows = [
        (0x5F8B, 0x6116, "Block permutation / origin carry"),
        (0x6114, 0x6310, "Per-block update + redraw"),
        (0x6CF0, 0x6E10, "Dispatcher region with 0x5F8B caller"),
        (0x79FA, 0x7AEE, "BBox check + world resolver"),
    ]
    for s, e, title in windows:
        print(f"\n== {title} ({s:04X}..{e:04X}) ==")
        for line in disasm_window(code, s, e):
            print(line)


if __name__ == "__main__":
    main()

