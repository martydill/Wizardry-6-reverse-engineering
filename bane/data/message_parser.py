from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict

from bane.data.huffman import HuffmanDecoder


@dataclass
class MessageEntry:
    id: int
    bank: int
    offset: int
    id_span: int
    range_index: int
    text: str = ""


class MessageParser:
    """Parses Wizardry 6 message databases (MSG.DBS / MSG.HDR)."""

    def __init__(self, tree_path: Path | str):
        self.decoder = HuffmanDecoder.from_file(tree_path)
        self.messages: Dict[int, MessageEntry] = {}
        self._ranges: list[MessageEntry] = []
        self._dbs_raw: bytes = b""

    def load(
        self,
        dbs_path: Path | str,
        hdr_path: Path | str,
        backend: str = "raw",
    ) -> Dict[int, str]:
        """Load messages indexed by MSG.HDR start IDs.

        Runtime model mirrored from WROOT:
        - MSG.HDR entry = (start_id, start_offset, id_span, bank)
        - each record in MSG.DBS = [u8 record_len][record payload]
        - record payload format = [u8 decoded_len][Huffman bits]
        - msg_id in range is found by stepping (msg_id - start_id) records.
        """
        if backend not in {"raw", "readable"}:
            raise ValueError(f"Unsupported backend: {backend}")

        self._parse_hdr(Path(hdr_path))
        self._decode_dbs_banks(Path(dbs_path))

        id_to_ptr = self._build_id_record_ptrs()
        decoded_by_id = {msg_id: self._decode_record_at(ptr) for msg_id, ptr in id_to_ptr.items()}

        result: Dict[int, str] = {}
        for entry in self._ranges:
            text = self._compose_range_text(entry, decoded_by_id)
            if backend == "readable":
                text = self._normalize_readable_text(text)
            entry.text = text
            result[entry.id] = text

        return result

    def _decode_dbs_banks(self, path: Path) -> list[bytes]:
        """Validate and cache MSG.DBS as fixed-size 1KB banks."""
        data = path.read_bytes()
        self._dbs_raw = data
        bank_size = 1024
        if len(data) % bank_size != 0:
            raise ValueError(
                f"Unexpected MSG.DBS size {len(data)} (not a multiple of {bank_size})"
            )
        return [data[i : i + bank_size] for i in range(0, len(data), bank_size)]

    def _parse_hdr(self, path: Path) -> None:
        """Parse MSG.HDR triplets into start-ID range descriptors."""
        data = path.read_bytes()
        words = [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data) - 1, 2)]
        if not words:
            return

        count = words[0]
        self.messages.clear()
        self._ranges.clear()

        i = 1
        for range_index in range(count):
            if i + 2 >= len(words):
                break
            start_id = words[i]
            start_offset = words[i + 1]
            packed = words[i + 2]
            bank = (packed >> 8) & 0xFF
            id_span = packed & 0xFF
            entry = MessageEntry(
                id=start_id,
                bank=bank,
                offset=start_offset,
                id_span=id_span,
                range_index=range_index,
            )
            self._ranges.append(entry)
            self.messages[start_id] = entry
            i += 3

    def _build_id_record_ptrs(self) -> Dict[int, int]:
        """Build absolute record pointers for every in-range message ID."""
        data = self._dbs_raw
        out: Dict[int, int] = {}
        for entry in self._ranges:
            pos = entry.bank * 1024 + entry.offset
            for delta in range(entry.id_span + 1):
                msg_id = entry.id + delta
                if pos >= len(data):
                    break
                out[msg_id] = pos
                if delta < entry.id_span:
                    pos = self._next_record_ptr(pos)
        return out

    def _next_record_ptr(self, pos: int) -> int:
        """Return pointer to the next length-prefixed record."""
        data = self._dbs_raw
        if pos >= len(data):
            return len(data)
        record_len = data[pos]
        return min(len(data), pos + 1 + record_len)

    def _decode_record_at(self, pos: int) -> str:
        """Decode one [len][payload] record at an absolute MSG.DBS pointer."""
        data = self._dbs_raw
        if pos >= len(data):
            return ""
        record_len = data[pos]
        start = pos + 1
        end = start + record_len
        if record_len == 0 or end > len(data):
            return ""
        payload = data[start:end]
        if not payload:
            return ""

        decoded_len = payload[0]
        bitstream = payload[1:]
        decoded = self.decoder.decode(bitstream, decoded_len)
        return decoded.decode("ascii", errors="replace")

    def _compose_range_text(self, entry: MessageEntry, decoded_by_id: Dict[int, str]) -> str:
        """Join all sub-IDs from one header range.

        A small subset of ranges continue at the start of the next bank. We
        stitch those only when the two adjacent ranges are contiguous by ID and
        exhibit the near-end/near-start bank-offset pattern.
        """
        parts: list[str] = []
        parts.extend(decoded_by_id.get(msg_id, "") for msg_id in range(entry.id, entry.id + entry.id_span + 1))

        idx = entry.range_index
        while idx + 1 < len(self._ranges):
            cur = self._ranges[idx]
            nxt = self._ranges[idx + 1]
            contiguous_ids = nxt.id == cur.id + cur.id_span + 1
            bank_wrap = nxt.bank == cur.bank + 1 and cur.offset >= 960 and nxt.offset <= 64
            if not (contiguous_ids and bank_wrap):
                break
            parts.extend(
                decoded_by_id.get(msg_id, "")
                for msg_id in range(nxt.id, nxt.id + nxt.id_span + 1)
            )
            idx += 1

        return self._join_fragments(parts)

    def _join_fragments(self, parts: list[str]) -> str:
        """Join decoded fragments and restore implicit boundary spaces."""
        out = ""
        for part in parts:
            if not part:
                continue
            if not out:
                out = part
                continue
            prev = out[-1]
            nxt = part[0]
            if prev == "@" and nxt.isalnum():
                out += " "
            elif prev.isalnum() and nxt.isalnum() and prev != "^":
                out += " "
            out += part
        return out

    def _normalize_readable_text(self, text: str) -> str:
        cleaned = self._interpret_control_stream(text)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = re.sub(r"\s+,", ",", cleaned)
        cleaned = re.sub(r"\s+\.", ".", cleaned)
        return cleaned.strip()

    def _interpret_control_stream(self, text: str) -> str:
        """Interpret control markers used by the original message renderer."""
        out: list[str] = []
        for ch in text:
            code = ord(ch)
            if code == 0x1F:
                out.append("\n\n")
                continue
            if code in (0x1E, 0x0E):
                out.append(" ")
                continue
            if code < 32:
                out.append(" ")
                continue
            if ch in ("!", "%"):
                out.append("\n\n")
                continue
            if ch == "$":
                out.append("\n")
                continue
            if ch == "@":
                prev_char = ""
                if out:
                    prev = out[-1]
                    prev_char = prev[-1] if prev else ""
                if prev_char.isalnum():
                    out.append("@")
                    continue
                if out and not out[-1].endswith("\n"):
                    out.append("\n")
                out.append("@")
                continue
            out.append(ch)
        return "".join(out)


def load_messages(
    gamedata_dir: str | Path,
    prefix: str = "MSG",
    tree_file: str = "MISC.HDR",
    backend: str = "raw",
) -> Dict[int, str]:
    """Helper to load a message set from the gamedata directory."""
    base_path = Path(gamedata_dir)
    parser = MessageParser(base_path / tree_file)
    return parser.load(
        base_path / f"{prefix}.DBS",
        base_path / f"{prefix}.HDR",
        backend=backend,
    )
