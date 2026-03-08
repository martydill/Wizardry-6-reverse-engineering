# MAZEDATA to 3D Wall Rendering Mapping (Current RE State)

## Confirmed

### 1) Map wall state comes from `NEWGAME*.DBS` map records

- Record stride and key offsets are already reconstructed in `scratch/render_map_walls_reconstructed.py`.
- Per map record:
  - `+0x60`: packed 2-bit wall field A
  - `+0x120`: packed 2-bit wall field B
  - `+0x1E0`, `+0x1EC`: 12 block origin tables (X/Y) for stitched world coordinates
- Relevant code:
  - `scratch/render_map_walls_reconstructed.py:30`
  - `scratch/render_map_walls_reconstructed.py:51`
  - `scratch/render_map_walls_reconstructed.py:165`
  - `scratch/render_map_walls_reconstructed.py:189`

`wall_mode_value(...)` in that file matches the `WMAZE` 4-mode accessor behavior:

- mode 0: local south edge from field A (`+0x60`)
- mode 1: local east edge from field B (`+0x120`)
- mode 2: north neighbor lookup (cross-block) then field A
- mode 3: west neighbor lookup (cross-block) then field B

For edge values:
- `0`: open
- `1`: passage-like special edge (current interpretation)
- `3`: door-like special edge (current interpretation)
- non-zero = blocked for geometry

### 2) `MAZEDATA.EGA` is not just a raw atlas; it has primitive tiles + display records

`bane.data.sprite_decoder.decode_mazedata_tiles` is the correct parser for primitive tile payloads:

- Header:
  - `N` primitive tiles (`153`)
  - `N2` display-list records (`366`)
- Primitive tile descriptors are 5 bytes each.
- A second header table of `N2 * 5` bytes exists after descriptors.
- Primitive pixel payload starts after descriptor table + display list.

Relevant code:
- `bane/data/sprite_decoder.py:456`
- `bane/data/sprite_decoder.py:493`
- `bane/data/sprite_decoder.py:497`
- `bane/data/sprite_decoder.py:511`

## Critical Correction: Display Table Is Fixed 5-byte Records

Initial RE assumed a 4-byte record + separator model. Current data points show a stronger model:

- The display table is exactly `N2` fixed records of 5 bytes each.
- Byte0 is an `owner_id` in range `0..152` (exactly 153 distinct values).
- Byte1 is usually a primitive tile reference (`1..153`), with control values `0` and occasional `255`.
- Byte2/Byte3 behave like direct pixel coordinates in many composites (not byte*8 in this model).
- Byte4 is an auxiliary field (likely priority/layer/depth/control).

Evidence from generated analysis:
- `owner_id_count = 153`
- `owner` record histogram: `{1:81, 2:12, 3:22, 4:2, 5:35, 12:1}`
- composites rendered by grouping on `owner_id` produce plausible wall-slice sprites

Tool and outputs:
- Script: `scratch/analyze_mazedata_display_records.py`
- JSON dump: `scratch/mazedata_display_analysis/display_records.json`
- Contact sheet: `scratch/mazedata_display_analysis/owner_contact_sheet.png`

### 2.1) EGA/CGA parity confirms display records are mode-independent

`MAZEDATA.EGA` and `MAZEDATA.CGA` have identical `(N, N2)` and identical
`N2*5` display-record bytes.

- `N=153`, `N2=366` in both files
- display table bytes (`1830`) are byte-for-byte equal
- `MAZEDATA.T16` matches the same table as well

This strongly indicates the owner/tile composition table is canonical data, while
pixel payload differs by graphics mode.

Repro:
- `scratch/research_maze_render_path.py`

### 2.2) Owner IDs have strong slot-family structure

Owner composites are highly structured by rendered bbox and repeated signatures:

- 153 owners total
- 36 exact duplicate-signature groups
- repeated bbox families (same `(x0,y0,w,h)` with multiple owners)
- 94 distinct bbox families (grouping by rendered extents)

This is consistent with perspective slot taxonomy (depth/orientation variants),
with multiple owners reused or aliased across wall states.

Artifacts:
- `scratch/infer_owner_slot_taxonomy.py`
- `scratch/owner_slot_taxonomy/owner_taxonomy.json`
- `scratch/render_owner_bbox_groups.py`
- `scratch/owner_bbox_groups/manifest.json`

Reference parser:
- `scratch/composite_stairway.py:45`

### 3) Owner composites are likely the 3D view primitives used by the renderer

Using `owner_id` buckets from the fixed 5-byte table:

- many owners are single-record (simple slices)
- some owners are multi-record composites (complex wall/door/stairs overlays)
- many owners are duplicated in pattern families (probable orientation/depth/style variants)

## What This Gives Us Right Now

You can already build a correct render input pipeline:

1. Decode wall edges per visible world cell using `wall_mode_value`.
2. For each visible wall segment (left/right/front at each depth), classify:
   - orientation (front/left/right)
   - depth
   - wall type (`1` solid, `3` door, etc.)
3. Resolve that triple into a MAZEDATA `owner_id`.
4. Draw each display record for that owner:
   - fetch primitive tile by `tile_ref - 1` when `tile_ref in [1,153]`
   - apply record placement/aux semantics (currently best-fit is `x=byte2`, `y=byte3`, plus aux controls)

Only step 3 is not fully decoded yet.

## Prototype Renderer Harness (Implemented)

A working prototype path now exists that wires:

1. real map wall edges from `NEWGAME.DBS` (`+0x60/+0x120`, origin-aware),
2. real MAZEDATA owner composites,
3. first-person slot visibility (`front/left/right` by depth).

Files:

- `scratch/build_owner_slot_candidates.py`
  - builds provisional `slot -> owner_ids` candidates, mirror hints, and
    `slot_candidates_by_wall_value` (value-aware picks)
  - outputs `scratch/owner_slot_candidates/slot_candidates.json`
- `scratch/render_map_3d_owner_prototype.py`
  - renders first-person frames from map walls + MAZEDATA owners
  - supports manual overrides:
    - `slot=owner`
    - `wall:slot=owner`
  - example outputs:
    - `scratch/proto_3d_map10_n.png`
    - `scratch/proto_3d_map10_e.png`
    - `scratch/proto_3d_map10_s.png`
    - `scratch/proto_3d_map10_w.png`

Important:

- This is a calibration harness, not final parity.
- Slot-to-owner mapping is still heuristic until the runtime dispatch table is
  fully decoded from game code.

### Calibration tooling (new)

To converge the mapping against real in-game visuals:

- `scratch/generate_slot_candidate_scene_sheet.py`
  - renders the same scene repeatedly while changing one slot candidate
  - outputs comparison sheets for manual pick/validation
- `scratch/init_owner_mapping_overrides.py`
  - creates editable `mapping_overrides.json` from current top picks
- `scratch/render_map_3d_owner_prototype.py --mapping-overrides-file ...`
  - loads persisted per-wall-value slot picks

Example output:

- `scratch/slot_candidate_sheets/sheet_map10_N_w2_center_d2.png`
- `scratch/slot_candidate_sheets/sheet_map10_N_w2_center_d3.png`
- `scratch/slot_candidate_sheets/sheet_map10_N_w2_left_d2.png`
- `scratch/slot_candidate_sheets/sheet_map10_N_w2_right_d2.png`
- `scratch/owner_slot_candidates/mapping_overrides.json`

This enables slot-by-slot calibration before final runtime-table recovery.

### Wall value distribution (from real map data)

Across all current map records in `NEWGAME.DBS`, nonzero edge values are:

- value `1`: `389`
- value `2`: `7838`
- value `3`: `155`

So value `2` is dominant and should be treated as the primary solid-wall path in
the provisional renderer, with value `3` as a rarer special/door-like path.

Artifact:
- `scratch/analyze_wall_value_distribution.py`
- `scratch/wall_value_distribution/distribution.json`

## Missing Piece (Still RE Needed)

The unresolved part is the lookup table in game code (likely `WBASE.OVR` and/or `WMAZE.OVR`) that maps:

- `(view slot/depth/orientation, wall value/type, maybe map style)`  
to
- `MAZEDATA owner_id`

The disassembly confirms wall fetch routines and cross-block resolvers, but we still need the table that chooses which owner to draw for each view slot.

## New Call-Graph Finding: `0x53AA` Is Not Widely Used For Draw

Raw near-call scan shows only two `WMAZE` callsites to `0x53AA`:

- `0x5898`
- `0x76E2`

Those windows are movement/interaction checks (door/passability flow), not the
full first-person wall painter. So the final owner-selection table is likely in
the render path using other intermediates (possibly shared draw/resource logic
invoked from overlays beyond `WMAZE`).

Repro:
- `scratch/research_maze_render_path.py`

## Dispatcher-Level Finding Around `0x6E4C` (new)

The `0x6E2*` region is now decoded as a real switch-based dispatcher (not linear
code):

- table at `0x6E13` with 9 handlers:
  - `0x6DF9, 0x6E07, 0x6E34, 0x6E6A, 0x6EAF, 0x6EBC, 0x6EC1, 0x6EF0, 0x6EF5`
- switch stub:
  - `0x6E25: cmp ax, 9`
  - `0x6E2D: jmp cs:[bx+0x6EF7]`

Two central helpers in this cluster are now clear:

- `0x6E4C`: draws a 2x2 sprite block via repeated `0x22FF` calls.
- `0x6EBF`: draws a 2x4 strip via repeated `0x22FF` calls.

Both receive small hardcoded sprite IDs in callers (examples: `1..0x19`,
`0x0A..0x11`, `0x20`) such as the blocks at `0x73B8..0x74AF`. This strongly
indicates these are HUD/overlay composition helpers, not the final wall-owner
selection table for MAZEDATA perspective walls.

Repro:
- `scratch/disasm_wmaze_render_dispatch.py`

## Refined `0x53AA` Interpretation (new)

The second `0x53AA` callsite (`0x76E2`) is in passability/step-check flow:

- reads directional wall state via `0x53AA`
- compares against threshold (`cmp ax, 2`)
- branches into movement resolution (`call 0x751D`)

So this path is gameplay collision/state gating, not the wall-slice draw
dispatch that maps `(slot, depth, wall type)` to MAZEDATA owner IDs.

Repro:
- `scratch/disasm_wmaze_render_dispatch.py`

## New Cross-Overlay Lead: `WBASE` Uses Map Record `+0x43E8` Directly In Draw Calls

Fresh `WBASE` disassembly windows show repeated draw sequences where:

- map record pointer is built as `0x1B0 * map_index + 0x43E8`
- that pointer is passed into shared draw helpers (`0x2439`, `0x2405`, `0x22FF`)

Examples:

- `WBASE:0x5FF2..0x6002` -> `call 0x2439` with `0x1B0*map + 0x43E8`
- `WBASE:0x6B30..0x6B3D` -> `call 0x2439` with `0x1B0*map + 0x43E8`
- `WBASE:0x6D93..0x6DA0` -> `call 0x2405` with `0x1B0*map + 0x43E8`

This is the strongest current static signal that final visible wall/theme sprite
selection is likely anchored in map-record data consumed in shared `WBASE` draw
paths, while `WMAZE` contributes wall-state query logic and movement checks.

Repro:
- `scratch/disasm_wbase_map_theme_draws.py`

### Corroboration in `WMAZE`: `0x4AC4` mirrors `WBASE:0x5FAD` logic

`WMAZE:0x4AC4..0x4DA5` is a near-identical draw routine to
`WBASE:0x5FAD..0x628E`:

- same call pattern to `0x0227`, `0x2439`, `0x22FF`
- same offset usage pattern:
  - global indexed array `0x43D0[map_idx]` (not entry-local)
  - `+0x4589`, `+0x4587`
  - global indexed tables `0x0526[]`, `0x0532[]` (not entry-local)
  - `+0x450A`, `+0x450C`, `+0x450D`
  - `+0x44F8`
  - `+0x4428`, `+0x442D`
  - `+0x4400/02/04/06`
- same `0x1B0*idx + 0x43E8` stream pointer feed into `0x2439`.

Artifacts:

- `scratch/wmaze_4ac4_5200_disasm.txt`
- `scratch/analyze_wmaze_4ac4_calls.py`
- `scratch/wmaze_4ac4_calls.json`

Interpretation:

- this strongly confirms shared overlay draw infrastructure around map-entry
  records and stream pointers.
- this routine appears to be panel/object/overlay composition logic, not the
  final first-person wall-slot owner table by itself.

Related new finding:

- `WBASE:0x50AC` is a global slot allocator over `0x43D0[]`:
  - scans prior entries for used IDs
  - returns first free ID in `0..5` (else `0`)
- artifact: `scratch/analyze_wbase_50ac.py`, `scratch/wbase_50ac_disasm.txt`

## Draw-Core Reverse Engineering (new): `WROOT:0x22B7`

The shared draw primitive used by `0x22FF/0x2439/0x2405` is now decoded:

- `WROOT:0x22B7`:
  - resolves a draw object from the object list at `cs:[0x1BD2]`
  - writes encoded draw word into object cell buffer (`[obj+0x10 + 2*cell]`)
  - computes screen/source index from object position (`obj+2/3`) and cursor (`obj+6/7`)
  - checks ownership/mask byte in a `0x3E8` grid (`cs:[0x1B60]`)
  - issues final low-level blit via far call (`lcall cs:[0x1B8A]`)
  - advances per-object cursor (`obj+6/7`)
- `WROOT:0x24E9`:
  - iterates zero-terminated byte stream and calls `0x22B7` per byte.
- `WROOT:0x251D`:
  - iterates stream and calls `0x23E3` variant per byte.

Implication:
- byte streams passed into `0x2405/0x2439` are direct sprite/code sequences.
- the unresolved mapping is therefore upstream stream construction logic
  (`slot/depth/wall state -> byte stream`), not inside `0x22B7` itself.

Repro:
- `scratch/disasm_wroot_draw_core.py`

## Correction: `WMAZE:0xD2CF..0xDAE4` Is Interaction Flow (not wall painter)

The high-address cluster around `0xD2CF` includes:

- window/widget composition calls
- input/event loops
- conditional state updates and mini-loop UI behavior

and does not behave like a first-person wall pass over visible slots.

So this region should be treated as interaction/minigame logic, not the main
3D wall renderer mapping path.

## Callsite Context Extraction (new)

A callsite context dump for `WMAZE` draw helpers is now generated:

- `scratch/extract_wmaze_draw_callsite_context.py`
- output: `scratch/wmaze_draw_callsite_context.json`

Current pattern in reachable contexts:

- many `0x2439`/`0x2405` calls consume either:
  - `0x1B0*idx + 0x43E8` streams, or
  - local temporary streams loaded via resource helper calls (e.g. `0x0677`).
- no direct `0x53AA` adjacency in these draw wrappers.

This supports the model that wall-direction access (`0x53AA`) and final stream
composition are decoupled through intermediate state tables/buffers.

## New Data Finding: Map Records Carry Leading Draw Streams

By scanning real `NEWGAME.DBS` map records (`stride 0x0C0E`), the first region of
each map contains compact zero-terminated byte streams with map-specific
patterns (common lengths: `12/24/36/60/84`).

Example map stream heads:

- map 2: `[1, 23, 24, 5, 6, 7, ...]` (len 36)
- map 8: `[74, 75, 75, 77, 78, 78, ...]` (len 36)
- map 10: `[135, 135, 135, 136, 101, 101, ...]` (len 12)

This is consistent with `0x2405/0x2439` expecting byte-stream inputs and with
`WBASE` passing `0x1B0*idx + 0x43E8` pointers into draw wrappers.

Important caveat:

- Some stream values exceed MAZEDATA owner range (`>152`, e.g. up to ~180), so
  these bytes are likely **intermediate draw codes**, not direct owner IDs.
- A remaining mapping layer is still required:
  - `map-stream code -> MAZEDATA owner/tile primitive(s)`.

Artifacts:

- `scratch/extract_map_owner_streams.py`
- `scratch/map_owner_streams/streams.json`
- `scratch/map_owner_streams/map_XX_stream0.png`

## Renderer Upgrade (new): Map-Stream Driven Owner Picks

`scratch/render_map_3d_owner_prototype.py` now supports using real map-stream
bytes from `NEWGAME.DBS` for slot owner picks:

- flag: `--use-map-streams`
- mapping option: `--stream-set-map "2:0,1:1,3:2"`

Current implemented model:

1. Extract primary stream from map record `+0x000..+0x1AF`:
   - skip leading `0x00` sentinel run (if present),
   - read until first `0x00`.
2. Split stream into `12`-byte sets.
3. Treat each set as depth-major triplets of slots:
   - `[center_d1,left_d1,right_d1, center_d2,left_d2,right_d2, ... center_d4,left_d4,right_d4]`
4. Decode stream code to owner:
   - `0..152` -> direct owner id
   - `153..180` -> `owner = code - 28`
5. Choose set per wall value using `--stream-set-map`.

This makes the prototype consume real per-map render codes rather than purely
generic geometry heuristics.

Example runs:

- `python scratch/render_map_3d_owner_prototype.py --map-id 2 --facing N --use-map-streams --out scratch/proto_3d_map2_stream_n.png`
- `python scratch/render_map_3d_owner_prototype.py --map-id 12 --facing N --use-map-streams --out scratch/proto_3d_map12_stream_n.png`

Notes:

- This is still an intermediate RE model.
- Slot order and wall-value->set assignment are now data-driven and overrideable,
  but still need final confirmation against full original runtime behavior.

### New controls added

- `--auto-stream-set-map`
  - infers wall-value set assignment from stream-set structure metrics.
- `--stream-code-map-file <json>`
  - explicit `stream_code -> owner_id` override map.

Bootstrap helper:

- `scratch/init_stream_code_map.py`
  - writes `scratch/owner_slot_candidates/stream_code_map_default.json`
  - default mapping currently:
    - `0..152 -> same`
    - `153..180 -> code-28` (provisional)

### Batch output baseline

Generated full map/facing stream-driven baseline renders:

- directory: `scratch/proto_stream_batch/`
- files: `map00_N.png` .. `map15_W.png`

This gives a concrete artifact set for iterative parity checks while RE
continues on exact translation semantics.

## New Stream-Offset Finding (`+0x00/+0x24/+0x48`)

In the first `0x1B0` bytes of each map record, stream entry points at offsets
`+0x24` and `+0x48` are real zero-terminated code runs and, when present,
are suffixes of the primary stream at `+0x00`.

Confirmed examples:

- map `11`:
  - `len(stream0)=84`
  - `len(stream24)=48`, starts at `stream0[36]`
  - `len(stream48)=12`, starts at `stream0[72]`
- map `12`:
  - `len(stream0)=60`
  - `len(stream24)=24`, starts at `stream0[36]`
  - `stream48` empty

Artifacts:

- `scratch/analyze_map_stream_offsets.py`
- `scratch/map_owner_streams/offset_stream_analysis.json`

This is consistent with a data layout where different wall classes can begin
reading from different stream entry points rather than a single global set list.

## Renderer Upgrade: Per-Wall Stream Offsets

`scratch/render_map_3d_owner_prototype.py` now supports offset-driven stream
selection:

- `--use-stream-offsets`
- `--stream-offset-map "2:0x0,1:0x24,3:0x48"`

Behavior:

1. For each wall value (`1/2/3`), extract stream from configured offset.
2. Split per-wall stream into `12`-code sets.
3. Select set index via existing `--stream-set-map`.
4. Decode code to owner (`0..152` direct, `153..180 -> code-28`, still provisional).
5. If a wall-value offset stream is empty, fallback to the primary stream sets.
6. When offset mode is enabled and default set-map is unchanged, renderer now
   defaults to set `0` for wall values `1/2/3` (each class already has its own
   stream entry).

New output baselines:

- `scratch/proto_stream_offset_batch/map00_N.png` .. `map15_W.png`
- `scratch/proto_stream_offset_batch_set0/map00_N.png` .. `map15_W.png`
- `scratch/proto_3d_map11_stream_offsets_n.png`
- `scratch/proto_3d_map12_stream_offsets_n.png`
- `scratch/proto_3d_map11_stream_offsets_n_set0.png`
- `scratch/proto_3d_map12_stream_offsets_n_set0.png`

## Experimental High-Code Inference (analysis artifact)

Added:

- `scratch/infer_stream_code_map.py`

This infers `stream_code -> owner` from slot co-occurrence over all map streams
and offsets and writes:

- `scratch/owner_slot_candidates/stream_code_map_inferred.json`
- `scratch/owner_slot_candidates/stream_code_map_inferred_debug.json`

Current result over-collapses high codes to a narrow owner set, so this is
kept as an analysis artifact only and is not considered parity-accurate yet.

## `WMAZE:0x4AC4` Structured Call Trace (new)

Added extraction:

- `scratch/analyze_wmaze_4ac4_calls.py`
- output: `scratch/wmaze_4ac4_calls.json`

This captures each `0x0227/0x22FF/0x2439/0x2405` call in `0x4AC4..0x4DA5`
with the immediate setup context and field references.

Recovered offsets consumed by this draw routine:

- global tables/arrays:
  - `0x43D0[]`
  - `0x0526[]`, `0x0532[]`
- per-entry (`0x1B0*idx + ...`) offsets:
  - `+0x4589`, `+0x4587`
  - `+0x450A`, `+0x450C`, `+0x450D`
  - `+0x44F8`
  - `+0x4428`, `+0x442D`
  - `+0x4400/0x4402/0x4404/0x4406`

This further supports that `WMAZE:0x4AC4` is shared overlay/panel composition
logic over `0x1B0` map-entry records, not by itself the final first-person wall
slot->owner dispatch table.

Important correction from deeper decode:

- `0x43D0` in this routine is accessed as a global indexed array (`[2*idx + 0x43D0]`),
  not as `entry + 0x43D0`.
- `0x0526` and `0x0532` are also global indexed tables.
- `WBASE:0x50AC` assigns values for `0x43D0[]` by choosing first free ID in `0..5`
  across existing entries.

Critical correction:

