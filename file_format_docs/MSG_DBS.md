# MSG.DBS / MSG.HDR File Format — Game Messages

Applies to: `MSG.DBS`, `MSG.HDR`, `MISC.HDR`

## Overview

The Wizardry 6 message system uses three files together:

| File       | Role                                                          |
|------------|---------------------------------------------------------------|
| `MISC.HDR` | Huffman decode tree (shared by all message banks)            |
| `MSG.HDR`  | Index: maps message IDs to locations within MSG.DBS           |
| `MSG.DBS`  | Body: Huffman-compressed message records, laid out in 1KB banks |

Messages are identified by integer IDs (e.g. `10010`). A message ID is looked up in
`MSG.HDR` to find which bank and offset in `MSG.DBS` holds its compressed record, then
decoded using the Huffman tree from `MISC.HDR`.

---

## File 1: MISC.HDR — Huffman Tree

`MISC.HDR` contains the canonical Huffman tree used to decompress all message records.

### Structure

The file is a flat array of **4-byte nodes**, read from byte 0:

```
Node N at byte offset N×4:
  Bytes 0–1: left_child   (LE signed int16)
  Bytes 2–3: right_child  (LE signed int16)
```

Each node has two child references, one for bit=0 (left) and one for bit=1 (right):

- **Negative value** (e.g. `-3`): internal node pointer — follow to node index `-value`
  (e.g. `-3` → node 3)
- **Non-negative value**: leaf — emit `value & 0xFF` as the decoded byte and reset to
  root (node 0)

The tree typically fits in **1024 bytes = 256 nodes**.

### Decoding algorithm

Bits are consumed **MSB-first** from each byte of the compressed bitstream:

```python
bit = (compressed_byte >> (7 - bit_index)) & 1
```

Starting at node 0, follow left (bit=0) or right (bit=1) child at each step.
On reaching a leaf (non-negative child value), emit that byte and reset to node 0.
Stop after `uncompressed_len` bytes have been emitted.

---

## File 2: MSG.HDR — Message Index

`MSG.HDR` is a compact index that maps message IDs to their locations in `MSG.DBS`.

### Structure

The file is a sequence of **LE16 words** (2 bytes each):

```
Offset  Field    Description
------  -----    -----------
0       count    Number of range entries that follow
```

Then `count` range entries, each **3 words (6 bytes)**:

```
Word 0  start_id      First message ID covered by this range
Word 1  start_offset  Byte offset within the bank where the first record begins
Word 2  packed        High byte = bank index, Low byte = id_span
```

Unpacking word 2:
- `bank     = (packed >> 8) & 0xFF` — which 1KB bank in MSG.DBS (bank N starts at `N × 1024`)
- `id_span  = packed & 0xFF` — number of additional IDs beyond `start_id` (inclusive count = `id_span + 1`)

A single range entry covers message IDs `start_id` through `start_id + id_span` (inclusive).
Their records appear **consecutively** in MSG.DBS starting at `bank × 1024 + start_offset`.

### Bank wrapping

Occasionally a long message spans a bank boundary. In that case two adjacent range entries
are stitched together when:
- Their IDs are contiguous (`next.start_id == cur.start_id + cur.id_span + 1`)
- The current range ends near the end of its bank (`cur.start_offset >= 960`)
- The next range starts near the beginning of the next bank (`next.start_offset <= 64`)
- The banks are consecutive (`next.bank == cur.bank + 1`)

---

## File 3: MSG.DBS — Compressed Message Records

`MSG.DBS` is a flat byte array organized as **fixed-size 1KB (1024-byte) banks**.
File size must be an exact multiple of 1024.

```
Bank 0: bytes    0 –  1023
Bank 1: bytes 1024 –  2047
Bank 2: bytes 2048 –  3071
...
```

### Record Format

Each record within a bank is **length-prefixed**:

```
Offset  Size   Field          Description
------  ----   -----          -----------
0       1      record_len     Total byte length of the payload that follows
1       1      decoded_len    Number of bytes the Huffman bitstream will expand to
2       …      bitstream      Huffman-compressed data (record_len - 1 bytes)
```

Total record size in file: `1 + record_len` bytes.

Records are packed consecutively; to advance to the next record, skip `1 + record_len` bytes
from the start of the current record:

```python
next_pos = current_pos + 1 + data[current_pos]
```

A `record_len` of 0 means an empty/missing message.

### Locating a message record

Given a message ID `msg_id`:

1. Find the range entry in MSG.HDR where `start_id <= msg_id <= start_id + id_span`
2. Compute absolute start position: `pos = bank × 1024 + start_offset`
3. Step forward `(msg_id - start_id)` records, advancing by `1 + record_len` each time
4. `pos` now points to the target record

### Decoding a record

```python
record_len  = data[pos]
decoded_len = data[pos + 1]
bitstream   = data[pos + 2 : pos + 1 + record_len]
text_bytes  = huffman_decode(bitstream, decoded_len)
text        = text_bytes.decode("ascii", errors="replace")
```

---

## Text Encoding and Control Codes

Decoded text is ASCII. The following special byte values are used as inline control codes:

| Character / Code | Raw value | Meaning                                      |
|------------------|-----------|----------------------------------------------|
| `$`              | 0x24      | Newline (line break)                         |
| `!`              | 0x21      | Paragraph break (double newline)             |
| `%`              | 0x25      | Paragraph break (double newline)             |
| `@`              | 0x40      | Speaker/name marker; inserts line break before if mid-sentence |
| `^`              | 0x5E      | Separator; suppresses auto-space at boundary |
| `0x1F`           | —         | Paragraph break (double newline)             |
| `0x1E`           | —         | Space                                        |
| `0x0E`           | —         | Space                                        |
| `< 0x20`         | —         | Any other control byte → rendered as space   |

### Fragment boundary spacing

When a message is assembled from multiple sub-ID fragments, spaces are inserted
automatically between fragments at join points:

- If the previous fragment ends with `@` and the next starts with an alphanumeric → insert space
- If both sides are alphanumeric (and previous does not end with `^`) → insert space

---

## Multi-file Relationship

```
MISC.HDR ──────────────────────────────────► Huffman tree (decode all records)
                                                    ▲
MSG.HDR  ──► range[N]: (start_id, bank, offset, id_span)
                 │                                  │
                 └──► MSG.DBS  bank×1024+offset ───►│
                          [record_len][decoded_len][bitstream] ──► decoded text
```

---

## Decoder Reference

`bane/data/huffman.py` — `HuffmanDecoder`:
- `HuffmanDecoder.from_file(path)` — load tree from MISC.HDR
- `decoder.decode(bitstream, decoded_len)` — returns raw bytes

`bane/data/message_parser.py` — `MessageParser`:
- `_parse_hdr(path)` — parses MSG.HDR into range entries
- `_decode_dbs_banks(path)` — validates and caches MSG.DBS (must be multiple of 1024)
- `_build_id_record_ptrs()` — walks each range, stepping record-by-record to build `{msg_id: abs_offset}`
- `_decode_record_at(pos)` — extracts `[record_len][decoded_len][bitstream]`, calls Huffman decoder
- `_compose_range_text()` — stitches sub-ID fragments and handles bank-wrap continuation
- `load_messages(gamedata_dir)` — convenience wrapper loading all three files

## Viewer

```
python -m loaders.message_parser 10010        # single message by ID
python -m loaders.message_parser              # all messages
python -m loaders.message_parser --search gate
python -m loaders.message_parser --raw        # show raw control codes
python -m loaders.message_parser --output all_messages.txt
```
