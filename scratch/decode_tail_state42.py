from __future__ import annotations

from pathlib import Path
import struct


DB_PATH = Path("gamedata/NEWGAME.DBS")
HEADER_SIZE = 0x019E
MAP_STRIDE = 0x0C0E
TAIL_SIZE = 0x42


def main() -> None:
    data = DB_PATH.read_bytes()
    map_count = (len(data) - HEADER_SIZE - TAIL_SIZE) // MAP_STRIDE
    tail_off = HEADER_SIZE + map_count * MAP_STRIDE
    tail = data[tail_off : tail_off + TAIL_SIZE]
    words = struct.unpack("<33H", tail)

    print(f"file={DB_PATH} size=0x{len(data):X}")
    print(f"map_count={map_count} tail_off=0x{tail_off:X}")
    print("tail words:")
    for i, v in enumerate(words):
        print(f"  w{i:02d}=0x{v:04X} ({v})")

    # Mapping from WBASE load routine around 0x5A92.
    mapping = {
        "w00 -> 0x363C (map_id?)": 0,
        "w01 -> 0x4FA4": 1,
        "w02 -> 0x4FA2": 2,
        "w03 -> 0x4FA0": 3,
        "w04 -> 0x4F9E": 4,
        "w05 -> 0x4F9C": 5,
        "w06 -> 0x4F9A": 6,
        "w07 -> 0x4F98": 7,
        "w08 -> 0x4F96": 8,
        "w09 -> 0x4F94": 9,
        "w10 -> 0x4F92": 10,
        "w11 -> 0x4F90": 11,
        "w12 -> 0x4F8E": 12,
        "w13 -> 0x4F8C": 13,
        "w20 -> 0x4F80 (low), w21 -> 0x4F82 (high)": 20,
        "w22 -> 0x4F7C (low), w23 -> 0x4F7E (high)": 22,
        "w24 -> 0x4F78 (low), w25 -> 0x4F7A (high)": 24,
    }

    print("\nknown mapped fields:")
    for label, idx in mapping.items():
        if "w20" in label:
            lo = words[20]
            hi = words[21]
            print(f"  {label}: 0x{hi:04X}{lo:04X}")
        elif "w22" in label:
            lo = words[22]
            hi = words[23]
            print(f"  {label}: 0x{hi:04X}{lo:04X}")
        elif "w24" in label:
            lo = words[24]
            hi = words[25]
            print(f"  {label}: 0x{hi:04X}{lo:04X}")
        else:
            print(f"  {label}: 0x{words[idx]:04X} ({words[idx]})")


if __name__ == "__main__":
    main()