- `WMAZE:0x4DA5` loops `call 0x4AC4` over `[0x43CE]` entries, which is consistent
  with per-entity/panel composition flow, not direct first-person wall-slice
  selection.
- treat `0x4AC4` as shared UI/entity draw infrastructure; do not treat it as the
  primary wall renderer.

Artifacts:

- `scratch/analyze_wbase_50ac.py`
- `scratch/wbase_50ac_disasm.txt`

## Renderer Decision Trace Export (new)

`scratch/render_map_3d_owner_prototype.py` now supports:

- `--debug-json <path>`

The trace includes:

- visible slots and wall values
- chosen owner per slot
- draw order
- stream selection details (set map, offset map, extracted streams)
- exact selected stream code per wall/slot before owner decode

Generated:

- `scratch/proto_3d_map11_stream_offsets_n_set0.json`
- `scratch/proto_3d_map12_stream_offsets_n_set0.json`

## New Loader Finding: MAZEDATA Is Resolved In `WINIT.OVR`

`WINIT` string table includes:

- `MAZEDATA.EGA`
- `MAZEDATA.CGA`
- `MAZEDATA.T16`

alongside `WFONT*` and `TITLEPAG*`, confirming initialization-level asset wiring.
This reinforces that the runtime owner lookup may be in shared resource/display
codepaths established at init time, not only map logic in `WMAZE`.

Repro:
- `scratch/research_maze_render_path.py`

## Most Efficient Next RE Step

Instrument the first-person draw path to capture, per frame:

- wall query inputs and returned 2-bit wall values
- the final resource/group IDs sent to draw calls

Given the new call-graph evidence, focus on:

- shared draw helpers (`0x0227`, `0x22FF`, `0x2405`, `0x2439`, `0x0B32`)
- their upstream callers in the maze-view overlays
- init/resource setup in `WINIT` for MAZEDATA-backed assets

Then map captured draw IDs back to parsed MAZEDATA owner groups.

Practical implementation loop:

1. Keep `scratch/render_map_3d_owner_prototype.py` as the integration base.
2. Replace heuristic slot picks with decoded runtime owner dispatch.
3. Validate against captured in-game frames until output matches per slot/depth.

## New Wall-Render Candidates (post-`0x4AC4` correction)

Raw callscan highlights a different cluster for first-person wall classification:

- calls to cross-block wall helpers:
  - `0x7B5D` at `0x5418`, `0x7F0E`, `0x8196`, `0x8324`
  - `0x7BC2` at `0x542F`, `0x7F28`, `0x8151`, `0x833D`
- HUD strip helpers remain at:
  - `0x6E4C` calls `0x73D4`, `0x73F6`, `0x742E`, `0x7452`, `0x7474`, `0x74AC`
  - `0x6EBF` calls `0x740C`, `0x748A`

Artifacts:

- `scratch/wmaze_call53aa_function_scan.txt`
- `scratch/analyze_wmaze_wall_render_candidates.py`
- `scratch/wmaze_wall_render_candidates.json`
- disasm windows:
  - `scratch/wmaze_7e80_8050_disasm.txt`
  - `scratch/wmaze_80f0_82a0_disasm.txt`
  - `scratch/wmaze_82d0_83f0_disasm.txt`

Interpretation:

- `0x7F**/0x81**/0x83**` regions look like wall/face classifiers:
  - read directional wall value (`+0x60/+0x120` or `0x7B5D/0x7BC2`)
  - combine with extra packed channels (`+0x1F8`, `+0x378`)
  - map into larger class buckets (constants around `4..14`) with side effects.

## Central Wall Draw Routine Located (`~0x90C0`) (new)

A larger `WMAZE` routine (`0x90C0..`) now appears to orchestrate first-person
wall lane draws:

- computes per-lane class values into globals:
  - `0x5220`, `0x5222`, `0x5224`, `0x5226`, `0x5228`
- class producers:
  - `0x7CA8`
  - `0x8091`
  - `0x824E`
- dispatches to draw helpers with class + depth index:
  - `0x84EC`
  - `0x8A34`
  - `0x8C23`
  - plus per-lane state updaters `0x8D12/0x8D75/0x8DA6/0x8DD7`

Artifacts:

- `scratch/wmaze_90c0_94f0_disasm.txt`
- `scratch/wmaze_84ec_8a34_disasm.txt`
- `scratch/wmaze_8a34_8c23_disasm.txt`
- `scratch/wmaze_8c23_8d12_disasm.txt`
- `scratch/wmaze_8d12_8e30_disasm.txt`
- `scratch/wmaze_7ca8_8091_disasm.txt`

This is currently the strongest candidate for the true first-person wall
renderer path.

## Dispatch Constants: Record-Index Hypothesis Confirmed (new)

From the `0x90C0` call contexts, extracted immediate constant bundles passed to
`0x84EC/0x8A34/0x8C23`.

Artifacts:

- `scratch/extract_wmaze_wall_draw_dispatch.py`
- `scratch/wmaze_wall_draw_dispatch.json`
- `scratch/analyze_wmaze_draw_dispatch_constants.py`
- `scratch/wmaze_draw_dispatch_constants_analysis.json`

Key result:

- constants range `0..335`
- `MAZEDATA` display records count is `N2=366`
- all constants are valid display-record indices

And stronger:

- every extracted constant is exactly at an owner-boundary start in the
  display-record table (not in the middle of an owner run).

Artifact:

- `scratch/map_dispatch_constants_to_mazedata_records.py`
- `scratch/wmaze_dispatch_constants_to_records.json`

Interpretation:

- runtime draw dispatch appears to reference MAZEDATA by **display-record start
  index** (owner-run anchor), not by raw owner id directly.
- this explains why draw constants exceed owner id max (`152`) while staying
  below display-record count (`366`).

## Stream-Code Interpretation Test (new, strong)

Tested all unique stream codes (from primary and offset streams across maps) as
MAZEDATA display-record indices.

Artifact:

- `scratch/analyze_stream_codes_as_record_indices.py`
- output: `scratch/map_owner_streams/stream_codes_record_index_fit.json`

Result:

- unique stream codes observed: `103`
- all `103/103` are valid record indices (`<366`)
- all `103/103` are **owner-boundary starts** in the display-record table
  (`boundary_ratio = 1.0`)

This is strong structural evidence that stream codes are intended as
display-record start indices (owner-run anchors), not arbitrary owner ids.

Companion mapping artifact:

- `scratch/init_stream_code_map_record_owner.py`
- output: `scratch/owner_slot_candidates/stream_code_map_record_owner.json`
  (`stream_code -> owner_id` via record-index lookup)

## Renderer Decode Mode Extension (updated)

Prototype now includes two additional stream decode modes:

- `record_owner`
  - interpret stream code as MAZEDATA display-record index, map to that record's
    owner id
- `record_owner_high`
  - low codes use `minus28` path behavior
  - high codes (`>152`) use display-record index -> owner id
- `record_run`
  - interpret stream code as display-record run start index and draw that exact
    run (no owner-bucket collapse)
- `record_run_high`
  - low codes use `minus28` owner path
  - high codes (`>152`) use display-record run start index draw

Files:

- `scratch/render_map_3d_owner_prototype.py`
- `scratch/run_mazedata_3d_viewer.py`

Comparison outputs:

- `scratch/proto_decode_compare/map11_131_140_W_record_owner_high.png`
- `scratch/proto_decode_compare/map11_131_140_W_record_owner.png`
- `scratch/proto_decode_compare/map12_122_149_S_record_owner_high.png`
- `scratch/proto_decode_compare/map12_122_149_S_record_owner.png`
- `scratch/proto_decode_compare/map11_131_140_W_record_run.png`
- `scratch/proto_decode_compare/map12_122_149_S_record_run.png`
- `scratch/proto_decode_compare/map11_131_140_W_record_run_dispatchset.png`
- `scratch/proto_decode_compare/map12_122_149_S_record_run_dispatchset.png`

Observed:

- these record-index modes produce substantial changes vs `minus28`
  (`MAD ~18..30`, `MSE ~1980..3270` on current stress scenes),
  so this remains an active hypothesis to verify against game captures.
- `record_run` now follows the stronger structural model directly:
  stream code -> display-record run anchor -> draw exact run image.
- current `record_run` deltas vs `minus28` on stress scenes:
  - map11 `(131,140,W)`: `MAD 28.783`, `MSE 4057.946`
  - map12 `(122,149,S)`: `MAD 23.079`, `MSE 3244.383`
- with dispatch-inferred set-map enabled:
  - map11 `record_run -> record_run_dispatchset`: `MAD 8.914`, `MSE 1200.633`
  - map12 `record_run -> record_run_dispatchset`: `MAD 19.366`, `MSE 2861.700`

## Extra Packed Channels Confirmed In Map Records

From `NEWGAME.DBS` map record layout (`stride=0x0C0E`), these packed channels are
active and likely feed wall-style classification:

- `+0x1F8`: 4-bit channel (768 entries)
- `+0x378`: 2-bit channel (768 entries)

Size consistency:

- `0x378 - 0x1F8 = 0x180 = 384 bytes = 768 * 4 bits`

Artifact:

- `scratch/analyze_map_extra_channels.py`
- output: `scratch/map_extra_channels_analysis.json`

Observed (examples):

- map 11 has nonzero values across both channels (`3/4/5/7/10/12/14` in `+0x1F8`,
  and all `0..3` in `+0x378`)
- map 12 similarly has nonzero values in both channels
- map 10 is mostly zero in these channels

This aligns with maps 11/12 being the same maps where high stream-code behavior
was most visible.

## Renderer Debug Upgrade: Per-Slot Extra Channels

`scratch/render_map_3d_owner_prototype.py --debug-json` now includes
`visible_details` entries with:

- base world cell per depth
- resolved `(block,row,col)`
- `channel4_1f8`
- `channel2_378`

This makes slot-by-slot comparison against `WMAZE` classifier logic practical
without re-running disassembly for each camera state.

## Dispatch-Consistency Set-Map Inference (new)

Added an inference pass that selects `wall_value -> stream-set index` per map by
maximizing overlap with the discovered `WMAZE` dispatch-constant universe.

Files:

- `scratch/infer_stream_set_map_by_dispatch.py`
- output: `scratch/map_owner_streams/inferred_set_map_by_dispatch.json`

Validation:

- `scratch/validate_stream_runs_vs_dispatch_constants.py`
- output: `scratch/map_owner_streams/stream_run_vs_dispatch_validation.json`

Result (all maps/cells/facings, current slot model):

- fixed `set0` per wall class: outside-dispatch ratio `0.775`
- inferred per-map set-map: outside-dispatch ratio `0.479`

Integration:

- `scratch/render_map_3d_owner_prototype.py`
  - new flags:
    - `--auto-dispatch-set-map`
    - `--dispatch-set-map-file`
- `scratch/run_mazedata_3d_viewer.py`
  - same flags
- `scratch/walk_3d.py`
  - same flags

This does not complete parity yet, but it materially reduces mismatch with the
runtime dispatch constant set while retaining stream/run-index rendering.

## Channel4-Conditioned Set Policy (experimental)

Added an experimental inference that conditions set choice on map channel
`+0x1F8` (4-bit) at the depth-base cell.

Files:

- `scratch/infer_stream_set_map_by_channel4_dispatch.py`
- output: `scratch/map_owner_streams/inferred_set_map_by_channel4_dispatch.json`
- `scratch/validate_stream_runs_channel4_policy.py`
- output: `scratch/map_owner_streams/stream_run_channel4_policy_validation.json`

Prototype integration (opt-in only):

- `scratch/render_map_3d_owner_prototype.py`
  - `--auto-dispatch-set-by-channel4`
  - `--dispatch-channel4-set-file`

Current result:

- outside-dispatch ratio with channel4 policy: `0.478992`
- outside-dispatch ratio with global dispatch-set map: `0.478965`

So this channel4-only conditioning is currently neutral/slightly worse and is
kept as an analysis hook, not a recommended default.

## Slot-Conditioned Set Policy (new, stronger)

Added a per-map, per-wall-value, per-slot set-policy inferred by dispatch
constant consistency.

Files:

- `scratch/infer_stream_slot_set_map_by_dispatch.py`
- output: `scratch/map_owner_streams/inferred_slot_set_map_by_dispatch.json`
- `scratch/validate_stream_runs_slot_set_policy.py`
- output: `scratch/map_owner_streams/stream_run_slot_set_policy_validation.json`
- comparison summary:
  - `scratch/map_owner_streams/dispatch_policy_comparison.json`

Validation result (all maps/cells/facings):

- global per-wall set-map policy: `outside_ratio = 0.478965`
- channel4 policy: `outside_ratio = 0.478992`
- slot-conditioned policy: `outside_ratio = 0.435672`

Integration:

- `scratch/render_map_3d_owner_prototype.py`
  - new flags:
    - `--auto-dispatch-slot-set-map`
    - `--dispatch-slot-set-map-file`
- `scratch/run_mazedata_3d_viewer.py`
  - same flags

Status:

- This improves structural consistency against dispatch constants globally, but
  can still worsen specific stress viewpoints; keep as optional mode.

## Slot Source+Set Policy (new best structural fit)

Added a per-map, per-wall-value, per-slot policy that chooses both:

- stream source wall class (`offset stream 2/1/3`)
- set index within that source stream

Files:

- `scratch/infer_stream_slot_source_set_policy_by_dispatch.py`
- `scratch/validate_stream_runs_slot_source_set_policy.py`
- outputs:
  - `scratch/map_owner_streams/inferred_slot_source_set_policy_by_dispatch.json`
  - `scratch/map_owner_streams/stream_run_slot_source_set_policy_validation.json`

Validation (all maps/cells/facings):

- slot-set policy: `outside_ratio = 0.435672`
- slot-source+set policy: `outside_ratio = 0.430138` (best so far)

Integration (opt-in):

- `scratch/render_map_3d_owner_prototype.py`
  - `--auto-dispatch-slot-source-set-map`
  - `--dispatch-slot-source-set-map-file`
- `scratch/run_mazedata_3d_viewer.py`
  - same flags

Stress-scene outputs:

- `scratch/proto_decode_compare/map11_131_140_W_record_run_slotsourceset.json`
- `scratch/proto_decode_compare/map12_122_149_S_record_run_slotsourceset.json`

## Dispatch Feature Search (map-scoped) (new)

Added a policy-feature search over map-scoped keys:

- `scratch/search_dispatch_policy_features.py`
- output: `scratch/map_owner_streams/dispatch_policy_feature_search.json`

Result:

- `map+wv`: `outside_ratio 0.4790`
- `map+wv+slot`: `outside_ratio 0.4357` (best)
- adding channel4/channel2 and local triplet keys did not improve over
  `map+wv+slot` in current corpus.

Interpretation:

- current best practical policy remains slot-conditioned set selection.
- richer keys are not yet adding predictive power under current model.

## WMAZE Switch Table Extraction (raw) (new)

Added raw switch-table dumps for key classifier/draw helpers:

- `scratch/extract_wmaze_switch_tables.py`
- output: `scratch/wmaze_switch_tables.json`

Notes:

- entries are raw 16-bit jump targets from in-function indirect dispatch sites.
- some targets resolve into `WMAZE` overlay space, others do not; these require
  cross-module runtime context to fully decode.

## High-Code Viewpoint Discovery (new)

Added scanner:

- `scratch/find_high_stream_code_viewpoints.py`

Purpose:

- find map/camera states where visible slots actually consume high stream codes
  (`>152`), so decode hypotheses can be tested on relevant frames.

Current output:

- `scratch/map_owner_streams/high_code_viewpoints.json`

Key result:

- high-code usage is concentrated in maps `11` and `12` (consistent with prior
  stream analysis), and the scanner now provides ranked concrete viewpoints.

Top stress viewpoints currently used:

- map `11`: `(wx,wy,facing) = (131,140,W)`
- map `12`: `(wx,wy,facing) = (122,149,S)`

## Renderer Decode Switch (new)

`scratch/render_map_3d_owner_prototype.py` now supports:

- `--stream-high-mode minus28|highbit|identity`

This switches how stream codes `153..180` map before owner lookup:

- `minus28`: `owner = code - 28` (current default/provisional)
- `highbit`: `owner = code & 0x7F` (test hypothesis)
- `identity`: `owner = code` (debug only; typically out-of-range for MAZEDATA owners)

Comparison renders generated for the stress viewpoints:

- `scratch/proto_decode_compare/map11_131_140_W_minus28.png`
- `scratch/proto_decode_compare/map11_131_140_W_highbit.png`
- `scratch/proto_decode_compare/map12_122_149_S_minus28.png`
- `scratch/proto_decode_compare/map12_122_149_S_highbit.png`

Matching traces:

- `scratch/proto_decode_compare/map11_131_140_W_minus28.json`
- `scratch/proto_decode_compare/map11_131_140_W_highbit.json`
- `scratch/proto_decode_compare/map12_122_149_S_minus28.json`
- `scratch/proto_decode_compare/map12_122_149_S_highbit.json`

Batch comparison tooling:

- `scratch/render_high_code_decode_comparison.py`
- output sheet: `scratch/proto_decode_compare/decode_mode_sheet.png`
- per-scene diff metrics: `scratch/proto_decode_compare/decode_mode_diff_metrics.json`

Observed from owner IDs in traces:

- `minus28` keeps high-band mappings in upper owner range (`126..147`), which
  is currently more consistent with the existing map-theme owner families.
- `highbit` maps to low owner IDs (`26..47`) for the same high-band slots and
  appears less plausible for these maps.

Observed from rendered-frame deltas (minus28 vs highbit):

- map 12 scenes often show large deltas (`MAD ~22`, `MSE ~2500`), so high-band
  decode choice is visually significant there.
- map 11 stress scenes are still clearly different, but less extreme
  (`MAD ~6.2`, `MSE ~676`).

## Interactive Viewer (new)

Added a real-time first-person viewer using the same data path as the prototype:

- `scratch/run_mazedata_3d_viewer.py`

Characteristics:

- uses real wall edges from `NEWGAME.DBS` (`+0x60/+0x120` decode path)
- uses MAZEDATA owner composites
- uses stream-offset picks (`2->0x00`, `1->0x24`, `3->0x48`) with set `0` per wall class
- supports high-band decode switch:
  - `--stream-high-mode minus28|highbit|identity`

Controls:

- `W/S` or Up/Down: forward/backward
- `A/D` or Left/Right: turn
- `Esc`: quit

Example:

- `python scratch/run_mazedata_3d_viewer.py --map-id 11 --stream-high-mode minus28`

## Decode Formula Search Artifact (new)

Added exploratory model ranking:

- `scratch/search_high_code_decode_models.py`
- output: `scratch/map_owner_streams/high_decode_model_search.json`

Current status:

- This is a heuristic-only ranking (structure priors, not pixel parity against
  original runtime).
- Top-ranked formulas from this search are currently not trusted as parity
  evidence.
- Keep this as analysis artifact only; direct frame behavior and RE of runtime
  helpers still take precedence.

## Critical RE Correction (new)

`WMAZE.OVR` disassembly mapping for code analysis was corrected:

- previous assumption in several scripts: code starts at `0x00F2`
- verified workable mapping for code decode: code starts at `0x000E`
- overlay base remains `0x4572` (from file header bytes `0x72 0x45`)

Impact:

- switch/jump tables at `0x7F2C`, `0x7F82`, `0x8129`, `0x8306`, `0x84C5`,
  `0x8A02`, `0x8CDA` now decode to coherent in-overlay handler targets.
- renderer classifier RE is now consistent with real indirect dispatches.
- earlier "garbage table entries" were an artifact of the wrong load offset.

Updated artifacts:

- `scratch/wmaze_switch_tables.json`
- `scratch/wmaze_switch_target_xrefs.json`
- `scratch/wmaze_wall_draw_dispatch.json`
- `scratch/wmaze_7ca8_semantics.json`
- `scratch/wmaze_7ca8_switch_effect_summary.json`

New concrete extraction from corrected `7CA8` path:

- primary mode switch (`0x7F2C`) resolves to handlers that set:
  - `word [bx+0x5050] = 1` (several modes)
  - `byte [bx+0x50AB] = 1` (several modes)
  - `byte [bx+0x5043] = 1` (specific mode)
- secondary mode switch (`0x7F82`) mostly toggles:
  - `byte [bx+0x5043] = 1`
- tail switch (`0x8129`) chooses class/flags and can set:
  - `word [bp-4]` class codes (`4..0xE`)
  - `word [bx+0x50B8] = 1`
  - `word [bx+0x5050] = 1`
  - `byte [bx+0x50AB] = 1`
  - `byte [bx+0x5043] = 1`

Classifier class-map extraction (corrected labels):

- old-label `0x8091` classifier corresponds to corrected function at `0x8175`
  with class-map table at `0x8306`
- old-label `0x824E` classifier corresponds to corrected function at `0x8332`
  with class-map table at `0x84C5`
- both tables map indices to class codes `{4,5,6,7,8,9,0xA,0xB,0xC,0xD}` via
  tiny handlers setting `DI`, with passthrough entries using current `DI`

Artifacts:

- `scratch/extract_wmaze_classifier_class_maps.py`
- `scratch/wmaze_classifier_class_maps.json`
- `scratch/extract_wmaze_draw_class_switches.py`
- `scratch/wmaze_draw_class_switches.json`
- `scratch/build_wmaze_class_to_draw_map.py`
- `scratch/wmaze_class_to_draw_map.json`

Joined class->draw chain is now extracted:

- classifier pair A: `0x8175` class-map (`0x8306`) feeds draw switch
  `0x85D0` (`0x8A02`)
- classifier pair B: `0x8332` class-map (`0x84C5`) feeds draw switch
  `0x8B18` (`0x8CDA`)
- joined map currently confirms class indices `4..0xD` selecting distinct
  draw handlers (`0x884C`, `0x8873`, `0x88D5`, `0x8918`, `0x8C26`, `0x8C5A`,
  `0x8C84`, `0x8CA7`, etc.)

Prototype integration (new):

