# WMAZE Stitching Findings (Map Block Order / Origins)

## High-confidence functions

- `WMAZE:0x5F8B` = block permutation + origin carry.
- `WMAZE:0x6114` = per-block update tick; called from:
  - `WMAZE:0x6413`
  - `WMAZE:0x70DE`
- `WMAZE:0x7A37` = world `(x,y)` resolver to `(block,row,col)` using runtime origin tables.
- `WMAZE:0x7B5D` / `0x7BC2` = cross-block north/west edge fetch for wall access.

## Verified callsites (raw E8 scan, not linear-disasm only)

- `0x5F8B` called at `0x6DD8`
- `0x6114` called at `0x6413`, `0x70DE`
- `0x4E48` (selector used by permutation) called at:
  - `0x5FAC`
  - `0x6D2B`
  - `0x6D58`
  - `0x6D8E`

## What `0x5F8B` actually does

1. Uses `0x4E48` to pick a block index (`0x43CC`) repeatedly.
2. Copies chosen block record (`0x1B0` bytes each, base `0x43E8`) into stack scratch.
3. Carries origin pair arrays with the same chosen order:
   - active origins from `+0x43DC/+0x43D0`
4. Compacts remaining active records from backup block store (`+0x4598`) and restores active origins from baseline arrays:
   - baseline origins `+0x43DE/+0x43D2` -> active `+0x43DC/+0x43D0`
5. Rebuilds final active list from scratch copy and calls `0x4AC4` per block.

Net: stitched order/orientation is runtime-selected and not equivalent to static file order.

## Origin arrays used by resolver

`0x7A37` checks block bbox with:

- x-origin table at `base + 0x1E0` (12 entries)
- y-origin table at `base + 0x1EC` (12 entries)

where `base = [0x4FAA]` runtime map buffer.

Important: treating static file offset `0x7B22` directly as `base` yields zero origin arrays, so `0x7B22` is not a direct runtime-struct base for `0x7A37`.

## Packed wall field helpers (WROOT)

- overlay `0x27F6` -> `WROOT:0x28DA` (`set_field`)
- overlay `0x2841` -> `WROOT:0x2925` (`get_field`)

For width=2 fields:

- bitpos = `2 * idx`
- byte = `bitpos >> 3`
- shift = `bitpos & 7`

So current 2-bit unpacking model is correct.

## Practical implication for map10

To match the 4-block square with the 3x3 ring crossing seams, renderer must use runtime-equivalent block order/origins after permutation logic (`0x5F8B`) rather than assuming static block IDs/placement from the compact file nibbles alone.

## Additional disassembly progress (WBASE load/editor paths)

New `WBASE` scan (`scratch/disasm_wbase_map_load.py`) confirms:

- Indexed DB seek/read routine at `WBASE:0x500D..0x50AB`:
  - `call 0x3DA4` (open)
  - `call 0x423D` (seek)
  - `call 0x41EF` (transfer)
  - `call 0x4225` (close)
- Header path at `WBASE:0x7CC9..0x7D52`:
  - open/seek/transfer/close with `call 0x41F6` in this path.

Important caveat: both `0x41EF` and `0x41F6` appear in DB transfer paths across overlays, so we should avoid overcommitting to a strict read/write label from static ID alone without the exact thunk/runtime context.

### `0x43D0/0x43DC` usage split (likely editor-side)

`WBASE:0x69BA..0x6B02` directly manipulates:

- `0x43DC[]`: populated from per-entry pointer table (`0x515A`-based),
- `0x43D0[]`: slot index assigned by `WBASE:0x50AC` (small integer lane assignment),
- `0x43CE`: active count.

This suggests at least one overlay path where `0x43D*` arrays are editor/list metadata, not world-space map origins. That aligns with the observation that runtime seam resolution in `WMAZE` depends on `base+[0x1E0/0x1EC]` under `[0x4FAA]`, and those arrays are only read (not written) inside current `WMAZE` windows we decoded.

### Next decode target

To eliminate the remaining row/last-row stitch errors, we need the load/transform path that populates `[0x4FAA]+0x1E0/+0x1EC` for active map state. The most efficient next step is to trace where the `0x4FAA` buffer content is copied/constructed before `WMAZE:0x7A37` is used, rather than continuing to tune renderer-side seam heuristics.

## Major offset model correction (resolved)

The long-running row-shift/scramble symptoms were largely caused by decoding from the wrong map base.

Recovered from `WBASE` load routine:

- DB header size: `0x019E`
- per-map record size: `0x0C0E` (`0x3304 + 0x3306` in loader state)
- candidate map record base:
  - `base(map_id) = 0x019E + map_id * 0x0C0E`

This model matches observed edit diffs:

- map0 block-move diffs at absolute `0x037E..0x0383` and `0x038A..0x038F`
  line up exactly with `base(map0)+0x1E0` and `base(map0)+0x1EC`.
- map10 edited wall bytes around `0x7B15..0x7BFA` fall inside
  `base(map10)+{0x60/0x120}` packed wall planes.

For map10:

- `base(10) = 0x7A2A`
- `x origins = data[base+0x1E0 : +12] = [0,0,0,0,0,0,0,0,136,144,136,144]`
- `y origins = data[base+0x1EC : +12] = [0,0,0,0,0,0,0,0,119,119,127,127]`

