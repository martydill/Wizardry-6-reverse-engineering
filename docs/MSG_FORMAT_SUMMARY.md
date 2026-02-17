# Wizardry 6 Message Loading Notes

## Current Proven Structure

### MISC.HDR
- Huffman tree, 256 nodes, 4 bytes per node (`<hh>` children).

### MSG.DBS
- Size is exactly `81920` bytes (`80 * 1024`).
- Treat as 80 fixed compressed banks of 1024 bytes each.

### MSG.HDR
- 16-bit words.
- `word[0] = 718` message records.
- Then 718 triplets:
  - `id`
  - `offset`
  - `packed`
- `packed` splits as:
  - `bank = packed >> 8`
  - `length = packed & 0xFF`
- Banks observed in header: `0..79` (all 80 banks referenced).

## Runtime Extraction (Implemented)

1. Decode each `MSG.DBS` 1KB bank with the Huffman tree from `MISC.HDR`.
2. Parse `MSG.HDR` triplets into `(id, bank, offset, length)`.
3. For each bank, sort message entries by offset and span each message to the
   next higher offset in that bank (fallback to bank end).
4. Return `decoded_bank[bank][offset:next_offset]` as stage-2 message slices.

This runtime path uses only original game assets (no bundled clean-text map).

This resolves major truncation issues:
- `msg 8200` now expands to a large Charron dialog block instead of a 74-byte
  fragment ending at `"FE"`.
- `msg 10010` now expands beyond a 2-byte fragment.

## WROOT/WINIT Evidence

- `WROOT.EXE` contains `MSG.DBS`, `DISK.HDR`, `SCENARIO.DBS` strings.
- `WINIT.OVR` contains `MSG.HDR`, `MISC.HDR`, `MSG.DBS`.
- `WINIT.OVR` has a contiguous asset filename table including:
  - `DISK.HDR`
  - `MSG.HDR`
  - `MISC.HDR`
  - `MSG.DBS`
  - `SCENARIO.DBS`

This matches message loading being orchestrated via startup/overlay asset tables.

## What Is Still Unsolved

- Stage-1 extracted text is tokenized and not fully user-readable.
- IDs such as `10010` decode to short token bytes (for example `"BO"`), implying a second-stage interpreter/expander.
- The second-stage control/token expansion logic is likely implemented in executable/overlay code and is not yet replicated.