- `scratch/render_map_3d_owner_prototype.py` now has optional
  `--use-classifier-c4-override`
  - loads `scratch/wmaze_classifier_class_maps.json`
  - applies corrected `8175` map index (`c4`) -> class-code
  - maps class-code -> stream-set via configurable
    `--classifier-class-to-set-map`
  - records applied overrides in debug JSON under
    `map_stream_info.classifier_c4_override`
- same override controls were mirrored to
  `scratch/run_mazedata_3d_viewer.py`

Classifier index emulation integration (new):

- `scratch/render_map_3d_owner_prototype.py` now also supports
  `--use-classifier-index-emu`
  - emulates corrected classifier gating skeleton from `0x8175/0x8332`:
    - variant A gate: `(c2 + 1) % 4 == facing_index` -> index := `c4`
    - variant B gate: `(c2 + 3) % 4 == facing_index` -> index := `c4`
    - else index remains helper-seed (provisional wall-based seed map)
  - index -> class code from extracted class-map tables
  - class code -> set index via `--classifier-class-to-set-map`
  - helper-seed index map is configurable via `--classifier-seed-map`
- viewer mirror:
  - `scratch/run_mazedata_3d_viewer.py` adds the same
    `--use-classifier-index-emu` / `--classifier-seed-map` controls

Stress-scene result with current provisional seed/variant pairing:

- map11 `(131,140,W)`: classifier-index mode currently matches classifier-c4
  output and differs from baseline record-run.
- map12 `(122,149,S)`: classifier-index mode currently matches baseline
  record-run (no change under current gate/seed state at this viewpoint).

Interpretation:

- the emulation scaffolding is in place, but helper-seed semantics (the true
  behavior of helper returns feeding `DI` before table override) are still the
  main unknown and are now the primary parity blocker.

Additional inference tooling (new):

- `scratch/infer_classifier_index_emu_policy.py`
  - searches per-wall `(variant, seed_index)` policies against dispatch
    constant consistency.
  - output: `scratch/map_owner_streams/inferred_classifier_index_policy.json`
  - current result remains weak globally (not used as default).
- `scratch/infer_classifier_index_feature_policy.py`
  - tests small seed-feature formulas (`c2/c4` transforms + constants).
  - output: `scratch/map_owner_streams/classifier_index_feature_policy.json`
  - current result also weak globally.
- `scratch/infer_class_to_set_map_from_c4.py`
  - infers `class_code -> set_index` from corrected classifier outputs.
  - output: `scratch/map_owner_streams/inferred_class_to_set_map_from_c4.json`

Renderer support added:

- `render_map_3d_owner_prototype.py`:
  - `--auto-classifier-class-to-set-map`
  - `--classifier-class-to-set-map-file`
- `run_mazedata_3d_viewer.py`:
  - `--auto-classifier-class-to-set-map`
  - `--classifier-class-to-set-map-file`

Current stress-scene behavior:

- using `--use-classifier-c4-override --auto-classifier-class-to-set-map`,
  both current stress scenes match the present `record_run` baseline output
  (`MAD=0` for map11/map12 stress frames).

MAZEDATA blit-mode integration (new):

- A major gap was that renderer composition ignored display-record `aux` byte.
- Added aux-aware blit handling in prototype/viewer:
  - `--mazedata-blit-mode legacy|transparent|opaque|heuristic`
  - default now uses `heuristic` path in both scripts
- Implementation:
  - prebuild two sprite layers per tile:
    - transparent layer (`palette index 0` clear)
    - opaque layer (`palette index 0` kept as black)
  - choose layer per record via aux-mode policy

Code:

- `render_map_3d_owner_prototype.py`
  - `build_sprite_layers`
  - `aux_is_opaque`
  - `render_owner_blitmode`
- `run_mazedata_3d_viewer.py`
  - mirrored `--mazedata-blit-mode` handling

Comparison outputs:

- `scratch/proto_decode_compare/map11_blit_mode_sheet.png`
- `scratch/proto_decode_compare/map12_blit_mode_sheet.png`

Still missing for full game-parity 3D:

- exact semantics of classifier handlers in the `7CA8/8091/824E` path
  (which per-slot state bytes/words are set for each wall category).
- exact call-level behavior of the draw helpers (`0x85D0`, `0x8B18`, `0x8D07`,
  `0x8DF6`, `0x8E59`, `0x8E8A`, `0x8EBB`) beyond constant extraction.
- integrating those true classifier outputs into the runtime renderer path
  instead of inferred set/slot policy heuristics.

Record-primitive mode wiring (new):

- `record_primitive` / `record_primitive_high` are now fully wired in both:
  - `scratch/render_map_3d_owner_prototype.py`
  - `scratch/run_mazedata_3d_viewer.py`
- Added explicit single-record image cache by record index and end-to-end
  `pick_kind == "record_primitive"` draw path.

Validation:

- map11 high-code viewpoint `(129,140,N)` now reports:
  - run mode: `pick_kind=record_run`
  - primitive mode: `pick_kind=record_primitive`
- output files:
  - `scratch/proto_decode_compare/map11_w129_140_run.json`
  - `scratch/proto_decode_compare/map11_w129_140_primitive.json`
  - `scratch/proto_decode_compare/map11_w129_140_run_vs_primitive.png`

Important finding:

- those two frames are pixel-identical at that viewpoint (for code 158),
  because this dataset segment currently resolves to a one-record run there.
- so the major mismatch is not primarily `record_run` vs `record_primitive`;
  it is deeper render-pipeline behavior.

Corrected render-pipeline extraction (new):

- Added `scratch/extract_wmaze_render_pipeline.py`
- Output: `scratch/wmaze_render_pipeline.json`
- This captures draw-pass order from corrected WMAZE disassembly window
  `0x91A0..0x9758` and shows the real multipass structure:
  - repeated conditional draw+cleanup calls per depth using
    `0x85D0`, `0x8B18`, `0x8D07` plus cleanup helpers
    `0x8DF6`, `0x8E59`, `0x8E8A`, `0x8EBB`, `0x8EE8`, `0x8F1A`, `0x8F4C`.

Implication:

- current prototype (single wall image per slot) is structurally too simple.
- to match the game, renderer must emulate this per-depth multipass pipeline
  and the flag-mutating cleanup passes, not just map stream code selection.

Pass-parameter and class-index bridge (new):

- Added `scratch/build_wmaze_pass_parameter_map.py`
  - output: `scratch/wmaze_render_pass_param_map.json`
  - provides per-pass call binding:
    - draw helper target
    - `[bp+4]` source (`bx` / `[0x5040]`)
    - `[bp+6]` source (`[0x5220]`, `[0x5222]`, `[0x5224]`, `[0x5226]`, `[0x5228]`, or immediate)
    - immediate-to-stack mapping (`bp+8`, `bp+A`, ...)
- Added `scratch/build_class_code_to_draw_index_map.py`
  - output: `scratch/wmaze_class_code_to_draw_index_map.json`
  - confirms concrete class-code -> draw-switch-index map, and it matches for:
    - `8175 -> 85D0`
    - `8332 -> 8B18`

Confirmed map:

- `4->7`, `5->1`, `6->2`, `7->8`, `8->3`, `9->4`,
  `10->9`, `11->10`, `12->11`, `13->12`

Why this matters:

- We now have all fixed constants needed to wire runtime pass invocation:
  1) classify cell (`class_code`)
  2) convert to draw-switch index
  3) invoke the exact pass helper with mapped stack constants for that pass.

Experimental WMAZE pass compositor (new):

- `scratch/render_map_3d_owner_prototype.py` now has:
  - `--use-wmaze-pass-render`
  - `--wmaze-pass-param-file`
  - `--wmaze-draw-offsets-file`
  - `--wmaze-class-code-to-draw-map-file`
- This path executes the real extracted WMAZE pass order (`0x85D0`, `0x8B18`,
  `0x8D07` sequence) and composites MAZEDATA *primitive records* in pass order.
- It falls back to the legacy slot compositor if no pass primitives are
  resolved.

New extraction used by pass compositor:

- `scratch/extract_wmaze_draw_handler_record_offsets.py`
  - output: `scratch/wmaze_draw_handler_record_offsets.json`
  - scans corrected helper disassembly (`84EC..8F80`) and records handler draw
    call sites plus `bp+offset` parameter sources used to select MAZEDATA
    record indices.

Current approximation limits (important):

- cleanup helpers are not yet emulated (only pass order is used)
- `0x85D0` draw-index selection now uses a partial `0x7D8C` emulator:
  - base wall class from visible slot wall value (`0..3`)
  - exact tail-switch transform from `c4/c2` (`0x8055..0x8156`)
  - side-neighbor shortcut approximation for `side = -1/+1`
  - still missing exact `7D0B` coordinate-helper semantics and cleanup-flag state
- `0x8B18` left/right passes can use classifier-derived draw-index overrides
  when `--use-classifier-index-emu` is enabled
- main-loop pass gating now has partial state emulation:
  - per-depth top-level flags initialized as in `0x90C0` render loop
  - cleanup helpers can clear a subset of top-level gates (`507a`, `5092`)
  - partial `7D8C` top-flag side effects applied from slot wall classes:
    - `wallv == 0` -> clear `508a`
    - `wallv == 1` -> clear `5092`, `509a`, `50a2`
  - `ax == -1` path (`5072`, `507a`, `5082` clears) is still not exact
    because `7D0B/28AF` path semantics are not fully emulated yet

Observed effect:

- Pass compositor is now materially different from slot compositor on test
  frames (thousands of pixels changed), and executes all major passes on
  side-wall scenes.
- `0x7D8C` draw-index emulation changed pass renders again:
  - map12 `(147,158,N)`: `795` pixels changed vs prior pass mode
  - map11 `(129,140,N)`: `2105` pixels changed vs prior pass mode
- Added partial top-gate side effects/gate suppression changed:
  - map11 `(129,140,N)`: `2933` pixels changed vs `7D8C`-only pass mode
  - map12 `(147,158,N)`: no image change on current test frame (gate trace shows
    skips in other passes are scene-dependent)

Further `7D8C` parity fixes (new):

- `render_map_3d_owner_prototype.py` now applies `7D8C` top-flag side effects
  per call/slot (`center`, `left`, `right`) instead of reusing center `c4` for
  all three pre-pass calls (`0x5220`, `0x5226`, `0x5228` path in `0x90C0`).
- The `0x7E54` dungeon special-case bypass (`map 0x0C` and `[bp+0xC] < 9`) now
  uses local `cell_ref` coordinates as proxy (`row`, fallback `col`) instead of
  world `wy`.
- `visible_details` now stores slot-specific map metadata:
  - `center`: current corridor cell
  - `left`: side-adjacent cell
  - `right`: side-adjacent cell
  This feeds both `7D8C` gate-side effects and classifier/draw-index emulation
  with the correct side tile classes (`c4/c2`), instead of sharing center tile
  metadata across all slots.
- `0x8B18` classifier-derived draw-index overrides now consume left/right slot
  `c4/c2` independently (previously center-only).

Observed effect of the slot-specific metadata patch:

- map11 `(129,140,N)` pass mode (`gateplus3` -> `gateplus4`)
  - `wmaze_pass_drawn`: `0 -> 4`
  - `wmaze_pass_gate_trace` entries: `9 -> 3`
  - image changed by `1384` pixels
  - surviving passes are depth-1 side `0x85D0` passes (left/right), which is a
    better structural match than the prior full gate wipe.
- map12 `(147,158,N)` pass trace remained stable in pixels for the tested view
  (`7` pass draws, `2` gate skips), but the code path is now using slot-correct
  metadata (important for asymmetric scenes).

Cleanup-helper emulation upgrades (new):

- Implemented exact cleanup helper predicates from corrected disassembly for:
  - `0x8DF6`, `0x8E59`, `0x8E8A`, `0x8EBB`, `0x8EE8`, `0x8F1A`, `0x8F4C`
- The prototype now models marker bytes `0x5066/0x5067/0x5068` (flat arrays) and
  sets them from the `7D8C` `0x7E7D` path:
  - side `-1` -> `0x5066 + 3*depth`
  - side `0`  -> `0x5067 + 3*depth`
  - side `+1` -> `0x5068 + 3*depth`
- Cleanup helper predicates now use the real patterns:
  - `8E59/8E8A`: clear on `class != 0`, or on `class == 0` only if
    `byte[0x5067 + 3*depth] == 1`
  - `8DF6/8EBB/8EE8/8F1A/8F4C`: clear on `class == 2`, `class >= 5`, or when
    `byte[0x506{6,7,8} + (3*depth + class)] == 1`
- Implemented `0x8DF6` effect on `0x521E` (render-loop depth limit):
  - prototype pass loop now tracks and applies the `min(0x521E, depth+3)` shrink
    behavior.

`7D8C` side-call early-return guard (new):

- Added a guard so the prototype only applies `7CA8/7E54`-derived side effects to
  side calls (`bp+0xE = -1/+1`) when the side call appears to *not* take the
  early `7D0B` success return path.
- Current approximation uses slot-specific side-cell existence (`cell_ref.block`)
  as the `7D0B` success proxy.
- Center call (`bp+0xE = 0`) still always enters the `7CA8` path, matching the
  real `7D8C` flow (`7D94..7D9A`).

`7D0B` early-shortcut inversion fix (new):

- Corrected a branch-condition bug in the prototype `0x85D0` draw-index emulator
  (`emulate_7d8c_draw_index_from_view`):
  - The map-mode-dependent shortcut class (`0` on maps `0x0A/0x0C`, else `2`)
    is returned when `7D0B` fails (nonzero return / no side-cell resolution),
    not when it succeeds.
- This was previously inverted for side calls, causing `0x5226/0x5228`-style
  `0x85D0` draw-index overrides to flip in some scenes.

Observed effect on current regression scenes:

- `map11 (129,140,N)`:
  - `d1:0x85D0:left  2 -> 0`
  - `d1:0x85D0:right 2 -> 0`
- `map12 (147,158,N)`:
  - `d1:0x85D0:left  0 -> 2`
  - `d1:0x85D0:right 0 -> 2`
- These reference frames were pixel-stable after the fix, but the draw-index
  decisions now match the `7D8C` branch direction instead of the inverted model.

Exact `7ADE/7B1B/7D0B` probe helpers (new):

- Added Python emulation helpers in `render_map_3d_owner_prototype.py` for:
  - `7ADE` block hit test (`emulate_7ade_hit`)
  - `7B1B` block search / local coord conversion (`emulate_7b1b_probe`)
  - `7D0B` side probe (rotation by facing + `7B1B`) (`emulate_7d0b_side_probe`)
- `render_wmaze_pass_experimental(...)` now uses the `7D0B` probe helper for
  `7D8C` top-flag side-effect prepass decisions and local-row (`[bp+0xC]`) proxy,
  with a tracked `0x4FA6`-style last-block cache across side probes.
- `0x85D0` side draw-index shortcut checks now use:
  1) `7D0B`-style rotated probe from center cell, and
  2) `7B1B`-style block probing (fallback) instead of direct side-slot presence.
- `0x85D0` draw-index override generation in `main()` now runs with a shared
  per-depth `7B1B` cache across center/left/right calls (closer to the real
  `0x5220/0x5226/0x5228` call ordering).

Observed effect (current tests):

- No additional pixel or pass-trace changes on:
  - `map11 (129,140,N)`
  - `map12 (147,158,N)`
  - asymmetric probe scene `map11 (128,138,N)`
- This still removes a proxy layer and gives us disassembly-faithful probe
  semantics for the next round of parity work.

`7D8C` local-variable mapping correction (new):

- Re-derived the `7D8C -> 7D0B -> 7B1B` argument order from the actual push order
  and corrected the meaning of `7D8C` locals:
  - `[bp+4]` / `[bp+6]`: world X / world Y (in-out through `7D0B`)
  - `[bp+8]` / `[bp+0A]`: local X / local Y (written by `7B1B`)
  - `[bp+0C]`: block index (written by `7B1B`)
- This means the `0x7E54` map-`0x0C` special-case (`cmp [bp+0xC], 9`) is a
  **block-id** test, not a local-row/local-col test.
- Prototype fix: `7D8C` top-flag side-effect prepass now feeds the `0x7E54`
  bypass with block index from the exact probe helper (`probe["block"]`) / center
  `cell_ref.block`, instead of row/col proxies.

Post-pass `0x84F1` queue consumer discovered (major missing stage):

- The corrected render-loop continuation at `0x9761..0x98C5` (after `0x9758`) walks
  a command queue built at `0x50D0` with count `0x50CE`.
- This queue is populated by helper handlers via `call 0x84F1` (numerous callsites
  inside `0x85D0` / `0x8B18` handlers).
- Confirmed queue entry stride is **11 bytes** (`0x0B`):
  - words at `+0`, `+2`, `+4`, `+6`
  - bytes at `+8`, `+9`, `+A`
  - base = `0x50D0 + entry_index * 0x0B`
- Consumer behavior (`0x9761..0x98C5`):
  1. First pass (per depth `0x5040`, reverse queue order):
     - only entries with `byte[+8] == 0xFF`
     - computes parity `0x521C` from `byte[+A] + 0x4FA4 + 0x4FA2 + 0x4F9A`
     - emits up to two `call 0x36AC` draws using pairs:
       - (`+0`, `+4`) and (`+2`, `+6`) with color/attr `byte[+9]`
  2. Second pass (same depth, reverse queue order):
     - only entries with `byte[+8] != 0xFF`
     - calls `0x3670` with all queue fields (`+0,+2,+4,+6,+8,+9,+A`)
  3. decrements `0x5040` and repeats for prior depth
- This means the current prototype pass compositor is missing a real post-pass
  queue-render stage even when MAZEDATA primitive pass composition is correct.

New artifacts for queue-stage reverse engineering:

- Corrected queue-consumer disassembly slice:
  - `scratch/wmaze_9761_98c5_disasm_corrected.txt`
- New `0x84F1` handler-call extractor:
  - `scratch/extract_wmaze_84f1_handler_calls.py`
  - output `scratch/wmaze_84f1_handler_calls.json`
- The extractor records `0x84F1` callsites by class-handler and reconstructs the
  **callee argument order** (`[bp+4]..[bp+10]`) by resolving nearby `push ax`
  sources to immediates / `bp+offset` / expressions. This is the next bridge for
  queue emulation.

Observed effect on current regression scenes:

- `map11 (129,140,N)` and `map12 (147,158,N)` showed no additional pixel change
  from the cleanup-helper exact predicate patch or the side-call `7D0B` guard on
  top of `gateplus4`, but these changes remove known structural inaccuracies in
  the emulation and should matter on deeper/asymmetric scenes.

Additional debug output:

- prototype debug JSON now includes:
  - `wmaze_pass_drawn`
  - `wmaze_pass_drawidx_overrides`
  so pass-by-pass draw-index source decisions can be audited directly.
- prototype debug JSON now also embeds estimated queue-stage traces (when
  `--use-wmaze-pass-render` is enabled and `0x84F1` producer handlers are hit):
  - `wmaze_84f1_queue_entries_estimated`
  - `wmaze_84f1_consumer_events_estimated`
  - `wmaze_84f1_unresolved_calls`
  This comes from a shared structural simulator (`scratch/simulate_wmaze_84f1_queue_trace.py`)
  that reconstructs `0x84F1` queue entries from `wmaze_pass_drawn` and runs a
  `0x9761..0x98C5`-style reverse-order consumer pass.

Validation note (embedded queue trace):

- `map12 (147,158,N)` with current pass emulation (`map12_w147_158_wmazepass_queueembed1`)
  produced:
  - `7` pass draws
  - `2` estimated `0x84F1` queue entries
  - `2` estimated queue-consumer events (`3670`-phase structural events)

## New Finding: Helper Indices Partition Into Direct vs Queued Draw Paths

New artifacts:

- `scratch/extract_wmaze_helper_draw_calls.py`
  - output `scratch/wmaze_helper_draw_calls.json`
  - extracts direct helper-side `call 0x36AC` / `call 0x3670` callsites by class-switch index
- `scratch/build_wmaze_helper_draw_mode_map.py`
  - output `scratch/wmaze_helper_draw_mode_map.json`
  - merges direct draw call extraction with `0x84F1` producer extraction

Observed partition (no overlap in extracted handlers):

- `85D0.class_draw_switch`
  - direct `36AC` only: `0,2,5,6,7,10,11,12,13,14`
  - queued `84F1` only: `1,3,4,8,9`
  - both: none
- `8B18.class_draw_switch`
  - direct `36AC` only: `1,3,4,5,6,7,10,11,12,13`
  - queued `84F1` only: `8,9`
  - none (in extracted range): `0,2`

Implication:

- The renderer does not just "sometimes also queue extras"; for these helper indices
  it often chooses **one draw mode or the other** (immediate `36AC` vs deferred `84F1` queue).
- This explains why the prototype can still diverge even when pass order and MAZEDATA
  primitive composition look plausible: some class indices require the post-pass queue
  stage instead of direct helper-side draw behavior.

Queue simulator improvement (exact `84F1` field modeling):

- `scratch/simulate_wmaze_84f1_queue_trace.py` now annotates queue entries with exact
  byte-field semantics (`type`, `attr`, `depth_tag`) and marks the unresolved DGROUP
  table adjustments applied by `0x84F1` to `x0/y0`:
  - x-adjust table `DS:[0x36E4 + type*0x13A + 2*attr]`
  - y-adjust table `DS:[0x3717 + type*0x13A + attr]`
- These tables are **not** in `WMAZE.OVR` (they are DS/DGROUP addresses), so they
  remain a separate reverse-engineering target.

## Prototype Update: Optional Helper Draw-Mode Gating

`scratch/render_map_3d_owner_prototype.py` now supports an optional structural
accuracy gate:

- `--respect-wmaze-helper-draw-modes`
- mode data from `scratch/wmaze_helper_draw_mode_map.json`

Behavior:

- If a pass resolves to a helper index classified as `queue_84f1_only`, the
  prototype suppresses direct MAZEDATA primitive compositing for that pass.
