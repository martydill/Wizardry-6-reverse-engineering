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
