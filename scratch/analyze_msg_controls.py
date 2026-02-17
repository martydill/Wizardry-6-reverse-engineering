from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from bane.data.message_parser import MessageParser


def main() -> None:
    parser = MessageParser("gamedata/MISC.HDR")
    parser._parse_hdr(Path("gamedata/MSG.HDR"))
    banks = parser._decode_dbs_banks(Path("gamedata/MSG.DBS"))

    entries_by_bank: dict[int, list] = defaultdict(list)
    for entry in parser.messages.values():
        entries_by_bank[entry.bank].append(entry)
    for bank_entries in entries_by_bank.values():
        bank_entries.sort(key=lambda e: e.offset)

    next_offset_by_id: dict[int, int] = {}
    for bank, bank_entries in entries_by_bank.items():
        bank_limit = len(banks[bank])
        for i, entry in enumerate(bank_entries):
            end = bank_limit
            for j in range(i + 1, len(bank_entries)):
                if bank_entries[j].offset > entry.offset:
                    end = bank_entries[j].offset
                    break
            next_offset_by_id[entry.id] = end

    data = parser._dbs_raw
    zero_hints = Counter()
    ctrl_chars = Counter()
    sample_msgs: dict[int, list[int]] = {}

    for msg_id, entry in parser.messages.items():
        start = entry.bank * 1024 + entry.offset
        end = entry.bank * 1024 + next_offset_by_id[msg_id]
        pos = start
        msg_zero_hints: list[int] = []

        while pos + 2 <= len(data) and pos < end:
            clen = data[pos]
            hint = data[pos + 1]
            pos += 2

            if clen == 0:
                zero_hints[hint] += 1
                msg_zero_hints.append(hint)
                continue

            payload = data[pos : pos + clen]
            pos += clen
            decoded = parser.decoder.decode(payload, 65535)
            for b in decoded:
                if b < 32:
                    ctrl_chars[b] += 1

        if msg_zero_hints:
            sample_msgs[msg_id] = msg_zero_hints

    print("Top zero-length record hints:")
    for hint, count in zero_hints.most_common(20):
        print(f"  hint={hint:3d} count={count}")

    print("\nTop decoded control bytes (<32):")
    for b, count in ctrl_chars.most_common(20):
        print(f"  byte={b:3d} count={count}")

    print("\nSample messages with zero-length hints:")
    for msg_id in (8200, 18950, 10010, 10030):
        print(f"  {msg_id}: {sample_msgs.get(msg_id)}")


if __name__ == "__main__":
    main()