- The pass is still recorded in `wmaze_pass_drawn` with:
  - `suppressed_by_helper_draw_mode = "queue_84f1_only"`
  - `helper_draw_modes = ["queue_84f1"]`
  - `records = []`
- This preserves `0x84F1` queue reconstruction (embedded queue trace still sees
  the pass) while preventing a known structural mismatch.

Validation (`map12 147,158,N`):

- mode-gated pass render (`...modegate2`) retained:
  - `7` pass rows total
  - `2` suppressed queue-only `8B18 idx=8` passes
  - `2` estimated `0x84F1` queue entries / `2` consumer events
- no pixel difference vs the non-gated image on this specific frame (scene uses
  queue-only passes that were not producing direct primitive blits anyway), but
  the pass trace is now more faithful to the helper behavior split.

## New Finding: WROOT `36AC` / `3670` Are Runtime-Patched Driver Thunks

New artifact:

- `scratch/extract_wroot_wrapper_thunk_table.py`
  - output `scratch/wroot_wrapper_thunk_table.json`

Confirmed from `WROOT.EXE` (loaded image, EXE header stripped):

- Wrapper `0x3670` (`WMAZE` queue consumer non-`0xFF` path) dispatches via:
  - `lcall cs:[0x1BB2]`
  - current table entry bytes = `2b 01 00 00` => far ptr `0000:012B`
- Wrapper `0x36AC` (`WMAZE` direct + queue `0xFF` path) dispatches via:
  - `lcall cs:[0x1BC6]`
  - current table entry bytes = `3f 01 00 00` => far ptr `0000:013F`

Observed wrapper thunk table pattern:

- `cs:[0x1B96..0x1BC6]` entries are far pointers with:
  - offset = sparse subset of `0x010F..0x013F` (step 4)
  - segment = `0x0000` for all observed entries in the static EXE image

Implication:

- These are not final draw-function targets in the shipped static `WROOT.EXE`.
- The most likely model is a runtime-patched graphics-driver thunk table:
  - offsets (`0x010F..0x013F`) are fixed entrypoints inside a loaded driver blob
  - segment words are filled later at runtime

This explains why static disassembly of `WROOT:0x3670/0x36AC` alone stalls at
wrapper thunks, and why exact deferred queue rendering still needs either:

1. the runtime-patched thunk table segment value (and target code), or
2. behavioral inference from higher-level call patterns / render outputs.

## Breakthrough: WROOT Draw Wrappers Resolve Into `EGA.DRV` Export Stubs

New artifacts:

- `scratch/extract_ega_drv_export_stubs.py`
  - output `scratch/ega_drv_export_stubs.json`
- `scratch/dump_ega_drv_key_exports_disasm.py`
  - output `scratch/ega_drv_key_exports_disasm.txt`
- `scratch/compare_graphics_drv_export_tables.py`
  - output `scratch/graphics_drv_export_table_compare.json`
- `scratch/extract_ega_drv_key_tables.py`
  - output `scratch/ega_drv_key_tables.json`

Key finding:

- `EGA.DRV` is a COM-style driver image (assume load base `0x100`) with an export
  stub table at the start:
  - pattern: `call rel16 ; retf`
- The WROOT thunk offsets match these export stub addresses exactly.

Confirmed mappings:

- `WROOT 0x3670` (`lcall cs:[0x1BB2]` -> thunk offset `0x012B`)
  - `EGA.DRV export 0x012B`
  - export stub target: `EGA.DRV 0x1D94`
- `WROOT 0x36AC` (`lcall cs:[0x1BC6]` -> thunk offset `0x013F`)
  - `EGA.DRV export 0x013F`
  - export stub target: `EGA.DRV 0x0B93`

This removes the previous ambiguity around the wrappers: we now know the actual
driver routines implementing the queued/directed draw operations for EGA mode.

### Cross-driver confirmation (standardized driver API)

`CGA.DRV`, `EGA.DRV`, `HERC.DRV`, and `TANDY.DRV` all expose the same 17 export
stub addresses (COM-style load base `0x100`):

- common stub range includes:
  - `0x0103, 0x0107, ... , 0x0143`
  - notably `0x012B` and `0x013F`

This strongly confirms WROOT is calling a **standardized graphics driver API**,
and `0x3670` / `0x36AC` are mode-agnostic wrapper IDs whose actual behavior is
implemented per-driver.

Examples from the comparison artifact:

- stub `0x012B` targets:
  - `CGA.DRV 0x17AB`
  - `EGA.DRV 0x1D94`
  - `HERC.DRV 0x1997`
  - `TANDY.DRV 0x1BE7`
- stub `0x013F` targets:
  - `CGA.DRV 0x08DB`
  - `EGA.DRV 0x0B93`
  - `HERC.DRV 0x0876`
  - `TANDY.DRV 0x08F3`

### Driver-local tables used by the EGA implementations

`scratch/extract_ega_drv_key_tables.py` extracts static table bytes referenced by
`EGA.DRV:0x0B93` / `EGA.DRV:0x1D94`.

Important result:

- `EGA.DRV cs:0x192` (used with `XLATB`) is a 256-byte **bit-reversal table**
  (`x -> reverse_bits_8(x)`).

This matches:

- `EGA.DRV:0x0B93` composite/translated path (the `arg3 != -1` branch behind `36AC`)
- `EGA.DRV:0x1D94` optional transform paths (`flags & 1`, `flags & 2`) behind `3670`

Also extracted:

- `cs:0x17A` word table used by `0x1D94` as a type/resource dispatch offset table
  (`index = type * 2`).

### Stack-argument offset note (important for reading driver disassembly)

The driver internal target sees an extra stack layer because the call chain is:

1. WMAZE calls WROOT wrapper (`near`)
2. WROOT wrapper `lcall`s driver export stub (`far`)
3. driver export stub `call`s internal routine (`near`)

Result: inside the driver internal routine, wrapper arguments are shifted and
begin at `[bp+0x0C]` (not `[bp+4]`).

Examples:

- `EGA.DRV 0x0B93` (behind WROOT `0x36AC`)
  - uses `[bp+0x0C]`, `[bp+0x0E]`, `[bp+0x10]` => wrapper args 1..3
  - checks wrapper arg3 (`[bp+0x10]`) against `0xFFFF`
- `EGA.DRV 0x1D94` (behind WROOT `0x3670`)
  - uses `[bp+0x0C]` as a resource/type index
  - uses `[bp+0x16]` as flags (bit tests observed)
  - uses `[bp+0x1A]` as pointer to attribute byte/word storage (matches queue consumer passing `&attr`)

Implication:

- We can now reverse the real EGA draw semantics for queued/non-queued operations
  directly in `EGA.DRV`, instead of being blocked at WROOT wrapper stubs.

### Updated queue-field interpretation (based on `EGA.DRV:0x1D94`)

The previous queue trace labels `x0/y0/x1/y1` were too generic. For the
`0x3670` queue consumer path (type != `0xFF`), `EGA.DRV:0x1D94` strongly
indicates the queue words behave like:

- `w0` (queue `+0`) = x position
- `w2` (queue `+2`) = y position
- `w4` (queue `+4`) = left clip boundary
- `w6` (queue `+6`) = right clip boundary

and the queue consumer calls:

- `3670(type, w0, w2, w4, w6, 0, 0, &attr_local)`

The queue-trace simulator now preserves exact queue layout aliases:

- `w0`, `w2`, `w4`, `w6`
- `b8_type`, `b9_attr`, `bA_depth`

while keeping the older field names for compatibility.

### `36AC` queue-pair note (based on `EGA.DRV:0x0B93`)

For the `type == 0xFF` queue subpass, `0x36AC` arguments are not simple screen
X values. The queue consumer builds wrapper calls of the form:

- `36AC(desc_a_or_b, attr, desc_alt_or_-1)`

and `EGA.DRV:0x0B93` uses those arguments as descriptor/table indices with two
execution paths:

- arg3 == `-1` : single-descriptor draw path
- arg3 != `-1` : composite/translated draw path (uses driver xlat table)

## Additional EGA Driver Queue-Path Findings (`0x3664` / `0x3670`)

New/updated artifacts:

- `scratch/dump_ega_drv_key_exports_disasm.py`
  - `scratch/ega_drv_key_exports_disasm.txt` now includes:
    - `EGA.DRV:0x1D25` (WROOT `0x3664`)
    - `EGA.DRV:0x220C` (helper used by `0x1D94`)
- `scratch/extract_ega_drv_key_tables.py`
  - corrected `scratch/ega_drv_key_tables.json`
- `scratch/extract_wmaze_wroot_wrapper_calls.py`
  - output `scratch/wmaze_wroot_wrapper_calls.json`

### Corrected `0x17A` table boundary (important correction)

The earlier broad dump of `EGA.DRV cs:0x17A` was too long and overlapped the
unrelated `0x192` bit-reversal xlat table.

Correct bounds:

- `0x17A .. 0x18D` = 10 words (resource/type dispatch table)
- `0x18E` = separate word used by descriptor draw logic (`0x0B93`)
- `0x190` = runtime word updated by loader path (`0x0731`)
- `0x192 .. 0x291` = 256-byte xlat table

Correct `0x17A` values (10 entries):

- `0x0000, 0x0180, 0x0340, 0x0600, 0x0700, 0x0D00, 0x1300, 0x1900, 0x1A00, 0x1B00`

Also useful:

- `0x184 .. 0x18D` (5 words) is a tail subrange used by `EGA.DRV:0x06F0`.

### `EGA.DRV:0x1D25` (WROOT `0x3664`) is the resource RLE chunk loader

The `0x1D25` disassembly confirms:

- wrapper arg1 (internal `[bp+0x0C]`) = DOS file handle
- wrapper arg2/arg3 (internal `[bp+0x0E]`, `[bp+0x10]`) = seek offset (DX:CX)
- wrapper arg6 (internal `[bp+0x16]`) = resource `type`

Behavior:

- computes destination segment:
  - `cs:[0x169] + cs:[0x17A + type*2]`
- uses scratch segment `cs:[0x16D]`
- seeks (`int 21h`, AH=`42h`) and reads compressed bytes (`AH=3Fh`)
- decodes a simple RLE stream into the destination resource segment:
  - `0x00` terminator
  - high bit clear = literal run (`rep movsb`)
  - high bit set = fill run (`rep stosb`)

This is the loader that populates the resources later consumed by `0x1D94`
(`3670`) and likely by related driver draw paths.

### `EGA.DRV:0x220C` (called by `0x1D94`) decodes sprite records into scratch

`0x1D94` repeatedly calls `0x220C` for nonzero resource-record bytes while
building the queued draw image in scratch (`cs:[0x16D]`).

Observed `0x220C` behavior:

- decodes a resource record selected by `AL` into a `0x18`-byte entry table
- uses width/height metadata from the `0x1D94` local state (`[bp-2]`, `[bp-4]`)
- composites 4 bitplanes into the scratch buffer in `cs:[0x16D]`
- honors the same transform flags (`flags & 1`, `flags & 2`) used later by `0x1D94`

Practical implication:

- We now have the real queue-path decode stages identified:
  1. `0x3664` / `1D25` loads RLE resource chunks by `type`
  2. `0x3670` / `1D94` + `0x220C` decodes records into scratch
  3. `0x1D94` applies clipping/transforms and blits to the EGA target

### WMAZE wrapper-call scan correction (important)

The first `WMAZE` wrapper-call scan result was a false negative. Two issues caused it:

- wrong WMAZE overlay addressing in call-target math (must use logical base `0x4572`)
- linear full-image disassembly stopping early on mixed code/data

`scratch/extract_wmaze_wroot_wrapper_calls.py` was corrected to:

- skip overlay header (`file + 0x000E`)
- use call target math with logical base `0x4572`
- detect calls via raw `E8 rel16` scanning instead of linear disassembly

Correct direct wrapper callsite summary in `WMAZE.OVR`:

- `0x36AC`: 28 direct calls
- `0x36A0`: 5 direct calls
- `0x3694`: 1 direct call
- `0x3670`: 2 direct calls
- direct `0x3664`: none found

Examples:

- queue consumer path:
  - `0x98AB -> 0x3670`
- post-pass present/update path:
  - `0x98D2 -> 0x36A0`
- direct `36AC` queue `0xFF` subpass:
  - `0x97E0`, `0x97F7`, `0x982E`, `0x9846`

Implication:

- The earlier claim that WMAZE only directly called `0x36DD` was incorrect.
- There are many direct wrapper calls in `WMAZE`; however `0x3664` (resource loader)
  still has no direct WMAZE callsite, so loader setup may still occur through a
  higher-level WROOT dispatch/initialization path.

### Cross-module wrapper census (new)

New artifact:

- `scratch/extract_game_module_wroot_wrapper_calls.py`
  - output `scratch/game_module_wroot_wrapper_calls.json`
- `scratch/extract_module_wrapper_call_args.py`
  - output `scratch/module_wroot_wrapper_call_args.json`
- `scratch/extract_winit_graphics_init_flow.py`
  - output `scratch/winit_graphics_init_flow.json`

This scans all game `.OVR`/`.EXE` modules for direct near-calls to WROOT graphics
wrappers using raw `E8 rel16` decoding (with corrected overlay header/base handling).

Key result:

- `WMAZE.OVR` directly calls `0x3670`, `0x3694`, `0x36A0`, `0x36AC` but not `0x3664`
- direct `0x3664` callers were found in other overlays:
  - `WBASE.OVR`
  - `WDOPT.OVR`
  - `WINIT.OVR` (multiple callsites)
  - `WMELE.OVR`
  - `WMNPC.OVR`

This narrows the loader-init search:

- `0x3664` resource loads are part of shared initialization / non-maze overlay paths,
  not something WMAZE directly issues during the queue consumer itself.

Observed direct `0x3664` call pattern (common form)

Across `WBASE/WDOPT/WINIT/WMELE/WMNPC`, one common caller pattern is:

- push `type`
- compute `bx = type * 0x13A`
- push `word ptr [bx + 0x36E4]`
- push `word ptr [bx + 0x36E2]`
- push `0`
- push `0`
- push `word ptr [0x4FE8]` (file handle)
- `call 0x3664`

This strongly suggests:

- `0x36E2/0x36E4` participate in a per-type resource offset table used during
  loader setup (even if the EGA driver's `0x1D25` path does not use every wrapper
  argument in the same way as other drivers might).

Important clarification from the mapped EGA implementation (`EGA.DRV:0x1D25`):

- EGA `0x3664` uses wrapper args:
  - arg1 = file handle
  - arg2/arg3 = seek offset (DX:CX)
  - arg6 = resource type
- In the common cross-overlay pattern above, arg2/arg3 are both `0`, which means:
  - the file handle likely already refers to a type-specific resource file (or file variant),
    so loading from offset `0` is expected.
- This resolves the apparent mismatch with `0x1D25` (which does require a source seek offset).

Notable `WINIT.OVR` detail:

- `WINIT` contains multiple `0x3664` call shapes, including callsites that pass
  explicit zero offsets and constants, making it a strong next target for tracing
  the graphics/resource initialization sequence.

`scratch/winit_graphics_init_flow.json` now captures an ordered startup call trace
for `WINIT` region `0x4640..0x5338`, including:

- filename/path builder calls (`0x0CD6`)
- open/read/close wrappers (`0x3E88`, `0x42D3`, `0x4309`)
- graphics wrapper calls (`0x3688`, `0x367C`, `0x3664`, `0x3670`, `0x3694`, `0x36A0`)

This provides a reusable sequence artifact for reconstructing the graphics init
pipeline instead of relying on ad-hoc disassembly windows.

### `WINIT` startup sequence gives a clean `0x3670` signature confirmation

From `WINIT.OVR` (`scratch/game_module_wroot_wrapper_calls.json` and disassembly around
`0x4EE0`), helper `0x4EE0` builds a direct `0x3670` call:

- pushes (callee order):
  - arg1 = `0` (type)
  - arg2 = `x`
  - arg3 = `y`
  - arg4 = `0` (left clip)
  - arg5 = `0x013F` (right clip)
  - arg6 = `0`
  - arg7 = `0`
  - arg8 = `&attr_local`
- then `call 0x3670`

This independently confirms the previously inferred `0x3670` wrapper signature used
in the queue consumer:

- `3670(type, x, y, clip_left, clip_right, flags1, flags2, &attr)`

and strongly supports the queue-field interpretation for non-`0xFF` entries:

- `w0 -> x`, `w2 -> y`, `w4 -> clip_left`, `w6 -> clip_right`.

It also suggests a common full-width clip bound:

- `clip_right = 0x013F` (319), matching EGA 320-wide rendering coordinates.

### `0x367C` sentinel behavior (new, high-confidence)

Cross-checking `WINIT` call patterns with `EGA.DRV:0x06F0` (WROOT `0x367C`) gives a
useful exact behavior:

- `0x367C` takes one argument (commonly a file handle)
- `EGA.DRV:0x06F0` checks `arg & 0x8000` (`test ah, 0x80`)
  - if clear: reads `0x8000` bytes from the file handle into a resource segment,
    then copies to `cs:[0x14D]`
  - if set (e.g. `0xFFFF`): skips the file read and only copies the existing
    cached resource chunk to `cs:[0x14D]`

`WINIT` uses both forms:

- `0x4EC3 -> 0x367C(handle)` : load/read a chunk
- `0x5097/0x5205/0x52D8 -> 0x367C(0xFFFF)` : reuse cached chunk (no file read)

This explains the repeated `0x367C(-1)` calls during UI animation/setup loops.

### `WINIT` offscreen-present pattern matches WMAZE usage

`WINIT` repeatedly uses:

- `0x3694` (EGA `0x0835`) on a handle-like object (`[0x4FBE]` / local handle)
- followed by `0x36A0` (EGA `0x08B3`) on that same handle

Observed examples:

- `WINIT:0x4EBA -> 0x3694`, then `WINIT:0x4ED8 -> 0x36A0`
- `WINIT:0x504B -> 0x3694`, then `WINIT:0x5079 -> 0x36A0`

This is consistent with the EGA mappings:

- `0x3694` = fill/write into offscreen planar buffer (`cs:[0x14D]`-backed descriptor)
- `0x36A0` = blit/present that descriptor to VGA/EGA memory

and matches the same `0x36A0` "present/update" role seen in `WMAZE` after queue
consumer draws (`0x98D2`) and in direct `0x3670` caller `0xB4DD`.

### WMAZE projection-table indexing references (`0x36E4` / `0x3717`)

New artifact:

- `scratch/extract_wmaze_projection_table_refs.py`
  - output `scratch/wmaze_projection_table_refs.json`

This finds two WMAZE code regions that reference the unresolved DGROUP projection
tables used by queued/non-queued `0x3670` draws:

- `WMAZE:0x84F1` queue producer (writes adjusted queue `+0/+2`)
- `WMAZE:0xB3AC..0xB4FF` direct `0x3670` caller (calls `0x3670`, then `0x36A0`)

Confirmed indexing pattern (same in both regions):

- x adjustment (`0x36E4`) uses:
  - `type*0x13A + 2*attr`
- y adjustment (`0x3717`) uses:
  - `type*0x13A + attr`

This corrects the earlier simplification where both x/y were annotated with
`2*attr`.

### Per-type record layout overlap hypothesis (new, strong)

The constants used by direct `0x3664` callers and the `0x84F1` / direct-`0x3670`
projection adjustments line up in a way that strongly suggests a shared per-type
record layout in DGROUP with stride `0x13A`:

- direct `0x3664` callers use:
  - `record_base + 0x00` via `[bx + 0x36E2]`
  - `record_base + 0x02` via `[bx + 0x36E4]`
  - where `record_base = type * 0x13A`
- projection adjustment paths use:
  - x table at `record_base + 0x02` (`0x36E4 + type*0x13A + 2*attr`)
  - y table at `record_base + 0x35` (`0x3717 + type*0x13A + attr`)

Since:

- `0x3717 - 0x36E2 = 0x35`
- `0x3717 - 0x36E4 = 0x33`

this implies the x/y adjustment tables likely live inside the same type record
header region, not in unrelated standalone arrays.

Practical interpretation:

- `0x36E2 + type*0x13A` appears to be the start of a per-type metadata block.
- `0x84F1` and direct `0x3670` callers are reading x/y projection adjustments
  from offsets within that metadata block.
- the `0x3664` common call pattern passing `[record+0]` / `[record+2]` may be
  cross-driver metadata convention (used by some drivers), while the EGA driver
  `0x1D25` path can ignore those wrapper args and use its internal `type` table.

This overlap is a strong clue for reconstructing the shared graphics metadata
format that feeds both resource loading and queued draw placement.

### WROOT path/string helper semantics (new extractor)

New artifact:

- `scratch/extract_wroot_path_helper_semantics.py`
  - output `scratch/wroot_path_helper_semantics.json`

This extracts and summarizes the key WROOT helpers behind WINIT filename/path
construction:

- `WROOT:0x0C82` = copy-until-delimiter helper
  - copies source to destination until NUL or delimiter match
  - includes the delimiter byte when matched
  - always writes trailing NUL
- `WROOT:0x0CD6` = path builder used before `0x3E88`
  - normalizes selector to `0/1` (with an EGA special case using `byte[0x3592]`)
  - selects a path-prefix table at `0x3540 + selector*0x50`
  - copies prefix through `':'` into temporary buffer `0x35EA`
  - appends caller suffix/template via `WROOT:0x38D7`
  - returns `AX = 0x35EA`
- `WROOT:0x38D7` = `strcat`-like helper
- `WROOT:0x390E` = `strcpy`-like helper

Important call-pattern correction:

- many `WINIT` callsites around `0x0CD6` push an extra word before `call 0x0CD6`
- that extra push is often intentionally left on the stack for the following
  `0x3E88` call
- so the observed "3-push pattern" does not mean `0x0CD6` consumes 3 args

This matters because it changes how we should read `WINIT` graphics-init traces
when reconstructing runtime resource filenames.

### WINIT uses shared WROOT filename buffers (`0x5004..0x50A4`) (new)

New artifact:

- `scratch/extract_winit_graphics_buffer_lifecycle.py`
  - output `scratch/winit_graphics_buffer_lifecycle.json`

