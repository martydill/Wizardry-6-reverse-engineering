from pathlib import Path
import re

from bane.data.huffman import HuffmanDecoder


def load_entries():
    hdr = Path("gamedata/MSG.HDR").read_bytes()
    words = [int.from_bytes(hdr[i : i + 2], "little") for i in range(0, len(hdr) - 1, 2)]
    count = words[0]
    i = 1
    entries = []
    for _ in range(count):
        mid = words[i]
        off = words[i + 1]
        packed = words[i + 2]
        entries.append((mid, (packed >> 8) & 0xFF, off, packed & 0xFF))
        i += 3
    return entries


def decode_msg(raw: bytes, dec: HuffmanDecoder, entries, mid: int, bit_offset: int) -> str:
    by = {e[0]: e for e in entries}
    by_bank = {}
    for e in entries:
        by_bank.setdefault(e[1], []).append(e)
    for b in by_bank:
        by_bank[b].sort(key=lambda x: x[2])

    bank = by[mid][1]
    off = by[mid][2]
    arr = by_bank[bank]
    idx = [k for k, e in enumerate(arr) if e[0] == mid][0]
    end = 1024
    for j in range(idx + 1, len(arr)):
        if arr[j][2] > off:
            end = arr[j][2]
            break

    pos = bank * 1024 + off
    eabs = bank * 1024 + end
    out = []
    while pos < eabs:
        ln = raw[pos]
        pos += 1
        if ln == 0 or pos + ln > len(raw):
            break
        out.append(dec.decode(raw[pos : pos + ln], 65535, bit_offset=bit_offset).decode("ascii", errors="replace"))
        pos += ln
    txt = "".join(out)
    txt = txt.replace("!", "\n").replace("%", "\n").replace("$", "\n")
    txt = re.sub(r"[ \t]{2,}", " ", txt)
    return txt


def main() -> None:
    raw = Path("gamedata/MSG.DBS").read_bytes()
    dec = HuffmanDecoder.from_file("gamedata/MISC.HDR")
    entries = load_entries()
    ids = [12100, 12560, 10010, 10030, 18950, 8200]
    for bit_offset in range(8):
        print(f"\nBO {bit_offset}")
        for mid in ids:
            txt = decode_msg(raw, dec, entries, mid, bit_offset)
            print(f"{mid}: {txt[:120].replace(chr(10), '|')}")


if __name__ == "__main__":
    main()
