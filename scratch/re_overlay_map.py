from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from capstone import CS_ARCH_X86, CS_MODE_16, Cs


@dataclass(frozen=True)
class OverlayMap:
    """Logical-address mapper for Wizardry 6 `.OVR` files."""

    base: int = 0x4572
    header_size: int = 0x00F2

    def logical_to_file(self, logical_addr: int) -> int:
        return ((logical_addr - self.base) & 0xFFFF) + self.header_size

    def file_to_logical(self, file_offset: int) -> int:
        return (self.base + (file_offset - self.header_size)) & 0xFFFF


def disassemble_at(path: Path, logical_addr: int, count: int = 24) -> list[str]:
    data = path.read_bytes()
    mapper = OverlayMap()
    off = mapper.logical_to_file(logical_addr)
    if off < 0 or off >= len(data):
        return [f"{logical_addr:04X}: <out of range>"]

    md = Cs(CS_ARCH_X86, CS_MODE_16)
    out: list[str] = []
    for ins in md.disasm(data[off : off + 256], logical_addr):
        out.append(f"{ins.address:04X}: {ins.mnemonic} {ins.op_str}".rstrip())
        if len(out) >= count:
            break
    if not out:
        out.append(f"{logical_addr:04X}: <unable to decode>")
    return out


def find_calls_to(path: Path, targets: Iterable[int]) -> list[str]:
    data = path.read_bytes()
    mapper = OverlayMap()
    wanted = set(t & 0xFFFF for t in targets)
    lines: list[str] = []

    for i in range(len(data) - 2):
        if data[i] != 0xE8:
            continue
        rel = int.from_bytes(data[i + 1 : i + 3], "little", signed=True)
        src = mapper.file_to_logical(i)
        dst = (src + 3 + rel) & 0xFFFF
        if dst in wanted:
            lines.append(f"{src:04X} -> {dst:04X} (file 0x{i:05X})")
    return lines


def main() -> None:
    ovr = Path("gamedata/WPCVW.OVR")
    if not ovr.exists():
        print(f"Missing overlay: {ovr}")
        return

    probe_targets = [0xBBB6, 0xBD6E, 0xBDA7, 0xC1F7, 0xDF85, 0xFAAB]
    print(f"Overlay: {ovr} ({ovr.stat().st_size} bytes)")
    print("Mapper: base=0x4572 header=0x00F2")

    print("\nResolved target disassembly:")
    for target in probe_targets:
        print(f"\n-- {target:04X} --")
        for line in disassemble_at(ovr, target, count=14):
            print(line)

    print("\nCall sites into target set:")
    calls = find_calls_to(ovr, probe_targets)
    if not calls:
        print("<none found>")
    else:
        for line in calls[:80]:
            print(line)


if __name__ == "__main__":
    main()