This traces `WINIT` graphics-init call flow (`0x4580..0x5338`) and annotates use
of the shared WROOT buffer range:

- `0x5004..0x50A4`

Key findings:

- these addresses are **not** reliable static strings in `WINIT.OVR`
- in the static `WROOT.EXE` image, `0x5004..0x50A4` is zeroed (BSS-like)
- `WINIT` populates these buffers at runtime before graphics wrapper calls

Observed lifecycle anchors from `scratch/winit_graphics_buffer_lifecycle.json`:

- `WINIT:0x4950` calls `WROOT:0x390E` with source `0x5004` (shared buffer)
- `WINIT:0x49DC` calls `WROOT:0x0CD6` with suffix/template pointer `0x5010`
- `WINIT:0x49E3` then opens the resulting filename via `WROOT:0x3E88`
- `WINIT:0x4AAA` directly opens buffer `0x501C`
- `WINIT:0x4C08..0x4C40` calls `WINIT:0x45A3`
  (`open path + load indexed chunk via WROOT:0x21BB`) using path pointers:
  - `0x5029`, `0x5034`, `0x503F`, `0x504A`, `0x5055`
- `WINIT:0x4C4A` / `0x4CA3` call `WINIT:0x45E5`
  (`open path + load descriptor tables via WROOT:0x3688`) with:
  - `0x5060`, `0x50A4`
- `WINIT:0x4C61..0x4C99` runs another indexed-chunk load series via `WINIT:0x45A3`:
  - `0x506D`, `0x5078`, `0x5083`, `0x508E`, `0x5099`

Correction:

- earlier notes in this section described `0x45A3/0x45E5` as "shared-buffer fillers"
- that was too shallow / partially wrong
- they *consume* the shared WROOT path buffers as path arguments, but their main
  work is resource loading (`0x21BB`) and descriptor-table loading (`0x3688`)

Practical implication for the 3D renderer work:

- the queue-stage blocker is no longer "unknown queue structure"
- it is runtime initialization of shared WROOT graphics/path buffers + metadata
- static inspection of `WINIT` immediates like `0x5004` / `0x5010` / `0x501C`
  must be interpreted as references to shared runtime buffers, not inline text

### WROOT `0x21BB` chunk loader used by `WINIT:0x45A3` (new extractor)

New artifact:

- `scratch/extract_wroot_21bb_chunk_loader.py`
  - output `scratch/wroot_21bb_chunk_loader.json`

`WROOT:0x21BB` (called by `WINIT:0x45A3`) is now decoded as a mode-aware fixed-size
chunk loader:

- signature (inferred): `21BB(file_handle, chunk_index)`
- selects destination segment from `cs:[0x1B64]` / `cs:[0x1B68..0x1B74]`
- chooses read size based on `chunk_index` and mode flags (`cs:[0x1B4E]`,
  `cs:[0x1B50]`)
- performs DOS read (`AH=3F`) into the selected segment

This confirms:

- `WINIT:0x45A3` is a resource/chunk loader helper (after path construction/open)
- the `0x5029..0x5099` etc values are path-buffer pointers used to open files whose
  contents are loaded into driver/WROOT segments

### EGA.DRV `0x0731` (WROOT `0x3688`) descriptor-table loader (new extractor)

New artifact:

- `scratch/extract_ega_drv_0731_descriptor_loader.py`
  - output `scratch/ega_drv_0731_descriptor_loader.json`

Corrected COM-base disassembly shows:

- `WROOT:0x3688` -> `EGA.DRV export 0x0133` -> `EGA.DRV:0x0731`
- `0x0731` reads a descriptor header block (`0x800` bytes) into driver memory
- updates runtime descriptor pointers/offsets (including `cs:[0x18E]` and
  `cs:[0x190]`)
- reads remaining descriptor payload into subsequent driver segments

This directly explains the runtime descriptor state consumed later by
`WROOT:0x36AC` / `EGA.DRV:0x0B93` and is a key part of accurate queue-stage
rendering parity.

### WINIT path-buffer address -> filename mapping (new, high-confidence)

New artifact:

- `scratch/extract_winit_path_buffer_name_map.py`
  - output `scratch/winit_path_buffer_name_map.json`

This statically maps the `WINIT` shared path-buffer block to concrete filenames by
matching:

- the embedded filename string pool in `WINIT.OVR`
- the exact path-buffer address ordering used in init code
- the stride between path-buffer addresses
- the string length (+NUL)

High-confidence result (`stride == len(name)+1` matches throughout):

- `0x5029..0x5060`
  - `WFONT0.EGA .. WFONT4.EGA`, `MAZEDATA.EGA`
- `0x506D..0x50A4`
  - `WFONT0.CGA .. WFONT4.CGA`, `MAZEDATA.CGA`
- `0x50B1..0x50E8`
  - `WFONT0.T16 .. WFONT4.T16`, `MAZEDATA.T16`
- `0x50F5..0x513A`
  - `MASTER.HDR`, `DISK.HDR`, `MSG.HDR`, `PCFILE.DBS`, `MISC.HDR`, `MSG.DBS`,
    `SCENARIO.DBS`, `CREDITS.PIC`
- `0x5146..0x516D`
  - `TITLEPAG` mode variants (`EGA`, `CGA`, `CGA`, `T16`)
- `0x517A..0x51A1`
  - `GRAVEYRD` mode variants (`EGA`, `CGA`, `CGA`, `T16`)
- `0x51AE..0x51D5`
  - `DRAGONSC` mode variants (`EGA`, `CGA`, `CGA`, `T16`)

This gives a strong interpretation of the `WINIT:0x4BFE..0x4D09` mode-branch logic:

- first `0x45A3`/`0x45E5` group loads `WFONT*.EGA` + `MAZEDATA.EGA`
- second group loads `WFONT*.CGA` + `MAZEDATA.CGA` (also likely shared by HERC mode)
- third group loads `WFONT*.T16` + `MAZEDATA.T16` (Tandy path)

Ordering insight (important, corrected):

- in `WINIT:0x4A89`, the mode-specific `0x45A3/0x45E5` load groups run **before**
  the later `0x49CA` / `0x48EE` paths that first consume `0x5010` / `0x5004`
- this sequencing remains important, but not because `0x3688` directly writes
  WROOT path buffers
- corrected disassembly of `EGA.DRV:0x0731` (the target of `WROOT:0x3688`) shows
  it is a driver-internal descriptor-table loader that patches EGA driver state
  (`cs:[0x18E]`, `cs:[0x190]`, and related descriptor offsets)
- the runtime write path that populates WROOT path/template buffers
  (`0x5004..0x51D5`) is still unresolved

The widened lifecycle trace (`scratch/winit_graphics_buffer_lifecycle.json`) now
also annotates later path-buffer uses through `0x51D5`, including:

- `WINIT:0x4D18/0x4D2A/0x4D3C/0x4D4E` (`0x469F`) on
  `MASTER.HDR`, `DISK.HDR`, `MSG.HDR`, `PCFILE.DBS`
- `WINIT:0x4D58` (`0x46E4`) on `MISC.HDR`
- `WINIT:0x4D65/0x4DB6` path-build/open on `MSG.DBS` / `SCENARIO.DBS`
- `WINIT:0x4F74` path-build/open on `CREDITS.PIC`

Next RE target from this point:

- reverse the *runtime write path* that populates the shared WROOT path buffers
  (now mapped through `0x51D5`)
- keep `0x3688`/`0x0731` in parallel as the descriptor-state init path for
  `0x36AC`
- combine:
  - path/resource loading (`WINIT` + path buffers + `0x21BB` / `0x3664`)
  - driver descriptor initialization (`0x3688` / `0x0731`)
  to recreate the runtime state assumed by `WMAZE` queue draws
  (`0x3670` / `0x36AC`)

### WINIT path-buffer write scan across whole overlay (new extractor)

New artifacts:

- `scratch/extract_winit_path_buffer_writes.py`
  - output `scratch/winit_path_buffer_writes.json`
- `scratch/build_winit_graphics_resource_init_recipe.py`
  - output `scratch/winit_graphics_resource_init_recipe.json`

The whole-overlay scan tightens the path-buffer population picture:

- explicit helper writes found in `WINIT` only for:
  - `0x4FEE` (`MON00.PIC`) via `WROOT:0x390E`
  - `0x4FF8` / `0x5004` (`SOUND00.SND`) via `WROOT:0x390E`
  - `0x5010` (`CREDITS.PIC`) via `WROOT:0x0CD6`
  - `0x5125`, `0x512D`, `0x513A` (later DBS/PIC path builds) via `WROOT:0x0CD6`
- **no direct absolute writes** to `0x4FEE..0x51D5` were found in `WINIT`
- no visible helper-write call in `WINIT` populates the large filename blocks:
  - `0x5029..0x50E8` (`WFONT*`, `MAZEDATA*`)
  - `0x5146..0x51D5` (`TITLEPAG*`, `GRAVEYRD*`, `DRAGONSC*`)

This is a strong negative result and shifts the remaining hypothesis from
"missed WINIT helper" toward a shared WROOT loader/dispatcher path (or overlay-load
init path) that writes those buffers before the visible consumers execute.

The merged recipe (`winit_graphics_resource_init_recipe.json`) is useful because it
resolves the `WINIT` init trace to real filenames, e.g.:

- `WINIT:0x4C08..0x4C40` -> `WFONT0..4.EGA` via `0x45A3` (`WROOT:0x21BB`)
- `WINIT:0x4C4A` -> `MAZEDATA.EGA` via `0x45E5` (`WROOT:0x3688` / `EGA.DRV:0x0731`)
- analogous `CGA` / `T16` groups at `0x4C61..0x4CFB`

### WROOT file-driven loader/dispatcher `0x36DD/0x36E9` (new extractor)

New artifact:

- `scratch/extract_wroot_36dd_dispatcher_loader.py`
  - output `scratch/wroot_36dd_dispatcher_loader.json`

This closes a major gap in the "who populates shared WROOT memory?" question.

`WROOT:0x36DD` (wrapper entry at `0x36DC`) behaves as a loader/dispatcher:

- reads caller-provided base path pointer from stack into DGROUP scratch `0x06BE`
- calls `0x36E9`
- tail-jumps to the address returned in `AX` (`jmp ax`)

`WROOT:0x36E9` is a file parser / record loader:

- builds filename in a local buffer:
  - `strcpy(local, [0x06BE])`
  - `strcat(local, dgroup:0x0636)` (fixed suffix)
  - `open(local)`
- reads a `0x0E`-byte record header via `WROOT:0x42D3`
- validates header fields, including destination address floor checks that reach:
  - `>= 0x4572`
  - `>= 0x4FEE` (shared path-buffer region)
- performs two data reads into header-specified destination addresses:
  - `0x3817` (DOS read wrapper variant)
  - `0x42D3` (generic DOS read/write wrapper in read mode)
- returns header word `[bp-6]` in `AX`, which `0x36DD` immediately `jmp`s to

Practical implication:

- `WROOT` already has a data-driven mechanism that can write directly into the
  shared `0x4FEE..0x51D5` region.
- This is now the strongest concrete candidate for how the large pre-populated
  path-buffer blocks appear before `WINIT` consumes them.

Next RE target from here:

- identify the `0x36DD` file suffix (`dgroup:0x0636`) and record source file
- recover the exact `0x0E` record format field semantics
- trace which module/init path invokes `0x36DD` before `WINIT` path-buffer consumers
  (or prove it is part of the same startup chain)

### OVR file header format matches WROOT `0x36E9` exactly (new extractor)

New artifact:

- `scratch/extract_ovr_loader_records.py`
  - output `scratch/ovr_loader_records.json`

This extractor parses all `.OVR` files using the header semantics inferred from
`WROOT:0x36E9`, and the result matches cleanly:

- 14-byte header words:
  1. `0x00F2` magic
  2. code destination address
  3. code block length
  4. data destination address
  5. data block length
  6. data BSS tail length (zero-filled after data block)
  7. entry/dispatch address (returned by loader; `0x36DC` then `jmp`s to it)
- file layout:
  - `[14-byte header][code block][data block]`

This confirms the `0x36DD/0x36E9` path is the generic overlay loader/dispatcher for
the game’s `.OVR` modules.

Critical consequence for the path-buffer mystery:

- `WINIT.OVR` header decodes to:
  - `code_dest=0x4572`, `code_len=0x1229`
  - `data_dest=0x4FEE`, `data_len=0x01FE`
  - `data_bss_len=0x0000`
  - `entry=0x575D`
- `0x4FEE + 0x01FE = 0x51EC`, so the `WINIT.OVR` data block directly covers the
  entire shared path-buffer block (`0x4FEE..0x51D5`)
- the ASCII content of the `WINIT.OVR` data block is exactly the filename table that
  `WINIT` later consumes:
  - `MON00.PIC`, `SOUND00.SND`, `WFONT*.EGA/CGA/T16`, `MAZEDATA.*`,
    `MASTER.HDR`, `SCENARIO.DBS`, `TITLEPAG*`, `GRAVEYRD*`, `DRAGONSC*`, etc.

This resolves the major ambiguity:

- the large shared path-buffer blocks are **not** populated by visible `WINIT`
  helper writes
- they are preloaded from the `WINIT.OVR` data block by the WROOT overlay loader
  (`0x36DD/0x36E9`)

Additional useful confirmations from the extractor:

- `WMAZE.OVR` and `WBASE.OVR` also use the same loader format, with smaller
  data blocks at `0x4FEE` plus BSS tails extending the runtime DGROUP region
- `WMAZE.OVR` data block contains initial strings like `SAVEGAME.DBS` and
  `SOUND00.SND`, matching observed runtime buffer usage

Practical impact for renderer parity:

- shared WROOT path/template buffers can now be reconstructed exactly from the
  `.OVR` data block, without guessing or tracing hidden string-copy code
- this reduces the init-state uncertainty before tackling exact queue-stage
  `0x3670` / `0x36AC` rendering

Important clarification from `.OVR` data-block evidence:

- the `0x4FEE+` region is best treated as an **overlay DGROUP convention** (same
  addresses reused across overlays), not a single persistent global buffer with
  fixed contents
- e.g.:
  - `WINIT.OVR` data block at `0x4FEE` contains the large filename/path table
  - `WMAZE.OVR` data block at `0x4FEE` contains a much smaller maze-specific init
    block (`SAVEGAME.DBS`, `SOUND00.SND`, etc.) plus BSS tail
- for renderer parity, this means we should seed runtime state from the **current
  overlay’s** data block (and model overlay transitions) rather than assuming
  `WINIT` path strings remain resident after `WMAZE` is loaded

### WROOT startup overlay dispatch sequence (`0x36DC`) recovered (new extractor)

New artifact:

- `scratch/extract_wroot_overlay_startup_dispatch.py`
  - output `scratch/wroot_overlay_startup_dispatch.json`

Using the decoded `0x36DC/0x36E9` loader path and DGROUP mapping in `WROOT.EXE`,
the startup overlay dispatch sequence is recovered directly from WROOT code.

Contiguous base-name table (`DGROUP:0x05F4..0x0630`, suffix `.ovr` at `0x0636`):

- `WINIT`, `WBASE`, `WMAZE`, `WMELE`, `WPOPS`, `WMEXE`, `WTREA`,
  `WPCMK`, `WPCVW`, `WMNPC`, `WDOPT`

Startup `0x36DC` call sequence (`WROOT:0x132D..0x1458`, 11 calls):

- `WINIT.ovr`
- `WBASE.ovr`
- `WMAZE.ovr`
- `WMELE.ovr`
- `WPOPS.ovr`
- `WMEXE.ovr`
- `WTREA.ovr`
- `WPCMK.ovr`
- `WPCVW.ovr`
- `WMNPC.ovr`
- `WDOPT.ovr`

This matters for the renderer work because it clarifies overlay load ordering and
supports the corrected model that the same DGROUP addresses (e.g. `0x4FEE+`) are
reused and overwritten as overlays are loaded.

### WMAZE render-related DGROUP addresses at overlay load (new extractor)

New artifact:

- `scratch/extract_wmaze_render_dgroup_init_state.py`
  - output `scratch/wmaze_render_dgroup_init_state.json`

This extractor builds the exact `WMAZE.OVR` runtime DGROUP init region from the
stored data block plus zero-filled BSS tail and inspects render-relevant addresses.

Confirmed at overlay load (`WMAZE.OVR` DGROUP init):

- render-state bytes/words used by current pass emulation start at zero:
  - `0x5066`, `0x5067`, `0x5068`
  - `0x5072`, `0x507A`, `0x5082`, `0x508A`, `0x5092`, `0x509A`, `0x50A2`
  - `0x50CE`, `0x50D0`
  - `0x521E`, `0x5220`, `0x5222`, `0x5224`, `0x5226`, `0x5228`
- these addresses are in the zero-filled BSS tail, not in stored overlay data

Practical implication:

- the prototype’s current initial-zero assumptions for these render-state
  addresses remain consistent with real overlay-load state
- remaining parity gaps are from later WMAZE/EGA runtime initialization and
  helper behavior, not from incorrect nonzero DGROUP seeds at overlay load

### `EGA.DRV:0x1D94` / `0x220C` `3670` semantics tightened (new extractor)

New artifact:

- `scratch/extract_ega_drv_1d94_220c_semantics.py`
  - output `scratch/ega_drv_1d94_220c_semantics.json`

This consolidates the disassembly-driven semantics for the deferred queue draw path:

- `WROOT:0x3670` -> `EGA.DRV export 0x012B` -> `EGA.DRV:0x1D94`
- `0x1D94` uses an **8-arg wrapper signature**, but driver `bp+offset` decoding is
  shifted by:
  - WROOT wrapper saved `BP`
  - WROOT far-call return (`IP:CS`)
  - EGA export stub near-call return

Confirmed mapping inside `EGA.DRV:0x1D94`:

- `[bp+0x0C]` = `type`
- `[bp+0x0E]` = `x`
- `[bp+0x10]` = `y`
- `[bp+0x12]` = `clip_left`
- `[bp+0x14]` = `clip_right`
- `[bp+0x16]` = `flags1`
- `[bp+0x18]` = `flags2`
- `[bp+0x1A]` = `&attr`

Flag semantics now much tighter:

- `flags1 bit0` = horizontal mirror (bit-reversal transform over scratch buffer via
  xlat table at `cs:0x192`)
- `flags1 bit1` = vertical flip (row-group swaps / offset changes in scratch decode path)
- `flags2 bit0` = hardware EGA write path (sequencer/graphics register programming +
  latch writes to `A000`) vs plain memory-buffer write path

`0x220C` (called by `0x1D94`) is the attr-command decoder/compositor:

- consumes one attr-stream command byte (`cmd`)
- indexes a 0x18-byte descriptor (`(cmd-1)*0x18`)
- composites record data into the 0x1400-byte scratch buffer (`cs:[0x16D]`)
- uses a descriptor bitmask region (starting at `+4`) as tile/cell occupancy
- honors the same transform flags (`flags1`) through traversal/offset setup

Working descriptor-layout hypothesis (0x18 bytes) remains:

- `+0x00` word: source offset in resource chunk
- `+0x02` byte: width (used on frame-header descriptor in `0x1D94`)
- `+0x03` byte: height (used on frame-header descriptor in `0x1D94`)
- `+0x04..+0x17`: occupancy bitmask / presence map used by `0x220C`

### Direct WMAZE `0x3670` call templates extracted (new extractor)

New artifact:

- `scratch/extract_wmaze_direct_3670_call_templates.py`
  - output `scratch/wmaze_direct_3670_call_templates.json`

This captures the two direct WMAZE `0x3670` callsites with arg-order templates:

- `WMAZE:0x98AB` (queue consumer non-`0xFF` phase)
  - call shape matches queue entries exactly:
    - `type = byte[entry+8]`
    - `x = word[entry+0]`
    - `y = word[entry+2]`
    - `clip_left = word[entry+4]`
    - `clip_right = word[entry+6]`
    - `flags1 = 0`
    - `flags2 = 0`
    - `attr_ptr = &local_attr` (loaded from `byte[entry+9]`)
- `WMAZE:0xB4D3` (direct projection-table path)
  - manually corrected template confirms:
    - `flags1 = 0`
    - `flags2 = 0`
    - `attr_ptr = &local_attr`
    - `x` is final x after x-adjust + loop offset math
    - `y` comes from the `0x3717` y projection table adjustment path
    - `clip_left`/`clip_right` are base bounds before x-adjust composition

Practical impact:

- queue-event `3670` calls are now tied directly to the driver’s exact arg/flag
  semantics, reducing ambiguity when implementing deferred pixel rendering in the prototype

### `EGA.DRV:0x0B93` (`36AC`) semantics tightened (new extractor)

New artifact:

- `scratch/extract_ega_drv_0b93_semantics.py`
  - output `scratch/ega_drv_0b93_semantics.json`

This consolidates the static RE for `WROOT:0x36AC` -> `EGA.DRV:0x0B93`.

Like `0x1D94`, wrapper args are shifted in the driver stack frame. `0x0B93` only
reads three wrapper args:

- `[bp+0x0C]` = `arg1_desc`
- `[bp+0x0E]` = `arg2_mode_or_attr`
- `[bp+0x10]` = `arg3_desc_or_minus1`

Branch split (driver):

- `arg3 == 0xFFFF` (entry `0x0BA9`)
  - single-descriptor path
  - arg2 controls merge mode (`cmp [bp+0x0E],0`):
    - nonzero => OR-composite
    - zero => direct copy
- `arg3 != 0xFFFF` (entry `0x0CC6`)
  - two-descriptor translated/combined path
  - still uses arg2 as the same merge-mode selector (`0` vs nonzero)

This matches the long-standing `36AC(desc1, attr_or_mode, desc2_or_-1)` model and
tightens the meaning of the middle argument:

- arg2 is not just a raw attr byte; in driver behavior it is acting as a
  merge-mode selector (`0` vs nonzero), while WMAZE commonly passes the queue/helper
  attr byte in that slot

