# WROOT / NEWGAME.DBS Load Path (RE Notes)

## Bottom line

`WROOT.EXE` itself does not contain the `NEWGAME.DBS` filename and does not directly parse map records from it.

`WROOT` provides DOS/overlay/file I/O runtime services.  
`WBASE.OVR` contains the `NEWGAME.DBS` / `SAVEGAME.DBS` names and calls into those `WROOT` services to open/seek/read map-related data.

## Hard evidence

- `WROOT.EXE` string table contains:
  - `SCENARIO.DBS` at file offset `0x10567`
  - `MSG.DBS` at `0x1055F`
  - no `NEWGAME.DBS` / `SAVEGAME.DBS`
- `WBASE.OVR` string table contains:
  - `NEWGAME.DBS` at file offset `0x3A21`
  - `SAVEGAME.DBS` at `0x3A2D`
  - table region starts around `0x39E0`

## Relevant runtime split

- `WROOT.EXE`
  - owns DOS `int 21h` file primitives (open/read/close/seek wrappers and startup I/O)
  - owns overlay/engine infrastructure
- `WBASE.OVR`
  - chooses DB filename(s)
  - opens the DB file handle
  - seeks and reads map-structured chunks
  - closes handle

## WBASE map/data read sequences

### Sequence A: open -> seek(0) -> read header block -> close

Around logical `WBASE:0x7CC9..0x7D4E`:

1. Builds filename text buffer (`call 0x0677`, id `0x08D2`, output at `[bp-0x6e]`).
2. Opens file (`call 0x3DA4`), result in global handle `0x4FEA`.
3. Seeks to start (`call 0x423D` with `origin=0`, offset `0`).
4. Reads `0x019E` bytes into buffer `0x33F8` (`call 0x41F6`).
5. Closes handle (`call 0x4225`).

This matches a DB header/index load step before per-map reads.

### Sequence B: open -> indexed seek -> fixed-size read -> close

Around logical `WBASE:0x500D..0x5086`:

1. Opens DB (`call 0x3DA4`), handle in local `[bp-2]`.
2. Computes per-entry offset from map index:
   - `offset = index * stride * 9`
   - where `stride` is `0x10` or `0x20` (`[bp-0x18]`).
3. Seeks to computed offset (`call 0x423D`).
4. Reads `stride*9` bytes to local buffer (`call 0x41EF`).
5. Closes handle (`call 0x4225`).

This looks like map-record block reads from the DB file.

## WROOT file-I/O disassembly evidence

Using MZ-aware disassembly (`file offset = logical + 0x200`), `WROOT` exposes
the DOS primitives overlays rely on:

- `WROOT:0x42C0` -> `AH=0x3F` (`int 21h`) read wrapper
- `WROOT:0x42C9` -> `AH=0x40` (`int 21h`) write wrapper
- `WROOT:0x4309` -> `AH=0x3E` (`int 21h`) close wrapper
- `WROOT:0x4321` -> `AH=0x42` (`int 21h`) seek wrapper

And startup code has direct open/read/close:

- `WROOT:0x1F43` -> `AH=0x3D` (open), then
- `WROOT:0x1F58` -> `AH=0x3F` (read), then
- `WROOT:0x1F69` -> `AH=0x3E` (close)

This confirms `WROOT` is the file-I/O service layer, while map-specific DB
selection and record addressing remain in overlays.

## Overlay call-ID caveat

In overlay disassembly, calls appear as fixed 16-bit IDs (e.g. `0x3DA4`,
`0x423D`, `0x41EF`, `0x41F6`, `0x4225`). These are overlay-linkage call
targets (thunk/import style) rather than direct file offsets into the `.OVR`
binary image.

Pragmatically: those IDs still map to open/seek/read/close behavior in runtime
flow, but they should not be treated as direct `WBASE.OVR` file offsets.

## Thunk mapping resolved (`overlay_id + 0x00E4`)

For the key service/helper calls used by `WBASE/WMAZE`, overlay call IDs map to
`WROOT` implementations at `id + 0x00E4`.

