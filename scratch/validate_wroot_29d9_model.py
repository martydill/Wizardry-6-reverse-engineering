from pathlib import Path
import re

from bane.data.huffman import HuffmanDecoder


def parse_hdr_entries():
    hdr = Path("gamedata/MSG.HDR").read_bytes()
    words = [int.from_bytes(hdr[i : i + 2], "little") for i in range(0, len(hdr) - 1, 2)]
    count = words[0]
    i = 1
    entries = []
    for _ in range(count):
        msg_id = words[i]
        off = words[i + 1]
        packed = words[i + 2]
        entries.append((msg_id, (packed >> 8) & 0xFF, off, packed & 0xFF))
        i += 3
    return entries


def decode_msg(msg_id: int, raw: bytes, entries, decoder: HuffmanDecoder) -> str:
    by = {e[0]: e for e in entries}
    by_bank = {}
    for e in entries:
        by_bank.setdefault(e[1], []).append(e)
    for b in by_bank:
        by_bank[b].sort(key=lambda x: x[2])

    bank = by[msg_id][1]
    off = by[msg_id][2]
    arr = by_bank[bank]
    idx = [k for k, e in enumerate(arr) if e[0] == msg_id][0]
    end = 1024
    for j in range(idx + 1, len(arr)):
        if arr[j][2] > off:
            end = arr[j][2]
            break

    pos = bank * 1024 + off
    abs_end = bank * 1024 + end
    parts = []
    while pos < abs_end:
        rec_len = raw[pos]
        pos += 1
        if rec_len == 0 or pos + rec_len > len(raw):
            break
        payload = raw[pos : pos + rec_len]
        pos += rec_len
        if not payload:
            continue
        out_len = payload[0]
        comp = payload[1:]
        decoded = decoder.decode(comp, out_len)
        parts.append(decoded.decode("ascii", errors="replace"))

    text = "".join(parts)
    text = text.replace("!", "\n\n").replace("%", "\n\n").replace("$", "\n")
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def main() -> None:
    raw = Path("gamedata/MSG.DBS").read_bytes()
    entries = parse_hdr_entries()
    decoder = HuffmanDecoder.from_file("gamedata/MISC.HDR")
    for mid in (12100, 12560, 10010, 10030, 8200, 18950, 100):
        text = decode_msg(mid, raw, entries, decoder)
        print(f"\nID {mid} len={len(text)}")
        print(text[:900].replace("\n", "\\n"))


if __name__ == "__main__":
    main()
