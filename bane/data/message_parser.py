from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from typing import Dict
import re
import math

from bane.data.huffman import HuffmanDecoder

@dataclass
class MessageEntry:
    id: int
    bank: int
    offset: int
    length_hint: int
    text: str = ""

class MessageParser:
    """Parses Wizardry 6 message databases (MSG.DBS / MSG.HDR)."""

    def __init__(self, tree_path: Path | str):
        self.decoder = HuffmanDecoder.from_file(tree_path)
        self.messages: Dict[int, MessageEntry] = {}
        self._dbs_raw: bytes = b""

    def load(
        self,
        dbs_path: Path | str,
        hdr_path: Path | str,
        backend: str = "raw",
    ) -> Dict[int, str]:
        """Load and decompress all messages from the database.

        Args:
            dbs_path: Path to the compressed data file (MSG.DBS).
            hdr_path: Path to the message index file (MSG.HDR).

        Returns:
            A dictionary mapping message IDs to their decoded strings.
        """
        if backend not in {"raw", "readable"}:
            raise ValueError(f"Unsupported backend: {backend}")

        # Parse MSG.HDR to recover (id, bank, offset, length).
        self._parse_hdr(Path(hdr_path))
        # Decode MSG.DBS into message banks and extract by header coordinates.
        banks = self._decode_dbs_banks(Path(dbs_path))

        # Build per-bank offset order so message text spans to the next offset in
        # the same bank. The low byte in MSG.HDR's third word is not a reliable
        # literal byte length for many entries.
        entries_by_bank: Dict[int, list[MessageEntry]] = {}
        for entry in self.messages.values():
            entries_by_bank.setdefault(entry.bank, []).append(entry)
        for bank_entries in entries_by_bank.values():
            bank_entries.sort(key=lambda e: e.offset)

        next_offset_by_id: Dict[int, int] = {}
        for bank, bank_entries in entries_by_bank.items():
            bank_limit = len(banks[bank]) if bank < len(banks) else 0
            for i, entry in enumerate(bank_entries):
                end = bank_limit
                for j in range(i + 1, len(bank_entries)):
                    if bank_entries[j].offset > entry.offset:
                        end = bank_entries[j].offset
                        break
                next_offset_by_id[entry.id] = end

        ordered_ids = list(self.messages.keys())
        result = {}
        for msg_id, entry in self.messages.items():
            offset = entry.offset
            end = next_offset_by_id.get(msg_id, offset + entry.length_hint)

            if entry.bank >= len(banks):
                continue
            bank_data = banks[entry.bank]
            if offset < 0 or end > len(bank_data):
                continue

            # Decode one or more compressed records whose starts fall in
            # [offset, end). Records are 1-byte length-prefixed payloads.
            abs_start = entry.bank * 1024 + offset
            abs_end = entry.bank * 1024 + end
            text = self._decode_records_abs_range(abs_start, abs_end)
            if backend == "readable":
                text = self._stitch_continuations(
                    msg_id=msg_id,
                    base_text=text,
                    ordered_ids=ordered_ids,
                    next_offset_by_id=next_offset_by_id,
                    banks=banks,
                )
                text = self._normalize_stage2_text(text)
            entry.text = text
            result[msg_id] = text

        return result

    def _stitch_continuations(
        self,
        msg_id: int,
        base_text: str,
        ordered_ids: list[int],
        next_offset_by_id: Dict[int, int],
        banks: list[bytes],
    ) -> str:
        """Stitch likely continuation fragments across bank boundaries.

        Some records near the end of a bank continue in very early offsets of
        the next bank and subsequent nearby records.
        """
        entry = self.messages[msg_id]
        if entry.bank >= len(banks):
            return base_text

        parts: list[str] = [base_text]
        idx = ordered_ids.index(msg_id)
        stitched_cross_bank = False

        # For short entries, decode a small number of sequential records
        # directly from the entry pointer. This captures split fragments
        # when the next HDR offset is too close.
        if 1 < entry.length_hint <= 3 and len(base_text) < 80:
            seq = self._decode_n_records_from_pointer(
                banks=banks,
                start_bank=entry.bank,
                start_offset=entry.offset,
                record_count=entry.length_hint + 1,
            )
            if len(seq) > len(base_text):
                parts = [seq]

        # If this entry is near bank end and next record starts early in the
        # next bank, append the leading bytes before that next offset.
        if entry.offset >= 960 and idx + 1 < len(ordered_ids):
            next_id = ordered_ids[idx + 1]
            next_entry = self.messages[next_id]
            if (
                next_entry.bank == entry.bank + 1
                and next_entry.bank < len(banks)
                and 0 < next_entry.offset <= 64
            ):
                carry = self._decode_records_abs_range(
                    next_entry.bank * 1024,
                    next_entry.bank * 1024 + next_entry.offset,
                )
                merged = self._append_with_overlap("".join(parts), carry)
                parts = [merged]
                stitched_cross_bank = True

                # Append a few early continuation entries from that next bank.
                for j in range(idx + 1, min(idx + 2, len(ordered_ids))):
                    cid = ordered_ids[j]
                    centry = self.messages[cid]
                    if centry.bank != next_entry.bank or centry.offset > 256:
                        break
                    cend = next_offset_by_id.get(cid, centry.offset + centry.length_hint)
                    if cend <= centry.offset or cend > len(banks[next_entry.bank]):
                        continue
                    seg = self._decode_records_abs_range(
                        next_entry.bank * 1024 + centry.offset,
                        next_entry.bank * 1024 + cend,
                    )
                    joined = self._append_with_overlap("".join(parts), seg)
                    parts = [joined]
                    # Stop once we have a complete ellipsis-terminated sentence.
                    if len(joined) >= 120 and "..." in joined:
                        break

        joined = "".join(parts)
        if stitched_cross_bank and len(joined) >= 120:
            ell = joined.find("...")
            if 0 <= ell <= 420:
                joined = joined[: ell + 3]
        return joined

    def _append_with_overlap(self, base: str, seg: str) -> str:
        """Append seg to base with suffix/prefix overlap deduplication."""
        if not seg:
            return base
        if not base:
            return seg
        if seg in base:
            return base

        max_olap = min(len(base), len(seg), 256)
        olap = 0
        for k in range(max_olap, 0, -1):
            if base.endswith(seg[:k]):
                olap = k
                break
        return base + seg[olap:]

    def _decode_n_records_from_pointer(
        self,
        banks: list[bytes],
        start_bank: int,
        start_offset: int,
        record_count: int,
    ) -> str:
        """Decode N sequential Huffman records from a bank pointer."""
        data = self._dbs_raw
        if not data:
            return ""
        pos = start_bank * 1024 + start_offset
        payloads: list[bytes] = []
        decoded = 0
        while decoded < record_count and pos + 1 <= len(data):
            clen = data[pos]
            pos += 1
            if clen == 0:
                break
            if pos + clen > len(data):
                break
            payloads.append(data[pos : pos + clen])
            pos += clen
            decoded += 1

        pieces = self._decode_record_sequence(payloads)
        return self._join_record_fragments(pieces)

    def _normalize_stage2_text(self, text: str) -> str:
        """Apply conservative readability cleanup to stage-2 token text."""
        cleaned = self._interpret_control_stream(text)
        # Remove marker-only runs like EEETEEET..., IEEE..., TITI...
        cleaned = re.sub(r"(?<![A-Z])[EIT]{4,}(?![A-Z])", " ", cleaned)
        # Collapse repeated whitespace/newlines.
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        # Choose a structural start point from message-script markers.
        start = self._find_structural_start(cleaned)
        if start > 0:
            cleaned = cleaned[start:]

        # Common stage-2 OCR/token artifacts observed across many strings.
        replacements = [
            (r"@\s+[A-Z]{1,4}R{1,3}\.\s+", "@ "),
            (r"\b([A-Z])\1{3,}\b", r"\1"),
            (r"\s+\.\s*", ". "),
            (r"\s+,", ","),
            # Remove sentinel-like trailing E after punctuation.
            (r"([.!?])E(\s|$)", r"\1\2"),
        ]
        for pattern, repl in replacements:
            cleaned = re.sub(pattern, repl, cleaned)

        # Remove obvious marker-heavy garbage tokens left after normalization.
        pieces: list[str] = []
        for token in cleaned.split():
            core = re.sub(r"[^A-Z0-9\^]", "", token)
            if re.fullmatch(r"(?:EO){2,}X?", core):
                continue
            if len(core) >= 4 and core.count("E") >= len(core) - 1:
                continue
            pieces.append(token)
        cleaned = " ".join(pieces)

        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
        cleaned = re.sub(r"\b([A-Z]{1,2})$", "", cleaned).rstrip()
        cleaned = self._trim_structural_tail(cleaned)

        return cleaned

    def _trim_structural_tail(self, text: str) -> str:
        """Trim likely spillover into a following dialog block.

        Some decoded spans run past the intended message boundary and begin a
        second top-level `YOU@` topic. Keep the first block when that pattern
        appears after substantial content.
        """
        if text.startswith("YOU@"):
            starts = [m.start() for m in re.finditer(r"\bYOU@\s", text)]
            if len(starts) >= 2:
                second = starts[1]
                if second >= 280:
                    return text[:second].rstrip()

        # Some endings/scripts terminate at an ellipsis and then immediately
        # transition into a marker-heavy new block. Keep the first block.
        for m in re.finditer(r"\.\.\.", text):
            tail = text[m.end() : m.end() + 96]
            if re.match(r"\s*(?:[A-Z]{1,3}\s+){1,5}[A-Z]{5,}\b", tail):
                return text[: m.end()].rstrip()
        # Stop at explicit "YOUR/HOUR MIND..." ending when trailing garbage
        # remains in the same span.
        for marker in ("YOUR MIND...", "@OUR MIND...", "HOUR MIND..."):
            idx = text.find(marker)
            if idx >= 0:
                return text[: idx + len(marker)].rstrip()
        return text

    def _interpret_control_stream(self, text: str) -> str:
        """Interpret message control markers used by the original renderer."""
        out: list[str] = []
        for ch in text:
            code = ord(ch)
            if code == 0x1F:
                out.append("\n\n")
                continue
            if code < 32:
                out.append(" ")
                continue
            if ch == "!":
                out.append("\n\n")
                continue
            if ch == "%":
                out.append("\n\n")
                continue
            if ch == "$":
                out.append("\n")
                continue
            if ch == "@":
                prev_char = ""
                if out:
                    prev_char = out[-1][-1] if out[-1] else ""
                # Keep inline tags like YOU@ intact; otherwise treat @ as a
                # paragraph/topic marker.
                if prev_char and prev_char.isalpha():
                    out.append("@ ")
                    continue
                if out and not out[-1].endswith("\n"):
                    out.append("\n")
                out.append("@")
                continue
            if ch == "^":
                out.append("^")
                continue
            out.append(ch)

        cleaned = "".join(out)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned

    def _find_structural_start(self, text: str) -> int:
        """Find a generic script start position without ID/content hardcoding."""
        # Keep already-sentence-like starts intact.
        if re.match(r"^[A-Z][A-Z ',\-]{12,}", text):
            return 0

        candidates: list[tuple[int, int]] = []

        for marker, weight in (
            ("YOU@ ", 4),
            ("YOU@", 4),
            ("YOU @", 4),
            ("* * *", 4),
            ("^HEAVY ", 4),
            ("\"", 1),
        ):
            pos = text.find(marker)
            if 0 <= pos <= 260:
                candidates.append((weight, pos))

        # Also consider first strong sentence-like start.
        m = re.search(r"(?:^|[\.\!\?]\s+)([A-Z][A-Z '\"]{12,})", text)
        if m:
            sent_pos = m.start(1)
            if 0 <= sent_pos <= 260:
                candidates.append((1, sent_pos))

        if not candidates:
            return 0
        max_weight = max(weight for weight, _ in candidates)
        return min(pos for weight, pos in candidates if weight == max_weight)

    def _decode_dbs_banks(self, path: Path) -> list[bytes]:
        """Load MSG.DBS as fixed-size compressed banks.

        Wizardry 6 MSG.DBS is exactly 80 * 1024 bytes. MSG.HDR entries encode the
        source bank in the high byte of the third word.
        """
        data = path.read_bytes()
        self._dbs_raw = data
        bank_size = 1024
        if len(data) % bank_size != 0:
            raise ValueError(
                f"Unexpected MSG.DBS size {len(data)} (not a multiple of {bank_size})"
            )

        banks: list[bytes] = []
        for i in range(0, len(data), bank_size):
            banks.append(data[i : i + bank_size])
        return banks

    def _decode_records_abs_range(self, abs_start: int, abs_end: int) -> str:
        """Decode records whose starts fall within [abs_start, abs_end)."""
        data = self._dbs_raw
        if not data:
            return ""
        pos = max(0, abs_start)
        end = min(len(data), abs_end)
        payloads: list[bytes] = []

        while pos + 1 <= len(data):
            record_start = pos
            if record_start >= end:
                break
            clen = data[pos]
            pos += 1
            if clen == 0:
                break
            if pos + clen > len(data):
                break
            payloads.append(data[pos : pos + clen])
            pos += clen

        pieces = self._decode_record_sequence(payloads)
        return self._join_record_fragments(pieces)

    def _join_record_fragments(self, pieces: list[str]) -> str:
        """Join decoded record fragments with boundary-marker cleanup."""
        if not pieces:
            return ""

        fixed: list[str] = []
        for i, piece in enumerate(pieces):
            cur = piece
            if i + 1 < len(pieces):
                nxt = pieces[i + 1]
                # Many records terminate with sentinel E marker before the
                # next text fragment starts. Trim that boundary marker.
                if cur.endswith("EE") and nxt and nxt[0] in " !@#$%^\"'(":
                    cur = cur[:-1]
                # WROOT decodes fixed-width records; boundaries often need an
                # implicit space when both ends are alphanumeric.
                if (
                    cur
                    and nxt
                    and cur[-1].isalnum()
                    and nxt[0].isalnum()
                    and not cur.endswith("^")
                ):
                    cur += " "
            fixed.append(cur)
        return "".join(fixed)

    def _decode_record_payload_candidates(self, comp: bytes) -> list[tuple[int, str]]:
        """Decode one payload using WROOT's `29D9` format.

        Record payload format:
        - byte 0: decoded output length
        - bytes 1..: Huffman bitstream
        """
        if not comp:
            return [(0, "")]
        out_len = comp[0]
        text = self.decoder.decode(comp[1:], out_len).decode("ascii", errors="replace")
        return [(0, text)]

    def _decode_record_sequence(self, payloads: list[bytes]) -> list[str]:
        """Choose bit offsets across a record sequence using transition scoring.

        The game's stage-2 stream can be bit-shifted at record boundaries.
        A sequence optimizer outperforms greedy per-record selection because
        neighboring fragments constrain boundary plausibility.
        """
        if not payloads:
            return []

        candidates = [self._decode_record_payload_candidates(comp) for comp in payloads]
        n = len(candidates)
        k = 8
        dp = [[-math.inf] * k for _ in range(n)]
        parent = [[-1] * k for _ in range(n)]

        for off, text in candidates[0]:
            dp[0][off] = self._score_record_text(text)

        for i in range(1, n):
            for off, text in candidates[i]:
                node = self._score_record_text(text)
                best_score = -math.inf
                best_prev = 0
                for prev_off, prev_text in candidates[i - 1]:
                    trans = self._score_record_transition(prev_text, text)
                    # Small inertia reduces offset flapping between records.
                    if prev_off != off:
                        trans -= 0.35
                    cand_score = dp[i - 1][prev_off] + node + trans
                    if cand_score > best_score:
                        best_score = cand_score
                        best_prev = prev_off
                dp[i][off] = best_score
                parent[i][off] = best_prev

        last_off = max(range(k), key=lambda off: dp[n - 1][off])
        path = [last_off]
        for i in range(n - 1, 0, -1):
            path.append(parent[i][path[-1]])
        path.reverse()

        chosen: list[str] = []
        for i, off in enumerate(path):
            chosen.append(candidates[i][off][1])
        return chosen

    def _score_record_transition(self, prev_text: str, next_text: str) -> float:
        """Score plausibility of adjacent decoded fragments."""
        if not prev_text or not next_text:
            return 0.0

        score = 0.0
        a = prev_text[-1]
        b = next_text[0]

        if ord(a) < 32:
            score -= 1.5
        if ord(b) < 32:
            score -= 1.5

        if a.isalpha() and b == " ":
            score += 1.1
        if a.isalpha() and b.isalpha():
            score -= 0.7
        if a in ".!?" and b == " ":
            score += 0.9
        if a == "E" and b == " ":
            score -= 0.6

        seam = (prev_text[-4:] + next_text[:4]).replace("\n", " ")
        if "EEE" in seam or "EOE" in seam or "EET" in seam:
            score -= 0.8
        if re.search(r"[.!?]\s+[A-Z]", seam):
            score += 0.5

        return score

    def _score_record_text(self, text: str) -> float:
        """Quality score for one decoded payload candidate."""
        if not text:
            return -math.inf

        score = 0.0

        # Prefer common words/patterns in game dialog.
        for word in (
            " THE ",
            " YOU ",
            " OF ",
            " AND ",
            " TO ",
            " IN ",
            " IS ",
            " ARE ",
            " WITH ",
            " FOR ",
            " THAT ",
            " CHARRON",
            " RIVER ",
            " STYX",
            "...",
            "@",
            "^",
        ):
            score += text.count(word) * 3.0

        # Penalize typical artifact runs.
        score -= text.count("EEE") * 2.0
        score -= text.count("EET") * 1.5
        score -= text.count("EOE") * 1.5

        nonprint = sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t")
        score -= nonprint * 4.0

        # Prefer payloads that start with a space or uppercase.
        first = text[0]
        if first == " ":
            score += 1.5
        elif "A" <= first <= "Z":
            score += 0.5
        else:
            score -= 1.0

        # Heuristic: strings starting with obvious garbage trigram lose.
        if re.match(r"^[A-Z]{2,3}[!@^]?[A-Z]{0,2}\s", text):
            score -= 1.0
        # Leading injected control letters (" OWORD", " SWORD") are common
        # mis-decodes; prefer cleaner starts when available.
        if re.match(r"^\s[OSR][A-Z]{3,}", text):
            score -= 2.5
        if re.match(r"^\s[A-Z]", text):
            score += 0.8
        if re.match(r"^\s(?:THE|YOU|ARE|I|WE|ON|OF|IN|WITH|AT|TO)\b", text):
            score += 2.0

        return score

    def _parse_hdr(self, path: Path):
        """Parse MSG.HDR triplets to locate messages by bank/offset/length."""
        data = path.read_bytes()
        if len(data) < 2:
            return

        # First u16 is the number of (id, offset, length) entries.
        words = [int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data) - 1, 2)]
        if not words:
            return
        count = words[0]

        self.messages.clear()
        i = 1
        for _ in range(count):
            if i + 2 >= len(words):
                break
            msg_id = words[i]
            offset = words[i + 1]
            packed = words[i + 2]
            bank = (packed >> 8) & 0xFF
            length = packed & 0xFF
            self.messages[msg_id] = MessageEntry(
                id=msg_id,
                bank=bank,
                offset=offset,
                length_hint=length,
            )
            i += 3

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