Confirmed examples:

- `0x3DA4 -> 0x3E88` : open/create mode wrapper
- `0x423D -> 0x4321` : seek (`AH=42`)
- `0x4225 -> 0x4309` : close (`AH=3E`)
- `0x41EF -> 0x42D3` : read via handle struct
- `0x41F6 -> 0x42DA` : write/read companion wrapper in same dispatcher block
- `0x435C -> 0x4440` : memory copy (`rep movs` with overlap handling)
- `0x0677 -> 0x075B` : indexed text/record lookup path
- `0x0BF2 -> 0x0CD6` : filename-build path (`0x35EA` buffer)
- `0x382A -> 0x390E` : string copy helper

This closes the earlier ambiguity about overlay call IDs.

## Bitfield helpers used by WMAZE wall/state updates

With thunk mapping applied:

- `WMAZE call 0x279D` -> `WROOT:0x2881`
  - set/clear one bit in byte-packed bitset:
  - byte index `index >> 3`, bit `(index & 7)`, value from 3rd arg
- `WMAZE call 0x27CB` -> `WROOT:0x28AF`
  - test one bit in byte-packed bitset, returns `AX=0/1`
- `WMAZE call 0x27F6` -> `WROOT:0x28DA`
  - set packed N-bit field in bitstream (`bits_per_entry`, `value`)
- `WMAZE call 0x2841` -> `WROOT:0x2925`
  - read packed N-bit field from bitstream
- `WMAZE call 0x287E` -> `WROOT:0x2962`
  - generic bit-slice extract helper

This is direct code-level proof that `WMAZE` manipulates map state/wall-like
channels as packed bitfields, not as simple per-cell byte structs.

## Packed channel layout recovered in WMAZE

From `WMAZE` callsites (notably `0x4651`, `0x48E8`, `0x53AA`, `0x5613`):

- Index formula used repeatedly:
  - `idx = (block << 6) + (row << 3) + col`
  - (8x8 tile inside one `block`, 64 entries per block)

- Geometry helpers normalize local coords by modulo 8 (`idiv 8`, keep remainder).

### Confirmed packed regions under base pointer `[0x4FAA]`

- `+0x043A`: 1-bit map (`get_bit`), 768 bits total
- `+0x049A`: 1-bit map (`get_bit`), 768 bits total
- `+0x0060`: 2-bit field map (`get_field bits=2`), 768 entries
- `+0x0120`: 2-bit field map (`get_field bits=2`), 768 entries
- `+0x04FA`: 3-bit field map (`get_field/set_field bits=3`), 60 entries
- `+0x0512`: 3-bit field map (`get_field/set_field bits=3`), 60 entries

### Size consistency evidence

- 768 one-bit entries = `0x60` bytes (matches `WMAZE` clears of `0x4E08` and `0x4E68` with size `0x60`)
- 768 two-bit entries = `1536` bits = `0xC0` bytes
  - offset delta `0x120 - 0x60 = 0xC0` matches exactly
- 60 three-bit entries = `180` bits = 23 bytes (24-byte aligned storage plausible)
  - offsets `0x4FA` and `0x512` differ by `0x18` (24 bytes)

### Behavioral interpretation from code flow

- `WMAZE:0x4651`
  - checks/sets a bit in `0x4E08` using normalized `(block,row,col)`
  - when clearing, also clears matching 3-bit coordinate records in `+0x4FA/+0x512`
  - uses 2-bit fields in `+0x60/+0x120` as adjacency/edge tests for propagation
- `WMAZE:0x48E8..0x49CB`
  - builds `0x4E68` bitset from entity tables, then populates `0x4E08` through helper calls
- `WMAZE:0x53AA`
  - mode-based accessor that reads direction/channel data via 2-bit fields (`+0x60` or `+0x120`)

Net: map/wall-related runtime state in `WMAZE` is organized as packed bitplanes
and packed small-width fields over `(block, row, col)` indices, not direct
per-cell byte structs.