### WMAZE queue `type==0xFF` (`36AC`) subpass arg patterns confirmed (new extractor)

New artifact:

- `scratch/extract_wmaze_direct_36ac_call_templates.py`
  - output `scratch/wmaze_direct_36ac_call_templates.json`

The queue consumer `0xFF` subpass in `WMAZE:0x9761..0x98C5` uses four `0x36AC`
calls (`0x97E0`, `0x97F7`, `0x982E`, `0x9846`) covering two paired draws:

- first pair uses queue words `w0` / `w4`
- second pair uses queue words `w2` / `w6`
- middle arg is always `byte[entry+9]` (queue attr)

Observed pattern around each pair (with `0x521C` branch affecting descriptor choice):

- translated/paired form:
  - `36AC(desc_a_or_minus1, attr, desc_b_or_fallback)`
- fallback/single form:
  - `36AC(desc_a, attr, 0xFFFF)`

In the queue consumer code:

- first pair:
  - descriptors sourced from `word[entry+0]` and `word[entry+4]`
- second pair:
  - descriptors sourced from `word[entry+2]` and `word[entry+6]`
- attr:
  - `byte[entry+9]`

This ties the queue `0xFF` subpass directly to `EGA.DRV:0x0B93`’s 3-arg branch
semantics and gives a much tighter basis for emulating deferred `36AC` rendering.

### `MAZEDATA.EGA` descriptor header parsing and `0x0731` table patch emulation (new parser)

New artifact:

- `scratch/parse_mazedata_ega_descriptor_tables.py`
  - output `scratch/mazedata_ega_descriptor_tables.json`

This parser emulates the core descriptor-table patch loop in `EGA.DRV:0x0731` using
the real `MAZEDATA.EGA` file and the static driver table at `EGA.DRV cs:0x18E`.

Important decoded structure (high confidence):

- `MAZEDATA.EGA` begins with a `0x800`-byte descriptor header (loaded by `0x0731`)
- header words:
  - `word0 = 0x0099` (`153`) => descriptor record count
  - `word1 = 0x016E` => packed adjustment input used by `0x0731`
- runtime `cs:0x190` header-table pointer is computed as:
  - `count * 5 + 4 = 0x0301`

The parser now exports three aligned 5-byte tables:

- `MAZEDATA.header_table_at_0x190` (header-owned table referenced via runtime `cs:0x190`)
- `EGA.DRV.static_table_at_0x18E` (pre-patch static driver table)
- `EGA.DRV.runtime_patched_table_at_0x18E` (after `0x0731` patch emulation)

This is directly relevant to `EGA.DRV:0x0B93` (`36AC`), which uses both runtime tables:

- one table via `cs:0x190` (header-derived)
- one table via `cs:0x18E` (driver static table patched by `0x0731`)

Useful concrete values from `MAZEDATA.EGA`:

- header count = `153`
- header table at `0x0301` contains many structured 5-byte records, e.g.:
  - `00 0d 28 00 0e`
  - `01 10 34 00 08`
  - `02 12 3c 00 04`
- these align with the 5-byte record usage pattern observed in `0x0B93`

Still unresolved (but now isolated):

- `0x0731`’s tail-size formula (derived from the final header 5-byte record) does not
  equal the full file remainder for `MAZEDATA.EGA`
- this implies additional structure/chunking beyond the currently decoded formula,
  which still needs to be recovered before exact file-to-resource reconstruction is complete

Practical impact:

- we can now reconstruct the runtime descriptor tables required by `36AC` from
  real `MAZEDATA.EGA` + `EGA.DRV`, instead of treating `cs:0x18E` / `cs:0x190`
  as opaque state

### First software `36AC` decoder pass (debug queue integration)

New artifact:

- `scratch/ega_36ac_emu.py`

What it does (current scope):

- emulates the `EGA.DRV:0x0B93` single-descriptor (`arg3 == 0xFFFF`) copy/OR path
  into a software planar `320x200` buffer using:
  - runtime-patched `cs:0x18E` table (reconstructed from `MAZEDATA.EGA` + `EGA.DRV`)
  - header `cs:0x190` table (`MAZEDATA.EGA` header)
- emulates the translated/two-descriptor branch (`arg3 != 0xFFFF`) using the
  decoded `0x0CC6..0x0E27` logic:
  - arg1 supplies source descriptor-table entry
  - arg3 supplies placement/repeat header
  - source bytes are read right-to-left with bit-reversal (`XLAT` table at `0x192`)
- exposes a helper to replay estimated queue `0x36AC` events:
  - `render_estimated_queue_36ac_events(...)`

Prototype integration (debug-only):

- `scratch/render_map_3d_owner_prototype.py` now calls the helper during debug export
  after queue-trace reconstruction and writes:
  - `wmaze_84f1_queue_36ac_estimated` (metadata/trace)
  - optional sibling image `*.queue36ac.png` when `0x36AC` events exist

Current limitation (important):

- this decoder still does not reproduce real deferred queue output reliably because
  the runtime resource/chunk state behind `0x3664` loader calls is not fully
  reconstructed yet
- in other words: the `0x0B93` copy logic is now partially emulated, but the source
  byte-address space it expects is still incomplete

Practical value right now:

- we can test `36AC` descriptor/address hypotheses against real driver table math
- queue `type==0xFF` events now produce structured per-call decode traces (and debug
  images when source bytes resolve), which is a better RE loop than trace-only events

### Critical correction: `0x18E` / `0x190` are header-table pointers, not inline EGA.DRV tables

This corrects an important misread in the earlier parser/decoder work.

`EGA.DRV:0x0731` / `0x0B93` semantics show:

- `cs:[0x18E]` and `cs:[0x190]` are **word pointers** (offsets) into the
  MAZEDATA descriptor header buffer (`DS = cs:[0x149]`), not inline 5-byte table
  bytes stored in the `EGA.DRV` image.

Concrete static driver values:

- `EGA.DRV cs:[0x18E] = 0x0004`
- `EGA.DRV cs:[0x190] = 0x0000` (later set by `0x0731` to `count*5+4`)

Implications:

- the first 5-byte table lives in `MAZEDATA.EGA` header at offset `0x0004`
- `0x0731` patches that header table in place (using header word1 nibble/segment math)
- the second 5-byte table lives in the same header at runtime offset:
  - `count*5 + 4 = 0x0301` for `MAZEDATA.EGA`

Artifacts updated/added:

- `scratch/parse_mazedata_ega_descriptor_tables.py` (corrected)
- `scratch/mazedata_ega_descriptor_tables.json` (regenerated with corrected semantics)
- `scratch/ega_36ac_emu.py` (corrected `36AC` table + source-address model)
- `scratch/analyze_36ac_unresolved_descriptor_sources.py`
- `scratch/ega_36ac_unresolved_descriptor_sources.json`

Practical impact (major):

With the corrected pointer model, plus a later fix for `0x0B93` 16-bit source
offset wrap semantics (`SI` wraps within a fixed `DS` segment), the software
`36AC` single-descriptor path now classifies all `153` descriptors as:

- `129` real draws
- `24` `repeat_rows_zero` no-ops
- `0` unresolved source-window failures

This is a major reduction from the earlier (incorrect-model) `123` out-of-range
results and strongly confirms the `0x18E/0x190` pointer interpretation.

Important nuance:

- the temporary "out-of-range" failures for descriptors `0`, `6`, `9` were
  resolved after modeling `0x0B93` source addressing as 16-bit offset wrap
  within `DS`, rather than a naive linear span check.
- one additional descriptor (`152`) was resolved by relaxing the source-segment
  mapper to allow partial file-backed windows (the draw only needs the accessed
  bytes, not a full 64K contiguous file region).

Updated artifact:

- `scratch/ega_36ac_unresolved_descriptor_sources.json`
  - now reports `129 draw`, `24 repeat_rows_zero`, `0 unresolved_source_window`

Current blocker has shifted:

- the remaining `36AC` gap is now primarily the exact
  interaction details in edge cases (if any) and integration into the real WMAZE
  deferred queue viewport path, not single-descriptor source-table reconstruction.

### Deferred queue `0x3670` debug replay scaffold (next blocker isolation)

After validating the exact `36AC` two-descriptor branch on a real queue-heavy view,
the next practical blocker is `0x3670` (`EGA.DRV:0x1D94`) for non-`0xFF` queue
entries.

New artifacts/scripts:

- `scratch/ega_3670_emu.py`
  - emits a `320x200` debug marker layer for estimated queue `0x3670` events
  - classifies scalar vs symbolic arguments from `likely_3670_semantics`
  - not pixel-accurate yet (markers only)
- `scratch/analyze_queue_3670_symbolics.py`
  - aggregates symbolic `0x3670` queue fields by expression and `0x84F1` callsite

Prototype integration:

- `scratch/render_map_3d_owner_prototype.py` now embeds:
  - `wmaze_84f1_queue_3670_estimated`
  - optional `*.queue3670.png` sibling image (debug marker layer)

Real-scene validation (queue-heavy translated-`36AC` view):

- `map11 (132,143,E)` now confirms:
  - `36` deferred queue `0x36AC` events
  - `16` exact two-descriptor (`arg3 != 0xFFFF`) `36AC` events
  - `18` deferred queue `0x3670` events

Current `0x3670` unresolved bottleneck (now isolated cleanly):

- all symbolic fields in the tested heavy scene reduce to just two forms:
  - `x : word ptr [bx + 0x52]`
  - `attr : word ptr [0x363e]`
- callsite aggregation (`scratch/queue_3670_symbolics_map11_132_143_E.json`) shows:
  - `0x873D`, `0x87DB` -> symbolic `x` via `[bx+0x52]`
  - `0x869A` -> symbolic `attr` via `[0x363e]`

This sharply narrows the next reverse-engineering target for accurate `0x3670`
queue replay: resolve those two producer-side symbols in `0x85D0` / `0x84F1`
reconstruction before implementing the full `EGA.DRV:0x1D94` pixel path.

### `0x3670` queue trace recovery update: symbolic fields removed, low-table init still unresolved

Follow-up work tightened the `0x84F1` queue reconstruction for the three dominant
`0x85D0` producer callsites:

- `0x869A`
  - now recovered as `word ptr [0x363E] + 0x0F` (using static WROOT image fallback)
- `0x873D`, `0x87DB`
  - now recovered as `word ptr [0x52 + (6*bp4 + 2*bp8)]`
  - `bp4 = depth_index`, `bp8 = pass immediate [bp+8]`
  - source bytes currently come from a **static WROOT image fallback**

Implementation / artifacts:

- `scratch/simulate_wmaze_84f1_queue_trace.py`
  - callsite-specific recovery for `0x869A` / `0x873D` / `0x87DB`
  - queue entries now include `recovered_callsite_exprs` annotations (with provenance)
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670resolve2.json`
  - validation frame after recovery patch

Practical result on the same queue-heavy scene (`map11 (132,143,E)`):

- `0x3670` events are now fully scalar in the debug replay metadata:
  - `events_total_3670 = 18`
  - `events_resolved_scalar = 18`
  - `unresolved_breakdown = {}`
- but `12/18` resolved `x` anchors are out of viewport (`events_marker_x_out_of_view = 12`)

Interpretation:

- the symbolic reconstruction problem is solved for those callsites
- but the `word ptr [0x52 + ...]` table values are still not trustworthy enough for
  final rendering parity when read from the static WROOT image
- the remaining gap is now specifically the runtime initialization/source of the low
  projection tables (`0x22/0x2A/0x32/0x34/0x52`) used by WMAZE direct/queued `0x3670`
  setup

### `WROOT 0x3694` is not the low projection-table source

`WMAZE:0x903B` calls `WROOT:0x3694` before some direct `0x3670` usage, so this was a
strong candidate for projection-table setup. That hypothesis is now ruled out.

New artifact:

- `scratch/extract_ega_drv_0835_semantics.py`
- `scratch/ega_drv_0835_semantics.json`

Confirmed mapping:

- `WROOT:0x3694 -> EGA.DRV export 0x0137 -> EGA.DRV:0x0835`

`EGA.DRV:0x0835` semantics (high confidence):

- fills a rectangle in the driver scratch buffer (`cs:[0x14D]`) across all 4 EGA planes
- takes a 4-byte rectangle descriptor + fill byte
- this is a clear/fill helper, not the `0x22/0x2A/0x32/0x34/0x52` projection-table generator

This means the next `0x3670` parity target remains unchanged:

- recover the runtime source/init path for WMAZE low projection tables, then replace
  the static WROOT-image fallback in queue `x` recovery and direct `0x3670` modeling.

### WROOT low-offset table correction: use DGROUP (`SS=e_ss`), not code bytes

A major modeling error in the provisional `0x3670` queue recovery was corrected:
the low-offset projection helpers (`DS:[0x22..0x52]`) are not read from WROOT code
image bytes near offset `0x0000`.

WROOT startup (`0x4072`) shows:

- `mov bp, 0x0FD8` (from EXE header `e_ss`)
- later `mov ss, bp`
- WROOT uses this segment as shared DGROUP/stack

So `DS:[0x22..0x52]` should be interpreted relative to **WROOT DGROUP**, whose
static initialized bytes live at:

- file image offset `e_ss * 16 = 0xFD80`

New artifact:

- `scratch/extract_wroot_dgroup_low_projection_tables.py`
- `scratch/wroot_dgroup_low_projection_tables.json`

This extractor dumps the static DGROUP words for:

- `0x22`, `0x2A`, `0x32`, `0x34`, `0x52`

Practical impact on queue `0x3670` reconstruction:

- switching `0x873D/0x87DB` recovery from WROOT code bytes to WROOT DGROUP static
  words turned nonsense x anchors (e.g. `1220`) into plausible values (e.g. `-32`,
  `64`, `0` before final projection adjustments).
- heavy test scene (`map11 (132,143,E)`) still has some off-screen x anchors, but
  the result is materially closer and supports the DGROUP-table model.

### `0x363E` state machine found in WMAZE (controls `0x869A` attr path)

Cross-module scans showed `0x363E` is written in `WMAZE.OVR`, not just read by the
render helper path.

Confirmed WMAZE refs:

- init/reset:
  - `4DF9: mov word ptr [0x363E], 0`
- temporary render-state changes:
  - `59C1: mov word ptr [0x363E], 1`
  - `59DA: mov word ptr [0x363E], 2`
  - `59EB: mov word ptr [0x363E], 0`

These writes occur around calls to `0x98CB` (render path), which explains the
`0x85D0` / `0x84F1` `0x869A` producer pattern:

- `attr = word ptr [0x363E] + 0x0F`

Prototype queue recovery now uses:

- WROOT DGROUP read for `0x363E` when available
- fallback to initialized WMAZE base-view state `0` (because `0x363E` is BSS/runtime
  state beyond static WROOT initialized bytes)

Result on the queue-heavy test scene (`map11 (132,143,E)`, base-view context):

- `0x3670` deferred events fully scalar again (`18/18`)
- `0x869A` attr resolves to `15` under the base-state fallback (`0x363E = 0`)
## Deferred Queue `0x3670` Software Replay (First Real Pixel Path)

Implemented a first software replay path for deferred queue `0x3670` events in `scratch/ega_3670_emu.py` and wired it through the prototype debug export.

What now works:
- Queue `0x3670` events (`type != 0xFF`) are no longer marker-only when the event is in the common queue-consumer form:
  - `flags1 = 0`
  - `flags2 = 0`
  - single-byte attr stream (`&attr_local`, then implicit `0` terminator)
- The replay emulates a constrained subset of `EGA.DRV:0x1D94/0x220C`:
  - resource record decode (`0x220C`) into a software scratch tile buffer
  - occupancy-mask-driven tile composition
  - queue-event sprite placement in pixel space with clip bounds
- Marker overlay is retained for visibility/debugging.

Current type-chunk source (still heuristic):
- `ega_3670_emu.py` now brute-force scans `MAZEDATA.EGA` for `0x1D25`-style RLE streams and scores candidates using:
  - descriptor plausibility for the observed attrs
  - actual queue-event replay pixel output (strongest signal)

Validated scene:
- `map11 (132,143,E)` queue-heavy test
- Embedded prototype queue `3670` debug metadata now reports:
  - `events_total_3670 = 18`
  - `events_resolved_scalar = 18`
  - `events_real_replayed = 18`
  - `real_pixels_drawn = 1232`

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670real3.meta.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670real3.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670real_embed1.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670real_embed1.queue3670.png`

Important limitation:
- The `0x3670` real replay currently relies on heuristic type-chunk recovery from raw `MAZEDATA.EGA` RLE streams.
- This is a useful bridge, but exact parity still requires recovering the runtime `0x3664` / `EGA.DRV:0x1D25` chunk-load state and the true per-type seek offsets (`0x36E2/0x36E4` metadata path).
## `0x36DE + type*0x13A` Metadata Block Load Path (Recovered)

New extractors:
- `scratch/extract_wroot_0882_semantics.py`
- `scratch/extract_winit_4721_type_metadata_loader.py`
- `scratch/extract_wroot_0882_table_accesses.py`

Artifacts:
- `scratch/wroot_0882_semantics.json`
- `scratch/winit_4721_type_metadata_loader.json`
- `scratch/wroot_0882_table_accesses.json`

Key result:
- `WINIT:0x4721` is a direct bridge into the missing graphics metadata path:
  - calls `WROOT:0x0882` with:
    - `opcode = 8`
    - `dest = 0x36DE + 0x13A*type`
    - `record_index = helper arg`
    - `mode = 0`
- This is the loader for the per-type WROOT shared metadata block that later feeds:
  - `0x36E2/0x36E4` (`WROOT:0x3664` call pattern)
  - `0x3717` / `0x36E4` projection adjustments used by WMAZE (`0x84F1`, direct `0x3670`)
  - `0x3812` per-type count bytes

`WROOT:0x0882` semantics (now high confidence):
- Signature inferred: `0882(opcode, dest_ptr, record_index, mode)`
- Uses shared runtime tables in WROOT DGROUP:
  - `0x3048` dword base-offset table
  - `0x3300` record-size table
  - `0x3338` direct-vs-temp read flag table
- Seeks on file handle `[0x842]` via `0x4321`, then reads/copies a record to `dest_ptr`

Important blocker clarified:
- `0x3048/0x3300/0x3338` are runtime shared-DGROUP tables (not recoverable from static WROOT EXE code image at those offsets).
- Current literal-reference scan (`wroot_0882_table_accesses.json`) only confirms `0x0882` reads them; initializer path is still unresolved.

Why this matters to rendering:
- This is the missing provenance for exact `0x36E4/0x3717` values, which are still not applied in queue `0x3670` reconstruction.
- Recovering the `0x0882` table initializer and record source will let us populate the real `0x36DE + type*0x13A` block and remove a major remaining source of queue-placement error.
## WINIT Bootstrap of `0x0882` Runtime Tables (`MASTER.HDR` / `DISK.HDR`)

New findings (WINIT `0x4D09..0x4D8E`):
- `WINIT` explicitly loads shared WROOT runtime table regions from files before using `0x0882` heavily:
  - `MASTER.HDR` (`0x50F5`) -> `0x3300`, size `0x42`
  - `DISK.HDR` (`0x5100`) -> `0x3044`, size `0x2BC`
  - `MSG.HDR` (`0x5109`) -> `0x0848`, size `0x13EE`
- This explains the previously “missing” `0x0882` runtime tables (`0x3048/0x3300/0x3338`): they are file-backed runtime state, not static WROOT image data.

Helper confirmations:
- `WINIT:0x469F` = open path + read exact bytes into destination buffer + close
- `WINIT:0x46E4` = open path + helper-process (`0x2985`) + close
- `WINIT:0x4DBD` opens `SCENARIO.DBS` into shared handle `[0x842]`
- `WINIT:0x4DD7` calls `0x47F5(0x0E)`, and `0x47F5` uses `WROOT:0x0882(opcode=9)` to populate `0x3344 + 0x0C*index`

New artifact:
- `scratch/extract_wroot_0882_bootstrap_tables_from_headers.py`
- Output: `scratch/wroot_0882_bootstrap_tables_from_headers.json`

This reconstructs from real files:
- `0x3300` opcode record sizes (from `MASTER.HDR`)
- `0x3338` opcode flags (from `MASTER.HDR`)
- `0x3048` opcode base offsets (from `DISK.HDR` + 4-byte load offset)

Critical values now confirmed:
- `opcode 8`:
  - size = `0x13A`
  - flag = `0x00` (direct read path in `0x0882`)
  - role = per-type metadata records (`0x36DE + type*0x13A`)
- `opcode 9`:
  - size = `0x0C`
  - flag = `0x00` (direct read path)
  - role = `WINIT:0x47F5` records (`0x3344 + 0x0C*index`)

## Queue `0x84F1` x/y Adjustments via `0x0882` Bootstrap (Applied)

`scratch/simulate_wmaze_84f1_queue_trace.py` now reconstructs `0x84F1` x/y adjustment bytes using:
- `MASTER.HDR` (`0x3300` / `0x3338`)
- `DISK.HDR` (`0x3048`)
- `SCENARIO.DBS` (`0x0882 opcode=8` records, size `0x13A`)

Applied adjustments:
- x adjust (`0x36E4 + type*0x13A + 2*attr`) as **byte** (corrected width)
- y adjust (`0x3717 + type*0x13A + attr`) as byte