This is a clean 2x2 block placement in world space (blocks 8..11), consistent with
the expected map10 stitched structure.

## New reconstruction script

- `scratch/render_map_walls_reconstructed.py`
  - decodes planes from `base+0x60` / `base+0x120`
  - uses direct origin tables at `base+0x1E0` / `base+0x1EC`
  - uses WMAZE mode semantics (`0/1/2/3`) for boundaries
  - uses OOB fallback rule from disassembly (`map_id 0x0A/0x0C -> open else blocked`)

This script is now the highest-confidence renderer path and should supersede
manual offset heuristics used in older map-specific scripts.

## WBASE load routine model (practical reconstruction)

From `WBASE:0x57D5..0x5C52`:

1. open selected DB path (`call 0x3DA4`)
2. seek to start (`call 0x423D`)
3. read `0x019E` header bytes into `0x33F8` (`call 0x41EF`)
4. loop `i=0..[0x3318)-1`:
   - read chunk A (`[0x3304]` bytes) to temp
   - read chunk B (`[0x3306]` bytes) to temp
   - for early entries, copy into pointer tables `[0x7D2/0x7D4]` and `[0x80A/0x80C]`
5. read `0x42` bytes of state
6. optional block-record load path (`bp+4 == 1`):
   - clear `0x43CE`
   - read `count` records of size `0x1B0` into `0x43E8 + idx*0x1B0`
   - assign companion lane ids in `0x43D0` via first-free allocator (`0x50AC`)
7. close file

Observed values indicate:

- `[0x3304] = 0x0542`
- `[0x3306] = 0x06CC`
- map-record stride = `0x0542 + 0x06CC = 0x0C0E`

This matches the direct file model used in `scratch/dump_all_map_records.py`,
which identifies 16 records in current `NEWGAME.DBS`:

- map IDs `0..13` populated
- map IDs `14..15` empty

## Runtime handoff in WMAZE (resolved)

Critical missing link is now recovered in `WMAZE:0x44C2..0x4570`:

1. Ensure runtime buffers:
   - if `[0x4FAA] == 0`, allocate `[0x3304]` bytes (`call 0x393E`) and store to `0x4FAA`
   - if `[0x4FA8] == 0`, allocate `[0x3306]` bytes and store to `0x4FA8`
2. If refresh flags are set (`0x4EEB/0x4EEA`), copy current-map planes into runtime:
   - copy `[0x3304]` bytes from pointer table entry `[idx*4 + 0x7D2/0x7D4]` -> `[0x4FAA]`
   - copy `[0x3306]` bytes from `[idx*4 + 0x80A/0x80C]` -> `[0x4FA8]`
   - where `idx = [0x363C]` (active map id)
3. Recompute world anchor:
   - `0x4FA4 = x_origin[current_block] + 0x4FA0`
   - `0x4FA2 = y_origin[current_block] + 0x4F9E`
   - using `[0x4FAA] + 0x1E0/+0x1EC`

This proves:

- runtime wall/origin reads in `WMAZE` are driven by loaded map plane blobs,
  not a separate hidden source;
- our record model (`base = 0x019E + map_id*0x0C0E`) is consistent with runtime behavior.

## Entry/call chain notes (WBASE)

- `WBASE:0x5E8D` is the high-level loader gateway:
  - `call 0x535B` (pre-check / UI gate)
  - `call 0x5626` (core load routine; argument forwarded from caller)
  - on success, enters post-load setup (`0x5C55`) and state transition.
- `0x5626` then executes the full DB ingest path (`open -> seek -> multi-read -> close`)
  described above.

## 0x42 tail-state mapping (partial but concrete)

After reading the trailing `0x42` bytes into stack local `[bp-0x48]`, loader code at
`WBASE:0x5A92..0x5AE3` copies words into globals. Confirmed mapping:

- `w00 -> 0x363C` (active map id)
- `w01..w13 -> 0x4FA4,0x4FA2,0x4FA0,0x4F9E,0x4F9C,0x4F9A,0x4F98,0x4F96,0x4F94,0x4F92,0x4F90,0x4F8E,0x4F8C`
- `w20/w21 -> 0x4F80/0x4F82` (32-bit pair)
- `w22/w23 -> 0x4F7C/0x4F7E` (32-bit pair)
- `w24/w25 -> 0x4F78/0x4F7A` (32-bit pair)
- `w32 -> [bp-8] -> block-record count used by subsequent `0x1B0` read loop (i.e., `0x43CE` source)`

This aligns with the save-side symmetry (where `0x43CE` is staged before tail write).
In current `NEWGAME.DBS`, `w32=0`, and file size has no trailing block-record section.

Utility:

- `scratch/decode_tail_state42.py` decodes and prints this mapping from current DB.

## Practical tooling status

- `scratch/render_map_walls_reconstructed.py`
  - now supports Left/Right map cycling across all records inferred from file size.
- `scratch/dump_all_map_records.py`
  - enumerates all map record bases, active block origins, and per-block nonzero wall counts.
- `scratch/export_all_maps_walls_json.py`
  - exports all maps (`0..N-1`) as resolved per-block boundaries (`h`/`v`) using
    origin-aware mode semantics, producing `scratch/all_maps_walls.json`.