## Wall-plane accessor semantics (new)

Further disassembly of `WMAZE` wall accessors clarifies what the two 2-bit
planes represent:

- `base+[0x60]` (2-bit entries): edge state used when moving between
  `(x,y) -> (x,y+1)` (same `x`, next `y`).
- `base+[0x120]` (2-bit entries): edge state used when moving between
  `(x,y) -> (x+1,y)` (next `x`, same `y`).

Key proof points:

- `WMAZE:0x4651` recursion:
  - checks `get_field(+0x60, idx)` before recursing to `y+1`
  - checks `get_field(+0x120, idx)` before recursing to `x+1`
  - checks `get_field(+0x60, idx-8)` for `y-1`
  - checks `get_field(+0x120, idx-1)` for `x-1`
- zero allows propagation; nonzero blocks movement in this flood-style traversal.

This confirms these are the two core wall/blocker edge planes (stored as packed
2-bit fields), with canonical ownership by one side of each adjacency.

### Cross-block neighbor helpers

`WMAZE` wrappers used by `mode 2/3` access (function `0x53AA`) translate across
neighbor blocks:

- `0x7B5D`: resolves `(x, y-1)` via `0x7A37`, then reads `+0x60`
- `0x7BC2`: resolves `(x-1, y)` via `0x7A37`, then reads `+0x120`

These wrappers are exactly the cross-block equivalents of `idx-8` / `idx-1`
lookups used within a block.

### Direction-mode accessor (`WMAZE:0x53AA`)

`0x53AA` is a mode-switched reader over the two edge planes:

- mode `0`: `get_field(+0x60, idx(block,row,col))`
- mode `1`: `get_field(+0x120, idx(block,row,col))`
- mode `2`: `0x7B5D(...)` => `get_field(+0x60, world(x,y-1) resolved via 0x7A37)`
- mode `3`: `0x7BC2(...)` => `get_field(+0x120, world(x-1,y) resolved via 0x7A37)`

So `0x53AA` is the unified "wall-edge in relative direction" primitive used by
higher-level movement/interaction code.

### Coordinate resolver (`WMAZE:0x7A37`)

`0x7A37` resolves world `(x,y)` to:

- `block` (0..11),
- local `col` (0..7),
- local `row` (0..7),

using per-block bounding boxes from:

- `base + 0x1E0 + block` (x-origin),
- `base + 0x1EC + block` (y-origin).

It tries:

1. current block,
2. cached previous block (`0x4FA6`),
3. linear scan over all 12 blocks.

On success it writes normalized locals and block id back through pointer args.

## Important correction on `call 0x001A`

Earlier map-staging notes treated `WMAZE call 0x001A` as a read-like helper.
Disassembly through thunk mapping shows:

- `WMAZE call 0x001A` -> `WROOT:0x00FE`
- `WROOT:0x00FE` forwards to `WROOT:0x387A`
- `WROOT:0x387A` is far `memcpy` (`les:di`, `lds:si`, `rep movsw/movsb`)

So `0x001A` is a memory copy primitive, not file read.

Implication:

- `WMAZE` first resolves/maintains pointer tables (`0x07D2/0x07D4`, `0x080A/0x080C`)
  for map chunks.
- It then copies those chunks into runtime work buffers (`0x4FAA`, `0x4FA8`) via `0x001A`.
- Actual file read/write remains through `0x41EF/0x41F6` wrappers.

## Block permutation/origin arrays (`WMAZE:0x5F8B`) (new)

`WMAZE:0x5F8B..0x6113` performs a block reorder pass over the `0x43E8`
block records (size `0x1B0` each), while carrying companion origin arrays:

- active origins: `0x43DC` / `0x43D0`
- baseline origins: `0x43DE` / `0x43D2`

Observed behavior:

- copies current block records to a large stack scratch area,
- repeatedly selects entries (`0x43CC`) and rotates/compacts block records,
- carries `0x43DC/0x43D0` with the same permutation,
- then restores block records and rewritten origin arrays.