Result on queue-heavy scene `map11 (132,143,E)`:
- Before bootstrap-applied adjustments (metadata unresolved / heuristic): queue `0x3670` anchors were partially off-screen.
- After applying `0x0882` bootstrap-derived metadata:
  - `events_marker_x_out_of_view`: `8 -> 0`
  - deferred `0x3670` software replay pixels: `1232 -> 3664`

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670_0882boot2_embed.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670_0882boot2_embed.queue3670.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670_0882boot2_embed.png`

Important caveat:
- The current `0x84F1` adjustment reconstruction uses `SCENARIO.DBS` opcode-8 records via the WINIT bootstrap path.
- This is a major step forward and clearly improves queue placement, but exact maze-render parity still requires confirming whether the runtime `0x36DE` metadata block in the maze view is sourced from the same `opcode 8 / SCENARIO.DBS` records or later overwritten by a maze-specific path.

## WROOT `0x33E9` Chunk Loader (Decoded) and WMAZE `0x9948` Reclassification

New artifacts:
- `scratch/extract_wroot_33e9_loader_semantics.py`
- `scratch/wroot_33e9_loader_semantics.json`
- `scratch/wroot_33e9_3556_disasm.txt`
- `scratch/extract_game_module_33e9_calls.py`
- `scratch/game_module_33e9_calls.json`

`WROOT:0x33E9` is now decoded as a generic chunk loader/decompressor into a runtime slot table at `cs:0x3579 + 4*slot`:
- caller selects slot with `arg6` (`[bp+0x0E]`)
- seeks file handle via DOS `AH=42h` using `arg2/arg3` (`[bp+6]/[bp+8]`)
- loads raw or tree-coded chunk data
- stores allocated segment + decoded size in the slot entry
- frees prior slot contents through helper `0x3556`

Important correction:
- The previously targeted `WMAZE:0x9948..0x9A23 -> WROOT:0x33E9` path is **not** the missing maze graphics chunk loader path.
- `WMAZE:0x9948` builds/open `SOUND00.SND` (template at WMAZE DGROUP `0x4FFC`) and calls `0x33E9` with slot `0x0E`.
- This is a sound/resource chunk path, not the deferred maze `0x3670` graphics chunk source.

Cross-module `0x33E9` call scan (`scratch/game_module_33e9_calls.json`) found direct calls in:
- `WINIT.OVR`
- `WMAZE.OVR`
- `WMELE.OVR`
- `WMNPC.OVR`
- `WDOPT.OVR`

Observed caller pattern (most callsites):
- path build (`0x0CD6`) + open (`0x3E88`)
- size words from `0x33F0/0x33F2` (often populated via `0x0882 opcode=9`)
- `call 0x33E9`

`WINIT` clarification:
- `WINIT:0x47F5` loops `0x0882(opcode=9)` records into `0x3344 + 0x0C*index` and calls `0x33E9`
- `WINIT:0x48EE` (the same structure WMAZE later mirrors) also calls `0x33E9`
- `WINIT` templates at `0x4FF8` / `0x5004` show `SOUND00.SND`, confirming this branch is part of the sound chunk-loading/caching setup

Implication for 3D renderer parity:
- `0x33E9` RE is still valuable (generic chunk format + slot behavior are now known), but it does **not** resolve the remaining deferred `0x3670` graphics chunk-source problem.
- The next graphics-targeted loader work should stay on the `0x3664` / `EGA.DRV:0x1D25` path and the runtime metadata words (`0x36E2/0x36E4`) that drive it.

## WINIT `0x4721` Batch Recipe for Graphics `0x3664` Loads (new)

New artifact:
- `scratch/extract_winit_4721_call_map.py`
- output: `scratch/winit_4721_call_map.json`

`WINIT:0x4721` is the decoded bridge function that:
- loads per-type metadata via `WROOT:0x0882(opcode=8)` into `0x36DE + type*0x13A`
- opens a file
- calls `WROOT:0x3664` with:
  - `type` (`[bp+6]`)
  - `word [type*0x13A + 0x36E4]`
  - `word [type*0x13A + 0x36E2]`
  - file handle (`[0x4FE8]`)

Recovered `WINIT` batch caller (`0x54A7..0x5526`) invokes `0x4721` seven times with this mapping:

- `type 0 -> record_index 3`
- `type 1 -> record_index 1`
- `type 2 -> record_index 2`
- `type 3 -> record_index 7`
- `type 7 -> record_index 4`
- `type 8 -> record_index 5`
- `type 9 -> record_index 6`

Notes:
- `record_index` is `0x4721 [bp+4]` and is used both for `0x0882(opcode=8)` record selection and filename-digit insertion before opening the file.
- `type` is `0x4721 [bp+6]` and drives the metadata destination + `0x3664` type argument.
- This is the strongest concrete runtime recipe so far for how WINIT stages graphics chunks before the maze renderer runs.

Why this matters:
- It reduces the remaining graphics-loader problem from a generic `0x3664` mystery to a specific staged load sequence with known `(record_index, type)` pairs.
- Next step is to identify the exact file produced by the `0x4721` path-build/open sequence (it uses local copy seeded from `WINIT` DGROUP `0x4FEE`) and confirm how those seven loads correspond to the chunk sources later used by `0x3670`.

### `WINIT:0x4721` file template correction (`0x4FEE` is `MON00.PIC`, not `SAVEGAME.DBS`)

Important correction:
- the earlier confusion about `0x4FEE` came from mixing `WMAZE.OVR` and `WINIT.OVR` DGROUP data blocks.
- In `WINIT.OVR`, DGROUP `0x4FEE` starts with:
  - `MON00.PIC`
- In `WMAZE.OVR`, DGROUP `0x4FEE` starts with:
  - `SAVEGAME.DBS`

This resolves the `0x4721` filename-digit rewrite puzzle:
- `0x4721` copies the string at `WINIT:0x4FEE` to a local buffer
- writes two digits at offsets `+3/+4`
- resulting filenames are valid:
  - `MON03.PIC`, `MON01.PIC`, `MON02.PIC`, `MON07.PIC`, ...

So no hidden runtime overwrite of `WINIT:0x4FEE` is needed for the `0x4721` path.

## Deferred `0x3670` Replay: Runtime-Informed Multisource Chunk Candidates (new)

Updated script:
- `scratch/ega_3670_emu.py`

New helper source:
- `scratch/winit_4721_call_map.json` (`type -> MONxx record_index`)

Change:
- `ega_3670_emu.py` no longer scans only `MAZEDATA.EGA` for `0x1D25`-style RLE chunk candidates.
- It now compares candidates across:
  - `MAZEDATA.EGA` (baseline heuristic source)
  - `MONxx.PIC` for driver `type`s covered by the recovered `WINIT:0x4721` mapping

Scoring update:
- replay probe now uses up to 24 real queue events (instead of 12) and weights replay output more heavily, reducing short-sample overfitting.

Validation (standalone replay on queue-heavy scene `map11 (132,143,E)`):
- input debug JSON:
  - `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queue3670_0882boot2_embed.json`
- output:
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_multisource_v2.meta.json`
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_multisource_v2.png`

Observed result:
- type-2 chunk source selected: `MON02.PIC`
- selected candidate offset: `0x4FA`
- deferred `0x3670` replay pixels: `4820` (standalone replay pass)

Interpretation:
- This is still a heuristic replay path, but it is now guided by a real runtime loader recipe (`WINIT:0x4721 -> 0x3664`) rather than a single-file brute-force search.
- It materially strengthens the bridge between disassembly findings and the software `0x3670` renderer.

Remaining caveat:
- We still have not fully modeled `EGA.DRV:0x1D25` argument usage and runtime chunk state for all modes/branches.
- `MONxx.PIC` winning on one queue-heavy scene does not yet prove it is the universal source for all WMAZE deferred `0x3670` types.

## WBASE `0x4BB2` Confirms a MONxx -> `0x3664` -> `0x3670` Bridge (new)

New artifact:
- `scratch/extract_wbase_4bb2_mon_loader_bridge.py`
- output: `scratch/wbase_4bb2_mon_loader_bridge.json`

`WBASE:0x4BB2` is a clear clone of the `WINIT:0x4721` graphics helper pattern:
- `0x0882(opcode=8)` loads `0x13A` metadata into `0x36DE + type*0x13A`
- template copy + digit rewrite + path build/open
- `0x3664` call with:
  - `type`
  - metadata words `0x36E2/0x36E4`
  - file handle in `[0x4FE8]`
- count-driven initialization using metadata byte `0x3812`

Important WBASE template/source strings:
- `0x4FF9` = `MON00.PIC` (used by `0x4BB2`)
- nearby overlay strings:
  - `0x5003` = `WPORT1.EGA`
  - `0x500E` = `WPORT1.CGA`

This matters because:
- `0x4BB2` is immediately followed by direct WROOT `0x3670` callers in WBASE (e.g. `0x4CD1`, `0x4D11`).
- It is direct evidence that non-maze `0x3670` rendering can consume resources loaded from `MONxx.PIC` via the same metadata/`0x3664` path.

Implication for the maze queue `0x3670` source question:
- The `MONxx.PIC` multisource candidate path is no longer just a heuristic guess; it now matches a confirmed `0x3664 -> 0x3670` runtime bridge in game code.
- The remaining uncertainty is whether WMAZE queue `type` slots are still using WINIT/WBASE-loaded `MONxx` chunks at the moment of maze rendering, or have been overwritten by another loader path.

## `0x4721`-Like MON Loader Clones Across Overlays (new)

New extractor:
- `scratch/extract_3664_mon_loader_clone_maps.py`
- output: `scratch/mon_loader_clone_call_maps.json`

Detection rule (from direct `0x3664` callsites):
- same `0x13A`-stride metadata pattern (`imul ... 0x13A`)
- pushes `[bx+0x36E4]` / `[bx+0x36E2]`
- helper also calls `WROOT:0x0882`

Recovered helpers so far:
- `WINIT:0x4721` (`MON00.PIC`)
- `WMNPC:0x5508` (`MON00.PIC`)

Recovered caller maps:
- `WINIT:0x4721`
  - `type -> record_index`: `0->3, 1->1, 2->2, 3->7, 7->4, 8->5, 9->6`
- `WMNPC:0x5508`
  - `type -> record_index`: `1->1, 4->4`

This is useful for queue `0x3670` parity because it gives a concrete overwrite path for graphics driver type slots beyond startup (`WINIT`), especially later overlays (`WMNPC`) that may replace the resources used by deferred queue rendering.

## `ega_3670_emu.py` MON Candidate Bug Fix + Clone-Map Integration (new)

Updated scripts:
- `scratch/ega_3670_emu.py`
- `scratch/extract_wbase_4bb2_call_map.py`

Important fix:
- the MON-source candidate replay scoring path in `ega_3670_emu.py` was referencing an undefined local (`sample_events`) inside a broad `try/except`.
- This could silently suppress MON candidate evaluation.
- Fixed by using the per-type probe event list (`type_scalar_sample_events[type]`).

Source-map integration improvements:
- `ega_3670_emu.py` now loads clone mappings from:
  - `scratch/mon_loader_clone_call_maps.json` (preferred)
  - with fallback to `winit_4721` / `wbase_4bb2` call maps
- It ranks helper provenance by actual WROOT startup overlay order using:
  - `scratch/wroot_overlay_startup_dispatch.json`

Validation (same queue-heavy scene `map11 (132,143,E)`):
- output:
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_multisource_clonemap.meta.json`
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_multisource_clonemap.png`
- result:
  - `events_real_replayed = 18`
  - `real_pixels_drawn = 4820`
  - `type_2` selected source remains:
    - `MON02.PIC`
    - `source_helper = WINIT:0x4721`
    - `source_mode = heuristic_rle_scan`

Interpretation:
- The queue `0x3670` replay is now structurally tied to a broader, real overlay-driven type-slot loader set (`WINIT`, `WBASE`, `WMNPC`) instead of a hardcoded WINIT-only assumption.
- The next remaining gap is exact runtime overwrite timing / `0x3664` chunk-state reconstruction, not just source-file enumeration.

## Pre-Maze MON Type Metadata (`0x36E2/0x36E4`) vs `0x3664` Chunk Source (new)

New artifacts:
- `scratch/build_mon_loader_type_chunk_args.py`
- `scratch/mon_loader_type_chunk_args.json`
- `scratch/build_mon_loader_type_slot_timeline.py`
- `scratch/mon_loader_type_slot_timeline.json`
- `scratch/analyze_mon_metadata_36e2_rle_offsets.py`
- `scratch/mon_metadata_36e2_rle_offsets.json`

What this adds:
- Builds a static potential type-slot overwrite timeline from recovered `0x4721`-like MON loader helpers (with WROOT startup overlay order hints).
- Derives likely pre-maze MON sources per type (e.g. type 2 -> `MON02.PIC`, type 4 -> `WBASE` `MON08.PIC` before `WMNPC` post-maze writes).
- Extracts real opcode-8 metadata records (`0x36DE + type*0x13A`) for those sources, including:
  - `0x36E2` / `0x36E4` words passed to `WROOT:0x3664`
  - projection adjustment bytes (`0x36E4 + 2*attr`, `0x3717 + attr`)
  - count byte `0x3812`

Important new constraint (strong):
- For all pre-maze MON-backed types, metadata `0x36E2/0x36E4` values are **not direct MON file offsets**.
- Example:
  - type 2 (pre-maze source `MON02.PIC`) has:
    - `36E2 = 0x230D`
    - `36E4 = 0x0000`
  - but `MON02.PIC` file size is only `8973` bytes (`0x230D` is out of range).
- `scratch/mon_metadata_36e2_rle_offsets.json` confirms this across all covered pre-maze types.

Implication for `0x3664` / `EGA.DRV:0x1D25`:
- The `0x36E2/0x36E4` pair is not a plain file seek into `MONxx.PIC`.
- It likely refers to an offset/state within a decoded/intermediate resource layout (or another runtime address space interpretation), which explains why the direct metadata-seek candidate fails in `scratch/ega_3670_emu.py`.

Follow-up experiment (manual, type 2):
- The current best replay candidate still comes from `MON02.PIC` heuristic RLE scan at `0x4FA`.
- The metadata `36E2=0x230D` falls **inside** both decoded candidate chunks (`MON02 @ 0x0` and `MON02 @ 0x4FA`) and may be a chunk-internal boundary/offset rather than a file position.
- This makes `0x1D25` layout/loader semantics the next concrete RE target, not file-source discovery.

## `EGA.DRV:0x1D25` (`WROOT:0x3664`) Arg Usage Correction + Strict Replay Mode (new)

New artifacts:
- `scratch/extract_ega_drv_1d25_semantics.py`
- `scratch/ega_drv_1d25_semantics.json`
- `scratch/analyze_direct_3664_type_loads.py`
- `scratch/direct_3664_type_loads.json`

Key correction:
- `EGA.DRV:0x1D25` (the EGA target behind `WROOT:0x3664`) reads only:
  - wrapper arg1: file handle
  - wrapper arg2/arg3: seek low/high (`DX:CX`)
  - wrapper arg6: type
- It does **not** read wrapper arg4/arg5 (the overlay metadata words often sourced from `0x36E2/0x36E4`).

Implication:
- On EGA, the common `WINIT/WBASE` helper pattern with `seek_lo=0`, `seek_hi=0` really is the seek used by the driver.
- The metadata `0x36E2/0x36E4` words are therefore not EGA file offsets for `0x1D25`; any effect they have must be outside `EGA.DRV:0x1D25` (or for other drivers).

Renderer bridge update:
- `scratch/ega_3670_emu.py` now supports:
  - `--prefer-exact-1d25-mon-seek0`
- This strict mode prefers disassembly-faithful pre-maze `MONxx.PIC @ seek0` candidates (from the MON loader timeline) over heuristic intra-file RLE rescans.

Validation on queue-heavy scene (`map11 (132,143,E)`):
- heuristic mode (`MON02.PIC` rescan winner at `0x4FA`):
  - `real_pixels_drawn = 4820`
- strict `1D25` mode (`MON02.PIC @ 0x0` forced for type 2):
  - `real_pixels_drawn = 3678`

Interpretation:
- This confirms the current mismatch is not solved by treating `0x36E2/0x36E4` as direct MON file offsets (that model is wrong on EGA).
- It also shows our current heuristic candidate can “look better” than the disassembly-faithful seek0 path, which is a strong signal that the remaining error is in `0x3670`/runtime chunk-state parity, not just source-file selection.

## `3670` Chunk Candidate Scoring Hardening (new)

Updated script:
- `scratch/ega_3670_emu.py`

Problem found:
- The previous heuristic chunk scorer could be fooled by high-pixel-output junk data.
- In the queue-heavy type-2 case (`MON02.PIC @ 0x4FA`), the chosen chunk had obviously suspicious descriptor records:
  - attr1/attr2 descriptor records were duplicate and low-entropy (uniform `0x0D` bytes)
  - yet it still won because the replay-pixel count dominated the score

Fix:
- Added descriptor plausibility penalties and a hard reject for:
  - duplicate low-entropy descriptor records across attrs used in the same queue scene

Validation (same queue-heavy scene, normal mode, no strict flag):
- output:
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_rescore2.meta.json`
  - `scratch/proto_decode_compare/map11_132_143_E_queue3670_rescore2.png`
- result:
  - type-2 source now selected by default:
    - `MON02.PIC`
    - `source_mode = direct_1d25_seek0_from_winit_4721`
    - `best_offset = 0x0`
  - `real_pixels_drawn = 3678`

Interpretation:
- This is a correctness-driven regression in raw pixel count (fewer pixels than the junk heuristic candidate), but it is progress toward faithful behavior:
  - the replay path now rejects a known bogus chunk and defaults to the EGA-disassembly-faithful `1D25` seek0 source for the pre-maze type-2 case.

## Prototype Queue Compositing Integration (new)

Updated script:
- `scratch/render_map_3d_owner_prototype.py`

New CLI flags:
- `--composite-estimated-deferred-queue`
- `--prefer-exact-1d25-mon-seek0` (passed through to `ega_3670_emu`)

What changed:
- The prototype can now composite estimated deferred queue replay layers (`36AC` + `3670`) into the main `320x200` canvas before viewport crop.
- This makes queue-stage RE visible in the actual prototype viewport output, not only in sidecar debug images.

Important integration fix:
- `scratch/ega_3670_emu.py` now supports `overlay_debug_markers=False`.
- The prototype uses marker-free `3670` replay for final canvas compositing, while keeping marker overlays available in debug images/CLI runs.
- This removes debug ticks from the rendered viewport (a real integration bug, not just aesthetics).

Validation artifact:
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite2.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite2.json`

Debug JSON confirms:
- deferred queue compositing executed (`estimated_deferred_queue_composited = true`)
- `3670` replay used the corrected source:
  - `type_2 -> MON02.PIC`, `source_mode = direct_1d25_seek0_from_winit_4721`

Follow-up integration correction:
- The first queue compositing pass layered:
  - all `36AC` events, then all `3670` events
- That is not WMAZE-accurate. The real queue consumer runs per depth:
  - depth `d`: `36AC` phase first, then `3670` phase
  - then next depth

Prototype fix:
- `scratch/render_map_3d_owner_prototype.py` now composites queue events in:
  - `per_depth_phase_order`
- It replays filtered per-depth subsets through the `36AC` and `3670` emulators and composites them in the same phase order as `WMAZE:0x9761..0x98C5`.

Validation artifact (phase-correct queue compositing):
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite6.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite6.json`

Debug JSON confirms:
- `estimated_deferred_queue_composite_mode = "per_depth_phase_order"`

## `3670` Clip Semantics Fix: Wrapped Clip Spans (new)

Updated script:
- `scratch/ega_3670_emu.py`

Problem isolated:
- Many `3670` queue events were composing valid sprites (`220C` succeeded, nonzero tile counts) but drawing `0` pixels.
- Per-event instrumentation showed numerous cases with:
  - `clip_left > clip_right` (e.g. `248..134`)
  - valid sprite placement and dimensions

Fix:
- `_RGBACompositor.blit_sprite(...)` now treats `clip_left > clip_right` as a wrapped visible span:
  - `[clip_left, 320) U [0, clip_right)`
- This matches observed queue behavior better than treating the interval as empty.

Validation (queue-heavy scene `map11 (132,143,E)`):
- before wrapped-clip fix:
  - `real_pixels_drawn = 3678`
  - nonzero `3670` events: `4 / 18`
- after wrapped-clip fix:
  - `real_pixels_drawn = 8078`
  - nonzero `3670` events: `10 / 18`

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite3.json` (before)
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite4.json` (after)
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite4.png`

Interpretation:
- This is a substantive `1D94` parity improvement.
- It also confirms some of the “renderer looks broken” output was caused by clip semantics, not just wrong resource source selection.

## `220C` Occupancy-Mask Cursor Fix (new)

Updated script:
- `scratch/ega_3670_emu.py`

Bug found:
- The software `220C` emulation reset the occupancy-mask cursor (`mask_ptr` + bit mask) at the start of each row.
- In the real `EGA.DRV:0x220C`, the mask cursor state persists across rows (`[bp-0x0A]` / `[bp-0x0C]` are carried through the outer loop).

Why this matters:
- The occupancy bitmask is packed sequentially across the whole `w*h` cell scan, not re-read from the first mask byte every row.
- Resetting per row over-composes tiles and can make junk-looking output appear “better” by drawing too much.

Validation (queue-heavy type-2 attr1 records):
- Before fix:
  - attr1 compose reported `tiles_composed = 42` for a `7x6` frame (all cells filled every time)
- After fix:
  - attr1 compose reports `tiles_composed = 32` (matches packed occupancy semantics)

Scene impact (`map11 (132,143,E)`, queue-composited prototype):
- Before `220C` mask-cursor fix (but after wrapped clip fix):
  - `3670 real_pixels_drawn = 8078`
- After `220C` mask-cursor fix:
  - `3670 real_pixels_drawn = 6138`

Interpretation:
- This is a correctness-driven regression in raw pixel count, and it is expected.
- The previous higher pixel count was partly caused by a real `220C` emulation bug (row-reset mask traversal).

## `36AC` Queue Descriptor Range Fix (new)

Updated script:
- `scratch/ega_36ac_emu.py`

Problem found:
- Queue `36AC` (`type==0xFF`) events in the queue-heavy maze scene included `arg1_desc` values:
  - `181`, `184`, `187`, `190`
- The software `36AC` emulator rejected them because it bounded `arg1_desc` / `arg3_desc` against the declared header count (`word0 = 153` for `MAZEDATA.EGA`).

Correction:
- The `EGA.DRV:0x0B93` path appears to index the second 5-byte header table directly and does not use a `word0` count check.
- `MAZEDATA.EGA` second table starts at `0x301` and the loaded header is `0x800` bytes, so indices like `190` still fit in-header.
- `scratch/ega_36ac_emu.py` now parses the second table (`cs:[0x190]`) to the end of the loaded `0x800`-byte header window (255 records for `MAZEDATA.EGA`), while keeping the declared count as metadata.

Validation (`map11 (132,143,E)` queue-composited scene):
- before:
  - `q36 events_rendered = 14`
  - high-desc events failed with `arg1_desc_idx_range`
- after:
  - `q36 events_rendered = 15`
  - high-desc events decode successfully:
    - three are legitimate no-ops (`repeat_rows_zero`)
    - one (`arg1_desc=184`) becomes a real two-descriptor draw

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_queue36ac_retest.meta.json`
- `scratch/proto_decode_compare/map11_132_143_E_queue36ac_retest.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite7.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite7.png`

