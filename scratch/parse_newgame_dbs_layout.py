from __future__ import annotations

from pathlib import Path
import struct


DB_PATH = Path("gamedata/NEWGAME.DBS")
HEADER_SIZE = 0x019E
MAP_A_SIZE = 0x0542
MAP_B_SIZE = 0x06CC
MAP_STRIDE = MAP_A_SIZE + MAP_B_SIZE  # 0x0C0E
TAIL_STATE_SIZE = 0x42
BLOCK_REC_SIZE = 0x1B0


def main() -> None:
    data = DB_PATH.read_bytes()
    size = len(data)
    print(f"file={DB_PATH} size=0x{size:X} ({size})")
    print(
        f"layout constants: header=0x{HEADER_SIZE:X}, mapA=0x{MAP_A_SIZE:X}, "
        f"mapB=0x{MAP_B_SIZE:X}, stride=0x{MAP_STRIDE:X}, tail=0x{TAIL_STATE_SIZE:X}, block=0x{BLOCK_REC_SIZE:X}"
    )

    if size < HEADER_SIZE + TAIL_STATE_SIZE:
        print("File too small for recovered layout.")
        return

    payload = size - HEADER_SIZE
    # Prefer exact-with-tail fit.
    if (payload - TAIL_STATE_SIZE) % MAP_STRIDE == 0 and payload >= TAIL_STATE_SIZE:
        map_count = (payload - TAIL_STATE_SIZE) // MAP_STRIDE
        map_bytes = map_count * MAP_STRIDE
        tail_off = HEADER_SIZE + map_bytes
        tail = data[tail_off : tail_off + TAIL_STATE_SIZE]
        extra = size - (tail_off + TAIL_STATE_SIZE)
        print(f"map_count={map_count}")
        print(f"map_records_off=0x{HEADER_SIZE:X}..0x{tail_off - 1:X}")
        print(f"tail_state_off=0x{tail_off:X}..0x{tail_off + TAIL_STATE_SIZE - 1:X}")
        print(f"extra_after_tail=0x{extra:X}")
        print("tail_state words (0x42 bytes => 33 words):")
        vals = struct.unpack("<33H", tail)
        for i, v in enumerate(vals):
            print(f"  w{i:02d}: 0x{v:04X} ({v})")
        block_count_from_tail = vals[32]
        print(f"tail w32 (expected 0x43CE/block-record count): {block_count_from_tail}")
        if extra > 0:
            block_count = extra // BLOCK_REC_SIZE
            rem = extra % BLOCK_REC_SIZE
            print(f"optional_block_records={block_count} remainder=0x{rem:X}")
            if rem == 0:
                print(f"matches_tail_count={block_count == block_count_from_tail}")
        else:
            print(f"optional_block_records=0 matches_tail_count={block_count_from_tail == 0}")
    else:
        print("No exact [header + N*stride + tail] fit; checking [header + N*stride] only.")
        if payload % MAP_STRIDE == 0:
            map_count = payload // MAP_STRIDE
            print(f"map_count={map_count} (no tail detected)")
        else:
            print("File does not match recovered layout exactly.")


if __name__ == "__main__":
    main()
