# Message RE Stage 2 Notes

## Working overlay mapping

For Wizardry 6 `.OVR` files in this data set, this mapping is currently the
best-fit hypothesis for resolving many near-call targets:

- Logical base address: `0x4572`
- Header/prefix size: `0x00F2`

Practical mapping used for reversing:

- `file_offset = ((logical_addr - 0x4572) & 0xFFFF) + 0x00F2`
- `logical_addr = (0x4572 + (file_offset - 0x00F2)) & 0xFFFF`

It resolves previously "missing" call targets in `WPCVW.OVR` such as:

- `0xBD6E`
- `0xBDA7`
- `0xC1F7`
- `0xDF85`
- `0xFAAB`

## Why this matters

Call sites in overlay code are emitted as 16-bit near-call logical addresses.
Without mapping logical addresses to file offsets, disassembly jumps appear to
leave the file. With the mapping above, these targets resolve inside the file.

## Utility script

Use:

```powershell
python scratch/re_overlay_map.py
```

It will:

- disassemble selected logical targets via the mapping
- find call sites that branch into those targets

## Current status

- Stage-1 Huffman extraction from `MSG.DBS`/`MSG.HDR` is present.
- Stage-2 text expansion remains unresolved and still needs runtime-code tracing.
- Parser code has been stripped of remaining content-specific ID/phrase checks
  so follow-up work can stay algorithmic and data-driven.

## New runtime findings (WROOT + WPCVW)

### `MSG.HDR` low byte semantics

`WROOT` routine around `0x063A` treats each message index entry as:

- `u16 start_id`
- `u16 start_offset`
- `u8 id_span`
- `u8 page`

It checks `start_id <= msg_id <= start_id + id_span`.

This confirms the low byte in packed header words is an ID-span/range field
for lookup, not a literal output-text length.

### Message retrieval path

`WROOT` routine around `0x075B`:

1. Finds an index entry for the requested message ID.
2. Loads the requested 1KB page through `0x06AA`.
3. Starts at `start_offset`.
4. Walks forward by length-prefixed records (`pos += 1 + record_len`) for
   `(msg_id - start_id)` steps.
5. Copies one final length-prefixed record as the message payload.

### Confirmed record layout in `MSG.DBS`

Runtime extraction now matches `WROOT` pointer-walk behavior when each record is
treated as:

- `u8 compressed_len`
- `compressed_len` bytes of Huffman payload

Key evidence from live data:

- Starting at `msg 10010` offset and stepping by `1 + len` lands exactly on the
  next valid records (`896 -> 920 -> 943 -> 967 -> 975` in bank 20).
- Decoding the first record for:
  - `10010` yields `"...APPROACHING THE GATE WITH CONFIDENCE..."`.
  - `10030` yields `"...YOU ARE IN THE ENTRANCE CHAMBER..."`.
  - `18950` yields `"* * * * * * *  B O O  * * * * * * *"`.

This rules out the previous two-byte per-record assumption (`len,hint`) as the
main parser bug.

## New decode-stage findings (WROOT `0x075B` -> `0x29D9`)

### `WROOT:0x075B` full message path

After selecting the record pointer for a requested message ID, `0x075B`:

1. Reads one byte at record start as `record_len`.
2. Copies exactly `record_len` bytes into a stack/temp buffer.
3. Calls `0x29D9(dst, src_record)` to decode to caller output.

So each record is:

- `u8 record_len`
- `record_len` payload bytes

### `WROOT:0x29D9` payload format

`0x29D9` confirms payload structure as:

- byte 0: `decoded_len` (exact output byte count)
- bytes 1..N: Huffman bitstream

It then decodes exactly `decoded_len` bytes using helper `0x2A18` and tree base
at `cs:[0x1B80]`.

This is the runtime decode model used by the game, and explains why previous
"decode-to-exhaustion" attempts produced boundary artifacts.

### Practical impact

Using the exact `29D9` model immediately yields near-clean text for known IDs:

- `100`: `HUMAN ELF DWARF ...`
- `10010`: `APPROACHING THE GATE WITH CONFIDENCE ...`
- `12100`: `A SILENT, MYSTERIOUS DARK MAN APPEARS ... "MAY I INTEREST YOU ..."`
- `12560`: catapult/target paragraph text appears clean
- `18950`: now ends at `...YOUR MIND...` without spillover

## Renderer-stage control handling (`WPCVW`)

### Confirmed text-window printer loop (`WPCVW:0x8DC0`)

`0x8DC0` sets up a text box, loads a message into buffer `0x558E` via call
`0x10677` (wrapped target `0x0677` in resident code path), then iterates bytes
from the current pointer:

- `!` (0x21): consumes marker and advances row
- `@` (0x40): consumes marker and forces row start state (`row=13`)
- `$` (0x24): consumes marker and forces column 1
- `^` (0x5E): consumes marker and reuses prior column

After row/column handling, it draws text at `(row,col)` and calls `0x2405`
per-byte to emit glyphs.

### Important negative finding

Within this printer loop, only `!/@/$/^` are explicitly branched on. No direct
checks for `0x1F`, `0x1E`, or `0x0E` were found in this path.

This matches raw decoded `msg 8200`, which still contains control bytes:

- `0x1F` (seen as topic separator)
- `0x1E`, `0x0E` (rare inline controls near dialogue transitions)

Therefore, interpretation of `0x1F/0x1E/0x0E` is likely done by a different
higher-level script/dialog path (or treated as drawable glyph codes in some UI
contexts), and remains the next RE target.

### Message handle initialization path

`WROOT` around `0x0CD6` builds filenames into buffer `0x35EA` and opens files via
`0x3E88`:

- `0x10DD`: result handle stored to `[0x844]`
- `0x1110`: result handle stored to `[0x842]`

So `0x844/0x842` are not constants; they are runtime-opened file handles.
The filename builder uses:

- source table base `0x3540`
- entry stride `10` bytes
- delimiter `':'` (0x3A), via helper at `0x0C82`

This implies the actual filename table is runtime data-driven (likely loaded/
initialized earlier), and static file bytes at that address in `WROOT.EXE`
cannot be treated as the final table content.

### Renderer control markers

`WPCVW` routine around `0x8E1C` handles line-prefix markers:

- `!` (0x21): advance vertical row
- `@` (0x40): force row 13 behavior
- `$` (0x24): set left column (`1`)
- `^` (0x5E): reuse previous column

This is a layout/printing interpreter, not the unresolved token-expansion
logic that still causes textual garble.