Notes:
- The final viewport image for this specific frame did not change (`queuecomposite6` vs `queuecomposite7`, pixel diff `0`), because the newly accepted event is either clipped/occluded or visually redundant in that scene.
- This is still an important emulator correctness fix and removes a false blocker from the deferred `36AC` path.

## `3670` Cross-Source Candidate Selection Fixes (new)

Updated script:
- `scratch/ega_3670_emu.py`

Problems fixed:
- `MON02@0x12` (a replay-clean type-2 chunk for attr set `{0,1,15}`) was being dropped before replay probing because `_score_type_chunk_candidate(...)` structurally rejected it.
- Cross-source MON candidate replay scoring could throw `NameError` (`_replay_score` out of scope) and get silently swallowed by a broad `except`, causing MON sources to disappear from selection.
- `--prefer-exact-1d25-mon-seek0` forced exact seek0 candidates even when they replayed fewer queue events than a heuristic MON candidate.

Corrections:
- Added a low-offset replay-rescue path in `_find_best_type_chunk_rle_offset(...)` for attr0 queue scenes (`scan_start=0`), so structurally-rejected early offsets can still be replay-probed and selected.
- Lifted replay scoring to a shared module helper (`_score_3670_replay_candidate`) so cross-source MON rows are scored correctly (no swallowed `NameError`).
- Guarded the exact-seek0 override: it is now suppressed when the exact candidate has worse replay validity (`events_ok` / fatal failures) than the currently selected candidate.

Validation:
- `map11 (133,143,E)` with queue composite:
  - before (exact override forced `MON02@0x0`):
    - `q37 events_real_replayed = 10/18`
    - `unresolved = {"real_frame_dims_implausible": 8}`
  - after fixes (same CLI, exact flag enabled):
    - `q37 events_real_replayed = 18/18`
    - `unresolved = {}`
    - type-2 chunk selected: `MON02.PIC @ 0x12`
    - override recorded as suppressed due to replay validity
- `map11 (132,143,E)` remains stable:
  - exact seek0 path (`MON02@0x0`) is still selected and valid there (`18/18`)

Artifacts:
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queuecomposite_attr0fix5.json`
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queuecomposite_attr0fix5.png`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite_attr0fix5.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite_attr0fix5.png`

Update (candidate-selection + diagnostics):
- Fixed `3670` MON candidate replay-scoring path in `scratch/ega_3670_emu.py` where cross-source MON rows could be dropped due to a swallowed `NameError` (`_replay_score` scope bug).
- Added low-offset replay-rescue for attr0 queue scenes so structurally-rejected candidates like `MON02.PIC @ 0x12` can still be probed and selected.
- Guarded `--prefer-exact-1d25-mon-seek0` so exact seek0 is not forced when it has worse replay validity than the selected candidate.
- `3670` replay metrics now split `events_real_nonnoop` vs `events_real_noop`, and no-op `real_trace` entries retain `type_index`/`attr` context.
- Selected `type_chunk_candidates` now include `replay_probe` metadata for faster debugging.

Validation:
- `map11 (133,143,E)` with pass+queue composite and exact flag enabled now keeps `MON02.PIC @ 0x12` (exact override suppressed), and `3670` replays `18/18` events with `events_real_nonnoop=4`, `events_real_noop=14`, `unresolved={}`.

Update (`1D25` RLE decoder boundary semantics correction):
- `scratch/ega_3670_emu.py::_decode_1d25_rle_stream(...)` now matches the real `EGA.DRV:0x1D25` refill behavior more closely:
  - refill check is applied at the top-level control-byte loop (`SI >= 0x0FFF`), not to every literal payload byte.
  - literal/repeat payload bytes may still consume the last byte of the 0x1000 scratch block before the next control-byte boundary check.
- This corrected an over-aggressive decoder variant that had been skipping too many compressed-source bytes.

Important consequence:
- The earlier `MON02.PIC @ 0x12` “all 18 queue events replay cleanly” result for `map11 (133,143,E)` was a false positive caused by the overly aggressive block-boundary decode.
- After the corrected `1D25` semantics:
  - `MON02@0x12` no longer replays all events (`first_record_oob` on 8 attr0 events)
  - `MON02@0x0` remains the stronger type-2 candidate under the corrected decoder for that scene (10 non-noop draws, 8 implausible attr0 record-255 cases)

Validation artifacts:
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queuecomposite_1d25blockfix2.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite_1d25blockfix2.json`
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queuecomposite_nonnooprank1.json`

Update (`3670` attr0 queue fallback + `36AC` trace normalization):
- `scratch/ega_3670_emu.py` now treats queue `attr=0` (`record 0xFF`) failures with implausible/missing descriptor 255 as a guarded no-op (`attr0_record255_implausible_dims` / `attr0_record255_unavailable`) instead of a hard replay failure.
  - Rationale: queue consumer passes attr stream `{0,0}`, so the command loop terminates immediately and these events are visually no-op unless descriptor 255 frame metadata is needed for non-visual side effects.
  - `1D94` still probes descriptor `0xFF` frame dims before the attr loop exits, so the fallback remains semantically closer than skipping the probe entirely.
  - New evidence from `scratch/analyze_mon_record255_descriptors.py` shows `record255` is implausible in most decoded `MONxx.PIC @ seek0` chunks, so this is no longer treated as a primary type-2 provenance blocker.
- `scratch/ega_3670_emu.py` replay metrics now expose:
  - `events_real_nonnoop`, `events_real_noop`
  - no-op traces retain `type_index` / `attr` context
  - selected `type_chunk_candidates[*].replay_probe`
- `scratch/ega_36ac_emu.py` trace rows now include normalized event summaries:
  - `event_ok`, `event_nonnoop`, `event_noop`, `event_fail_reasons`, `event_noop_reasons`

Validation:
- `map11 (133,143,E)` (`--prefer-exact-1d25-mon-seek0`):
  - `q37 events_real_replayed=18`, `events_real_nonnoop=10`, `events_real_noop=8`, `unresolved={}`
  - no-op reason: `attr0_record255_implausible_dims` x8
- `map11 (132,143,E)` remains stable:
  - `q37 events_real_replayed=18`, `events_real_nonnoop=18`, `events_real_noop=0`
- `q36` on heavy scene is fully valid under current emulator:
  - `36 total`, `15 non-noop draws`, `21 no-ops`, `0 failures`
  - all no-ops are `repeat_rows_zero`

Artifacts:
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queuecomposite_attr0noop1.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite_attr0noop1.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queuecomposite_36actrace1.json`

Update (`MONxx` descriptor-255 survey):
- Added `scratch/analyze_mon_record255_descriptors.py` to decode `MON??.PIC` with the current software `1D25` decoder (`seek0`) and inspect descriptor `0xFF`.
- Result (`scratch/mon_record255_descriptor_analysis.json`):
  - `record255` is present in most decoded MON chunks, but almost always has implausible frame dims for `3670` (`w<=0`, `h<=0`, or `w/h > 64`).
  - This supports the `attr=0` guarded no-op handling as expected queue behavior for MON-backed chunks rather than a strong signal of missing type-slot overwrite provenance.

Update (`36A0` / `EGA.DRV:0x08B3` deeper semantics):
- Added `scratch/extract_ega_drv_08b3_semantics.py`
  - outputs:
    - `scratch/ega_drv_08b3_semantics.json`
    - `scratch/ega_drv_08b3_disasm.txt`
- `WROOT:0x36A0` (export `0x013B`) is **not** a trivial no-op/present thunk:
  - it copies a rectangular region from driver shadow buffer `cs:[0x14D]` to `A000` plane-by-plane
  - then calls internal helpers (`0x0974`, `0x0B03`) that apply mode-dependent masked overlay/copy behavior using driver tables (`cs:[0x151]`, `cs:[0x11A6]`, `cs:[0x11A8]`, `cs:[0x11AE]`)
- The one wrapper arg (WMAZE pushes `word [0x4FBC]`) is a compact rectangle descriptor, with high-confidence field use in `0x08B3`:
  - `byte[+0]` = width in bytes
  - `byte[+1]` = height in 8-row blocks (routine uses `<<3` scanline count)
  - `byte[+2]` = x byte offset
  - `byte[+3]` = y pixel row
- Practical implication for the software renderer:
  - our current `3670` replay draws directly to the final RGBA image, which collapses the real `1D94 -> shadow` then `36A0 -> present` split.
  - `36A0` may still matter for exact parity because it applies additional mode/table-dependent masked copy behavior after queue/direct `3670` draws.
  - It is now a valid parity target (not just a bookkeeping wrapper), but it is probably secondary to WMAZE queue/pass emission parity unless we move the software pipeline to a driver-shadow-buffer model.

Update (`WROOT:0x011A` rect descriptor constructor + shared [0x4FBC] init):
- Added:
  - `scratch/extract_wroot_011a_rect_descriptor_ctor.py`
  - `scratch/extract_shared_4fbc_rect_initializers.py`
- Artifacts:
  - `scratch/wroot_011a_rect_descriptor_ctor.json`
  - `scratch/wroot_011a_rect_descriptor_ctor_disasm.txt`
  - `scratch/shared_4fbc_rect_initializers.json`

Key result:
- `WROOT:0x011A` constructs the rectangle descriptor consumed by `0x3694` (`EGA 0x0835`) and `0x36A0` (`EGA 0x08B3`), returning a pointer in `AX` that overlays store in shared variables like `[0x4FBC]`.
- The descriptor bytes used by `EGA.DRV:0x08B3` are now traced back to `0x011A` arguments:
  - `[0] = width_bytes`
  - `[1] = height_blocks`
  - `[2] = x_byte_off`
  - `[3] = y_row`
  - plus style/flags/pattern bytes at `[4..15]`

Startup initializer used by WMAZE later (`WINIT -> [0x4FBC]`):
- `WINIT:0x56CD -> call 0x011A`, then `WINIT:0x56D3 -> mov [0x4FBC], AX`
- inferred rect descriptor parameters:
  - `x_byte_off = 9` (`72 px`)
  - `y_row = 4`
  - `width_bytes = 22` (`176 px`)
  - `height_blocks = 14` (`112 px`)
- This matches the canonical first-person viewport size (`176x112`) and strongly confirms `[0x4FBC]` is the shared present/clear rectangle used by `WMAZE` queue/direct `36A0` calls.

Related observation:
- `WPOPS` also rebuilds `[0x4FBC]` with the same x/width and two heights (`96` and `112`) via the same constructor path, confirming the shared-rect model across overlays.

Update (prototype deferred queue alignment to real screen-space viewport rect):
- `scratch/render_map_3d_owner_prototype.py` deferred queue compositing now applies a screen->prototype offset derived from:
  - real queue/direct present rect origin from `[0x4FBC]` (`WINIT`-initialized via `0x011A`): `(72,4)`
  - prototype crop origin: `(12,14)`
  - resulting offset used during queue layer compositing: `(-60,+10)`
- This aligns `36AC/3670` queue replay layers (produced in real 320x200 screen coordinates) with the prototype canvas basis before final crop.

New debug metrics (to avoid false conclusions from alpha-only diffs):
- `estimated_deferred_queue_composite_diff_pixels_canvas`
- `estimated_deferred_queue_composite_diff_pixels_crop`
- `estimated_deferred_queue_composite_diff_pixels_canvas_rgb`
- `estimated_deferred_queue_composite_diff_pixels_crop_rgb`

Validation (queue-heavy scenes):
- `map11 (132,143,E)`:
  - deferred queue composite changes visible crop RGB by `1887` pixels
- `map11 (133,143,E)`:
  - deferred queue composite changes visible crop RGB by `1577` pixels

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queueoffset4.json`
- `scratch/proto_decode_compare/map11_132_143_E_wmazepass_queueoffset4.png`
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queueoffset4.json`
- `scratch/proto_decode_compare/map11_133_143_E_wmazepass_queueoffset4.png`

Update (WMAZE pass gate/cleanup trace instrumentation and comparison tooling):
- `scratch/render_map_3d_owner_prototype.py` now emits richer `wmaze_pass_gate_trace` rows with:
  - `event_type` (`7d8c_topflag`, `pass_skip`, `cleanup_helper`)
  - explicit skip reasons (`gate_flag_false`, `helper_draw_mode_queue_only`, `wall_presence_gate_zero`, etc.)
  - per-depth gate snapshots (`gate_before/after`)
  - marker snapshots (`markers_before/after`)
  - cleanup predicate booleans and triggering pass context
- `scratch/compare_queue_emission_traces.py` now summarizes and depth-normalizes:
  - `wmaze_pass_gate_trace`
  - cleanup delta signatures (which gate flags changed, if any)
- new helper summarizer:
  - `scratch/summarize_wmaze_pass_gate_trace.py`

Validation / findings on same-viewpoint A/B (`map11 (132,143,E)`, helper draw-mode gate on vs off):
- gate trace delta is exactly the expected six `helper_draw_mode_queue_only` skips (depth shift best = `0`)
- cleanup delta signatures are identical (depth shift best = `0`)
- artifact: `scratch/queue_emission_trace_compare_map11_132_143_E_drawmode_onoff_gate2.json`

New concrete parity target isolated by instrumentation:
- In queue-heavy E-facing scenes, cleanup helpers `0x8F1A` / `0x8F4C` can pass their extracted predicates (`pred_8df6_family_5068=True`) while producing no modeled gate/marker/loop-depth changes in the prototype.
- Observed in:
  - `map11 (132,143,E)` at depths `1` and `3`
  - `map11 (133,143,E)` at depth `2`
- This is now the clearest missing WMAZE cleanup-state behavior in the current pass emulator.

Update (implemented exact lower-flag writes for cleanup helpers):
- Corrected from disassembly (`scratch/wmaze_84ec_8f80_disasm_corrected.txt`):
  - `0x8EBB` clears per-depth `0x5083`
  - `0x8EE8` clears per-depth `0x5073` and `0x5084`
  - `0x8F1A` clears per-depth `0x509B` and `0x50A4`
  - `0x8F4C` clears per-depth `0x50A3`
- `scratch/render_map_3d_owner_prototype.py` now tracks these lower flags in the pass-state model and includes them in `wmaze_pass_gate_trace` snapshots.

Validation (same-viewpoint before/after, `map11 (132,143,E)`):
- pass rows: unchanged
- queue entries / consumer events: unchanged
- cleanup delta trace changed exactly for the previously missing rows:
  - `0x8F1A` class `2`: `[] -> ['509b', '50a4']`
  - `0x8F4C` class `2`: `[] -> ['50a3']`
- `predicate_true_but_no_modeled_effect` now drops to `0` for both heavy E-facing scenes.

Additional validation (scene that exercises all cleanup helper families used in the pass loop):
- `map12 (147,158,N)` now hits `0x8DF6`, `0x8E59`, `0x8E8A`, `0x8EBB`, `0x8F4C` with true predicates.
- `wmaze_pass_gate_trace` shows exact modeled flag deltas matching corrected disassembly:
  - `0x8DF6` -> clears `0x5074/0x507B/0x507C/0x508B/0x508C/0x508D/0x5093/0x5094/0x509C`
  - `0x8E59` -> clears `0x507A/0x5073/0x5084`
  - `0x8E8A` -> clears `0x5092/0x509B/0x50A4`
  - `0x8EBB` -> clears `0x5083`
  - `0x8F4C` -> clears `0x50A3`
- artifact:
  - `scratch/proto_decode_compare/map12_147_158_N_cleanupflags2.gatetrace_summary.json`

Static WMAZE cleanup-flag access scan (new):
- `scratch/extract_wmaze_cleanup_flag_accesses.py`
- `scratch/wmaze_cleanup_flag_accesses.json`
- Sliding-decode scan across all of `WMAZE.OVR` finds direct *reads* only for the top gate flags:
  - `0x507A`, `0x5092`, `0x509A`, `0x50A2`
- Lower flags (`0x5073/0x5083/0x5084/0x509B/0x50A3/0x50A4` and center-family cluster) appear as direct writes only in WMAZE code.
- Implication: lower-flag effects are either consumed in helper internals/indirect paths not yet recovered, or they are state written for non-WMAZE subsystems.

Correction / dead-end closed (`0x35C8` / `0x35FD` path):
- The resident WROOT entry near the previously suspected `0x35C8` target is actually `0x35FD`, not a function starting at `0x35C8`.
- `WROOT:0x35FD` is a thin wrapper around internal `WROOT:0x1462`.
- `WROOT:0x1462` is *not* a graphics draw helper:
  - uses BIOS `int 13h`
  - manipulates PIC / PIT / speaker ports (`0x21`, `0x40`, `0x43`, `0x61`)
  - installs/restores interrupt vectors
  - references timing/mode state at `cs:0x1756..0x1764` / `cs:0x19CC..0x19D2`
- This strongly indicates timer/sound/retrace control, not direct wall rendering.
- Result: the remaining direct-render parity problem should not be pursued through `0x35C8/0x35FD`; focus should stay on actual graphics paths (`0x36AC`, `0x3670`, `0x36A0`) and WMAZE helper emission behavior.

Artifact:
- `scratch/wroot_35fd_1462_semantics.json`

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_cleanupflags1.json`
- `scratch/proto_decode_compare/map11_132_143_E_cleanupflags1.gatetrace_summary.json`
- `scratch/proto_decode_compare/map11_133_143_E_cleanupflags1.json`
- `scratch/proto_decode_compare/map11_133_143_E_cleanupflags1.gatetrace_summary.json`
- `scratch/queue_emission_trace_compare_map11_132_143_E_cleanupflags_before_after1.json`
- `scratch/proto_decode_compare/map12_147_158_N_cleanupflags2.json`
- `scratch/proto_decode_compare/map12_147_158_N_cleanupflags2.gatetrace_summary.json`
- `scratch/wmaze_cleanup_flag_accesses.json`

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_gateinstr2.json`
- `scratch/proto_decode_compare/map11_132_143_E_gateinstr2.gatetrace_summary2.json`
- `scratch/proto_decode_compare/map11_133_143_E_gateinstr2.json`
- `scratch/proto_decode_compare/map11_133_143_E_gateinstr2.gatetrace_summary2.json`

Helper-side direct `0x36AC` bridge added to prototype:
- `scratch/render_map_3d_owner_prototype.py` now reconstructs helper-side direct `0x36AC` calls from:
  - `scratch/wmaze_helper_draw_calls.json`
  - `scratch/wmaze_direct_36ac_call_templates.json`
  - per-pass BP immediate map from `scratch/wmaze_render_pass_param_map.json`
- BP-sourced args are depth-adjusted only when the preserved call template context shows `add ax, word ptr [bp + 4]` between source load and push.
- New CLI:
  - `--wmaze-helper-draw-calls-file`
  - `--wmaze-direct-36ac-call-templates-file`
  - `--composite-estimated-helper-direct-36ac`
- New debug payload fields:
  - `wmaze_helper_direct_36ac_events_estimated`
  - `wmaze_helper_direct_36ac_unresolved`
  - `wmaze_helper_direct_36ac_estimated`
  - `estimated_helper_direct_36ac_composited`

Validation:
- `map11 (132,143,E)`:
  - reconstructed helper direct `36AC`: `18` events, `12` rendered, `0` unresolved
  - enabling helper-direct composite changes final cropped RGB by `65` pixels vs queue-only baseline
- `map11 (133,143,E)`:
  - reconstructed helper direct `36AC`: `6` events, `4` rendered, `0` unresolved
  - enabling helper-direct composite changes final cropped RGB by `255` pixels vs queue-only baseline

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_off.json`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_off.png`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_on.json`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_on.png`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_off.json`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_off.png`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_on.json`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_on.png`

Direct-`36AC` primitive fallback suppression:
- Added prototype flag:
  - `--suppress-direct-36ac-primitive-fallback`
- When enabled, pass rows whose helper mode is `direct_36ac` and not `queue_84f1` no longer composite primitive-record fallback images in `render_wmaze_pass_experimental(...)`.
- Cleanup helpers still run for those passes, and the pass rows are retained with:
  - `suppressed_by_helper_draw_mode = "direct_36ac_only"`
  - gate trace reason `helper_draw_mode_direct_36ac_only`

Pass-order helper-direct compositing:
- `--composite-estimated-helper-direct-36ac` now prefers per-event pass order instead of one batched helper image.
- Sort key:
  - `depth`
  - `pass_index`
  - helper `call_addr`
- This better matches the fact that helper direct `36AC` calls happen inside the pass loop, before deferred queue replay.

Validation:
- `map11 (132,143,E)`:
  - suppressing primitive fallback for direct-`36AC` pass rows changes cropped RGB by `29` pixels relative to helper-direct overlay-with-fallback
  - per-event pass-order helper direct compositing matches the batched result on this scene
- `map11 (133,143,E)`:
  - suppressing primitive fallback causes no further cropped RGB change relative to helper-direct overlay-with-fallback
  - per-event pass-order helper direct compositing changes cropped RGB by `18` pixels relative to batched helper-direct compositing

Artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_replace1.json`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_replace1.png`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_order1.json`
- `scratch/proto_decode_compare/map11_132_143_E_helper36ac_order1.png`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_replace1.json`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_replace1.png`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_order1.json`
- `scratch/proto_decode_compare/map11_133_143_E_helper36ac_order1.png`