This explains why wall planes are indexed by `(block,row,col)` but still need
runtime block-origin lookup for world-space placement.

Related updater paths:

- `WMAZE:0x63A4..0x6500` periodic block updates call `0x6114` and then `0x4AC4`.
- `WMAZE:0x70A9..0x70F3` movement-tick path also calls `0x6114`.

So world block layout is dynamic and maintained through these routines, not a
single fixed static lookup in `NEWGAME.DBS`.

## Why this matters for `NEWGAME.DBS`

- Since `NEWGAME.DBS` and `SAVEGAME.DBS` strings live in `WBASE.OVR`, the DB chosen for map loading is selected there, not in `WROOT`.
- `WROOT` supplies the generic file operations used by `WBASE`.
- Map decoding/render-time wall logic likely occurs downstream (other `WBASE` routines and/or `WMAZE.OVR`) after these read calls populate runtime buffers.

## Current confidence / gaps

High confidence:
- location of filename ownership (`WBASE`, not `WROOT`)
- file-open/seek/read/close control flow in `WBASE`
- `WROOT` role as service runtime

Still to pin down 100%:
- exact branch that chooses `NEWGAME.DBS` vs `SAVEGAME.DBS` in each game state
- exact in-memory struct layout of each map block after `0x41EF/0x41F6` reads

## WMAZE map staging path (new)

The high-confidence map-load staging routine in `WMAZE.OVR` is around
`0x66C0..0x6AE6` (logical overlay addresses).

### `WMAZE:0x66F7..0x6738` open path

- Builds/open parameters, then calls `0x3DA4` (open-style thunk).
- Stores handle in `[bp-6]`.
- On failure, emits error flow and returns `0xFFFF`.

### `WMAZE:0x673E..0x67F5` initial read

- Seeks to file start via `call 0x423D` with `(handle, 0, 0, origin=0)`.
- Copies 10-byte per-map snapshot:
  - source: `0x33F8 + map_index*10`
  - dest: `0x4EEC + map_index*10`
  - via `call 0x435C` with size `0x000A`
- Reads `0x019E` bytes into `0x33F8` via `call 0x41F6`.
- On read error: closes handle via `0x4225` and returns `0xFFFF`.

### `WMAZE:0x681A..0x6933` per-entry dual-block reads

- Loops `entry = 0 .. [0x3318)-1` (with fast-path split at `<0x0E`).
- Reads two per-entry blocks from file into stack buffers:
  - block A size `[0x3304]` (fallback clear size `0x0542`)
  - block B size `[0x3306]` (fallback clear size `0x06CC`)
- Each read uses `call 0x41F6`; any failure closes handle and returns error.

### `WMAZE:0x69F4..0x6AE6` tail reads

- Reads fixed `0x0042` bytes into local state struct (`[bp-0x48]`).
- Then loops `i = 0 .. [0x43CE)-1`:
  - destination table base `0x43E8 + i*0x1B0`
  - read size `0x01B0` bytes each
- Final close via `0x4225`, return success (`AX=0`).

Interpretation:
- `WBASE` decides which DB is used (`NEWGAME.DBS` vs `SAVEGAME.DBS`).
- `WMAZE` then performs the bulk map/runtime staging reads and buffer copies.
- Wall decode logic consumes these staged buffers, but much of the bit get/set
  behavior appears to go through external thunk calls (IDs below overlay base),
  so those helpers still need explicit runtime/thunk mapping.

## Layout confirmation from current NEWGAME.DBS (new)

Using the recovered loader constants:

- header: `0x019E`
- map chunk A: `0x0542`
- map chunk B: `0x06CC`
- map stride: `0x0C0E`
- trailing state blob: `0x42`

Current file (`NEWGAME.DBS`) matches exactly:

- size `0x0C2C0`
- `0x019E + 16 * 0x0C0E + 0x42 = 0x0C2C0`
- no trailing `0x1B0` block-record section present in this file instance

This confirms 16 map records are directly addressable via:

- `record_base(map_id) = 0x019E + map_id * 0x0C0E`
