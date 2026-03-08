# Render Pipeline Stage Map

This document is the reset point for the 3D renderer work.

The current prototype in `scratch/render_map_3d_owner_prototype.py` is a hybrid:
- partial `WMAZE` pass-loop emulation
- partial helper direct-draw replay
- partial deferred queue replay
- primitive fallback compositing

That is useful for reverse engineering, but it is not a faithful renderer.

The correct next step is to rebuild rendering as explicit stages that match the original pipeline.

## Goal

Replace the current hybrid compositor with a stage-by-stage renderer that mirrors the game:

1. `WMAZE` builds per-depth/pass state
2. helpers either draw immediately or emit deferred queue entries
3. queue consumer replays deferred work in exact order
4. driver shadow/present stage copies the viewport to the final screen rectangle

## High-Level Pipeline

### Stage 0: Runtime Initialization

Relevant modules:
- `WROOT.EXE`
- `WINIT.OVR`
- `EGA.DRV`

Known responsibilities:
- overlay loading via `WROOT:0x36DC/0x36E9`
- graphics path/template setup in `WINIT`
- descriptor loader `WROOT:0x3688 -> EGA.DRV:0x0731`
- graphics resource loads via `WROOT:0x3664 -> EGA.DRV:0x1D25`
- shared viewport rect init:
  - `WROOT:0x011A`
  - `WINIT` stores resulting descriptor in `[0x4FBC]`

Known outputs used later by maze rendering:
- `WMAZE` DGROUP zero-init state at overlay load
- `EGA.DRV` descriptor tables for `0x36AC`
- type/resource chunks loaded by `0x3664`
- shared rect `[0x4FBC]` for `0x3694/0x36A0`

Known blockers:
- exact runtime chunk-state layout after `0x3664/0x1D25`
- exact shadow-buffer state model around `0x36A0`

### Stage 1: WMAZE View/Pass State Build

Primary routine:
- `WMAZE:~0x90C0`

Known behavior:
- loops per visible depth
- computes class indices:
  - `0x5220`
  - `0x5222`
  - `0x5224`
  - `0x5226`
  - `0x5228`
- performs three `0x7D8C`-family prepass calls for center/left/right state
- mutates top gate flags:
  - `0x5072`
  - `0x507A`
  - `0x5082`
  - `0x508A`
  - `0x5092`
  - `0x509A`
  - `0x50A2`

Current status:
- partially emulated in prototype
- top-flag behavior is much tighter than before
- lower cleanup flags are now modeled on writes, but their consumers are still not fully known

### Stage 2: Immediate Per-Depth Pass Loop

Pass order is extracted in:
- `scratch/wmaze_render_pipeline.json`
- `scratch/wmaze_render_pass_param_map.json`

Known pass sequence:
1. `0x85D0` using class index `0x5220`
2. `0x8B18` using `0x5222`
3. `0x8B18` using `0x5224`
4. `0x8D07`
5. `0x85D0` using `0x5226`
6. `0x85D0` using `0x5226`
7. `0x85D0` using `0x5228`
8. `0x85D0` using `0x5228`

Cleanup helpers interleaved:
- `0x8DF6`
- `0x8E59`
- `0x8E8A`
- `0x8EBB`
- `0x8EE8`
- `0x8F1A`
- `0x8F4C`

Current status:
- pass order is known
- cleanup write-side behavior is now much better modeled
- helper internal behavior is still incomplete

### Stage 3: Helper Dispatch Split

Primary helpers:
- `0x85D0`
- `0x8B18`
- `0x8D07`

Important finding:
- helper indices are split by mode, not all rendered the same way

Known mode split from:
- `scratch/wmaze_helper_draw_mode_map.json`

Examples:
- `0x85D0`:
  - queue-only indices: `1,3,4,8,9`
  - direct-`36AC` indices: `0,2,5,6,7,10,11,12,13,14`
- `0x8B18`:
  - queue-only indices: `8,9`
  - direct-`36AC` indices: `1,3,4,5,6,7,10,11,12,13`

Implication:
- primitive fallback compositing should not be treated as the real output for these helper branches

### Stage 4: Immediate Helper Direct Draws

Known immediate direct draw wrapper:
- `WROOT:0x36AC -> EGA.DRV:0x0B93`

Current confirmed helper behavior:
- many helper branches perform immediate `36AC` calls
- these occur inside the pass loop, before deferred queue replay

Current status:
- direct helper `36AC` calls are now reconstructed from extracted call templates and pass BP-offset constants
- prototype can composite them
- ordering is still approximate compared to the full helper execution context

Main gap:
- the prototype still lacks a clean "helper branch replay" stage that fully replaces primitive fallback

### Stage 5: Deferred Queue Emission

Queue emitter:
- `WMAZE:0x84F1`

Queue storage:
- entries at `0x50D0`
- count at `0x50CE`
- stride `0x0B`

Known queue fields:
- words:
  - `+0`
  - `+2`
  - `+4`
  - `+6`
- bytes:
  - `+8` type
  - `+9` attr
  - `+A` depth tag

Known x/y adjustment provenance:
- bootstrap/runtime tables via `0x0882`
- queue producer uses projection adjustments from:
  - `0x36E4`
  - `0x3717`

Current status:
- queue reconstruction is reasonably strong
- queue args are much less heuristic than earlier

### Stage 6: Deferred Queue Consumption

Queue consumer:
- `WMAZE:0x9761..0x98C5`

Order:
- reverse queue order
- per depth
- phase 1: `type == 0xFF` -> `0x36AC`
- phase 2: `type != 0xFF` -> `0x3670`

Known immediate follow-up:
- `WMAZE:0x98D2 -> 0x36A0`

Current status:
- queue order is known
- prototype replays queue work in per-depth phase order
- this stage is still not fully faithful because the driver-shadow/present split is collapsed

### Stage 7: Deferred `36AC`

Driver path:
- `WROOT:0x36AC -> EGA.DRV:0x0B93`

Current RE status:
- arg mapping is known
- single-descriptor branch is implemented
- two-descriptor branch is implemented
- descriptor-table ownership and patching from `0x0731` are understood

Current renderer status:
- software `36AC` replay exists and is usable
- queue `36AC` path is one of the better-understood parts of the renderer now

Remaining issue:
- exact interaction with shadow/present stage is still missing

## Clean Renderer Status

The clean renderer artifact lives in `scratch/render_stage_reference.py`.

Current stage coverage:
- Stage 1: pass/gate/class structure
- Stage 2: helper emissions
- Stage 3: queue entries and consumer order
- Stage 4: pre-present merged event stream
- Stage 5: shadow-buffer contract, executable replay, coverage-mask image, and first real direct-`36AC` raster replay

Latest clean artifacts:
- `scratch/proto_decode_compare/map11_132_143_E_stage_reference28.json`
- `scratch/proto_decode_compare/map11_132_143_E_stage_reference28.coverage.png`
- `scratch/proto_decode_compare/map11_132_143_E_stage_reference28.shadow.png`

Current important result:
- Stage 5 now executes real direct helper `0x36AC` calls using `MAZEDATA.EGA` + `EGA.DRV`
- On the `map11 (132,143,E)` reference scene:
  - direct `36AC` events total: `12`
  - direct `36AC` events rendered: `8`
  - direct `36AC` events failed: `4`
  - cropped nonzero pixels in the final viewport rect: `0`

Implication:
- direct helper `36AC` arg recovery is now concrete enough to execute
- but raw `36AC` output alone does not yet land in the final viewport
- the next accuracy gap is the shadow/present path (`0x36A0` / `EGA.DRV:0x08B3`) and how pre-present shadow content maps to the visible first-person viewport

More specific follow-up from Stage 5 replay:
- the real direct `36AC` shadow output currently lands at:
  - `x=72..246`
  - `y=128..131`
- while the present rect from `[0x4FBC]` is:
  - `x=72..247`
  - `y=4..115`
- so the currently replayed direct `36AC` content does not overlap the viewport crop at all

This can mean one of two things:
1. Stage 5 still lacks the shadow/present mapping that makes this content visible, or
2. the clean Stage 1/2 predictor is selecting the wrong helper-direct rows/events

New comparison result:
- exact compare between clean Stage 2 direct-helper events and prototype traced helper-direct events shows **zero exact overlap** on both heavy E-facing references:
  - `map11 (132,143,E)`:
    - `scratch/proto_decode_compare/map11_132_143_E_stage_vs_proto_helper36ac_compare1.json`
    - stage events `12`, prototype events `18`, shared exact `0`
  - `map11 (133,143,E)`:
    - `scratch/proto_decode_compare/map11_133_143_E_stage_vs_proto_helper36ac_compare1.json`
    - stage events `12`, prototype events `6`, shared exact `0`

Current conclusion:
- the clean Stage 5 replay is useful, but the next correction target is upstream:
  - Stage 1/2 helper branch prediction for direct `36AC`
- until that matches traced helper events, Stage 5 direct-render replay will stay structurally wrong even if `0x36A0` is modeled better

### Stage 8: Deferred `3670`

Driver path:
- `WROOT:0x3670 -> EGA.DRV:0x1D94`
- internal compositor:
  - `EGA.DRV:0x220C`

Known semantics:
- wrapper arg mapping is known
- clip behavior is partially modeled
- occupancy-mask traversal in `0x220C` is partially modeled
- transform flags are partly known

Current renderer status:
- software `3670` replay exists
- this is still the weakest major stage

Main blockers:
- exact runtime chunk-state after `0x3664/0x1D25`
- exact shadow-buffer / present behavior
- possible remaining helper-side state effects that change which `3670` events exist

### Stage 9: Shadow/Present Path

Wrappers:
- `0x3694 -> EGA.DRV:0x0835`
- `0x36A0 -> EGA.DRV:0x08B3`

Known behavior:
- `0x0835` is a scratch/shadow rectangle fill helper
- `0x08B3` copies from driver shadow buffer to display memory using rect descriptor `[0x4FBC]`
- `0x36A0` is a real stage, not a trivial wrapper

Current renderer status:
- not faithfully implemented
- current prototype draws directly to RGBA image and bypasses the real shadow/present split

This is likely one reason the final image still looks unlike the game even when earlier sub-stages improve.

## What Must Be Rebuilt

The next clean renderer should not be "current prototype plus more fixes".

It should have explicit modules/stages:

1. `scene_state`
- visible depth slots
- class indices
- gate flags
- cleanup state

2. `helper_pass_replay`
- exact per-pass helper branch selection
- immediate direct draw calls
- deferred queue emission

3. `deferred_queue_replay`
- exact consumer ordering
- `36AC` phase
- `3670` phase

4. `driver_shadow_present`
- shadow buffer model
- `3694`
- `36A0`
- final viewport extraction using `[0x4FBC]`

## Immediate Priorities

### Priority 1
Build a complete call graph / state-transition map for the whole render pipeline and keep it separate from the prototype.

Deliverable:
- one reference doc
- one implementation checklist

### Priority 2
Stop using primitive fallback as a silent substitute for helper direct-render branches.

Deliverable:
- explicit marking of which branches are:
  - immediate direct draw
  - deferred queue
  - unresolved

### Priority 3
Model shadow/present path explicitly.

Deliverable:
- software shadow buffer for the viewport rectangle
- `36A0`-style present stage

### Priority 4
Then return to `3670` runtime chunk-state parity.

Deliverable:
- exact `0x3664/0x1D25`-backed source state for replay

## Clean Implementation Baseline

New clean-stage skeleton:
- `scratch/render_stage_reference.py`

Purpose:
- build a stage-based reference object without using the hybrid pass/queue compositor
- separate:
  - runtime initialization state
  - scene extraction state
  - later rendering stages

Current output shape:
- `RuntimeInitState`
  - startup overlay order
  - WMAZE overlay-local init region
  - zero-initialized render flags/queue words
  - WINIT graphics init calls
  - shared viewport rect `[0x4FBC]`
  - `0x0882` bootstrap tables
- `SceneState`
  - map id / position / facing
  - block origins
  - visible slot list with:
    - orient
    - depth
    - wall value
    - cell ref
    - `channel4`
    - `channel2`

Validation artifact:
- `scratch/proto_decode_compare/map11_132_143_E_stage_reference1.json`

This file is now the correct place to start Stage 1 reimplementation:
- pass-state build
- class index derivation
- gate-state mutation

It is intentionally not rendering pixels yet.

Updated clean-stage baseline:
- `scratch/render_stage_reference.py` now emits:
  - `Stage1PassState`
  - `Stage2HelperEmission`
  - `Stage3QueueState`
  - `Stage4PrePresent`
  - `Stage5PresentContract`
- new output artifact:
  - `scratch/proto_decode_compare/map11_132_143_E_stage_reference27.json`
  - `scratch/proto_decode_compare/map11_132_143_E_stage_reference27.coverage.png`

Current Stage 1 contents:
- structural pass templates from `scratch/wmaze_render_pass_param_map.json`
- helper mode family per pass
- classifier/draw-map family tags
- initial gate-state snapshot from WMAZE zero-initialized DGROUP state
- per-depth pass rows bound to visible slot hints (`center`, `left`, `right`) where known
- per-pass candidate draw-index splits:
  - possible mapped draw indices
  - direct `36AC` candidate indices
  - queue `84F1` candidate indices
  - explicit no-output indices
- predicted per-depth class state:
  - `0x5220/0x5222/0x5224/0x5226/0x5228`
- predicted top-gate state and pass gating
- predicted output mode per pass row:
  - `gated_off`
  - `direct_36ac`
  - `queue_84f1`
  - `no_output`
  - `immediate_non_helper_dispatch`
  - `unresolved`

Current Stage 2 contents:
- normalized immediate direct-helper event stream
  - `immediate_direct_36ac_events`
- normalized deferred queue-emission event stream
  - `deferred_queue_emission_events`
- explicit runtime dependencies for unresolved symbolic sources

Current Stage 3 contents:
- normalized `0x50D0`-style queue entries
  - `predicted_queue_entries`
- normalized queue-consumer ordering
  - per-depth reverse order
  - `36ac_pair1`
  - `36ac_pair2`
  - `3670`

Current Stage 4 contents:
- merged pre-present draw stream
  - immediate helper direct draws first
  - deferred queue-consumer events afterward
- explicit statement that these are still not final screen pixels

Current Stage 5 contents:
- explicit `0x36A0 -> EGA.DRV:0x08B3` present contract
- shared viewport rect `[0x4FBC]`
- required shadow/present inputs
- unresolved driver-shadow dependencies
- executable shadow-buffer replay target
- placeholder-but-executable spatial coverage accumulation for:
  - direct `36AC`
  - deferred `36AC`
  - deferred `3670`
- clean coverage-mask image export from Stage 5 replay
- clean shadow-image export now replays:
  - direct helper `36AC`
  - deferred queue `36AC`
  - deferred queue `3670`
  - in Stage 5 op order instead of family-batched order

Recent correction:
- Stage 1/2 direct-helper prediction now exactly matches traced prototype helper-direct `36AC` events on:
  - `map11 (132,143,E)` -> `18/18` exact
  - `map11 (133,143,E)` -> `6/6` exact
- Root causes fixed:
  - wrong left/right scene edge extraction in the clean scene model
  - wrong cleanup/gate sequencing in the clean pass loop
  - missing right-side `depth_index = depth-1` adjustment on `0x85D0` passes `6/7`
  - missing center-wall depth stop for farther pass generation

New clean Stage 5 baseline:
- direct-only clean shadow crop was effectively blank on the heavy E-facing reference scene
- after adding deferred queue replay in op order, clean Stage 5 shadow output is now non-empty:
  - `map11 (132,143,E)` shadow crop nonzero alpha pixels: `19712`
  - `map11 (133,143,E)` shadow crop nonzero alpha pixels: `19712`

Latest Stage 5 correction:
- clean queue normalization now resolves the two known scalar `0x84F1` symbolic fields:
  - `word ptr [0x363e]` -> `0x000F` for the `0x869A` attr source
  - `word ptr [bx + 0x52]` -> `word ptr [0x52 + (6*depth_index + 2*bp8)]` using the recovered WROOT DGROUP `0x52` table
- as a result, deferred `3670` ops are now concrete in clean Stage 5 replay instead of being skipped as symbolic

Current clean Stage 5 execution metrics:
- `map11 (132,143,E)`:
  - deferred `36AC`: `48 total`, `18 rendered`, `12 failed`
  - deferred `3670`: `18 total`, `18 replayed`, `18 non-noop`, `0 failed`
  - combined shadow crop nonzero pixels: `583`
- `map11 (133,143,E)`:
  - deferred `36AC`: `48 total`, `18 rendered`, `12 failed`
  - deferred `3670`: `18 total`, `18 replayed`, `18 non-noop`, `0 failed`
  - combined shadow crop nonzero pixels: `758`

Present-stage follow-up:
- Stage 5 replay now records the explicit viewport-present result:
  - `present_36a0_crop_nonzero_pixels`
  - `present_36a0_crop_bbox`
- for `map11 (132,143,E)`:
  - `present_36a0_crop_nonzero_pixels = 583`
  - `present_36a0_crop_bbox = (0,36)..(175,97)`

`0x36A0 / EGA.DRV:0x08B3` next concrete dependency:
- targeted scan now shows real runtime writes to the present-helper pointers:
  - `0x17E8: mov word ptr cs:[0x11A8], ax`
  - `0x17EC: mov word ptr cs:[0x11A6], bx`
- the same routine also refreshes runtime state around:
  - `0x117A..0x1182`
  - `0x11AA..0x11AE`
  - ends with `rep movsb` copies into `0x1182` and `0x11AE`
- implication:
  - the remaining `0x36A0` gap is not just viewport cropping
  - there is a driver-side state machine around `0x172F..0x182D` that prepares the masked overlay helpers used after the raw rect copy

Current `0x36A0` state-machine model:
- extracted in `scratch/ega_drv_36a0_present_state_machine.json`
- raw focused disassembly now also saved in:
  - `scratch/ega_drv_36a0_state_machine_disasm.txt`
- key routines:
  - `0x156C..0x15CC`
    - derives current grid state from rect coordinates
    - writes:
      - `0x117E = cx`
      - `0x1180 = dx`
      - `0x11AD = 0x19 - (0x1180 >> 3)`
      - `0x11AC = 0x28 - (0x117E >> 4)`
      - `0x1194[0..8] = 3x3 cell-grid indices (row stride 0x28)`
      - `0x11C0[0..8] = 3x3 screen destination offsets (row stride 0x140)`
  - `0x1836..0x189D`
    - marks `0x40` occupancy bits in the 3x3 cell map at `DS:[0x1182 + {...}]`
  - `0x189E..0x18C5`
    - clears those same `0x40` bits
  - `0x172F..0x182D`
    - uses `0x198B` and `0x1998` to prepare runtime tables/state
    - swaps `0x11A6 <-> 0x11A8`
    - copies current state to prior state (`0x117E/0x1180 -> 0x117A/0x117C`, `0x11AD/0x11AC -> 0x11AB/0x11AA`)
    - refreshes `0x1182` and `0x11AE` from static templates
  - `0x18F6..0x1988`
    - issues a row/column-clipped subset of `0x1B98` overlay copies
    - current clean model now records this as `present_36a0_overlay_call_plan`
    - on `map11 (132,143,E)`, the viewport rect produces a full 3x3 plan:
      - `present_36a0_helper_copy_count = 9`
  - `0x1B98..0x1BE0`
    - copies one 8x8 four-plane tile from the CS pattern table to A000
    - returns with `SI += 8`
  - `0x0974 / 0x0A2B / 0x0B03`
    - this is temporal, not just single-frame masking
    - `0x0974` saves sequential shadow tiles into `0x11A8`
    - `0x0A2B` saves indexed display tiles into `0x11A6` using `0x11AE`
    - `0x0B03` replays sequential tiles from `0x11A8`
    - `0x19DF` swaps `0x11A6 <-> 0x11A8`
    - implication:
      - exact `0x36A0` parity requires persistent per-frame present state, not only one-frame replay

Temporal present-state artifact:
- `scratch/ega_drv_36a0_temporal_semantics.json`
- clean Stage 5 now reports:
  - `present_36a0_requires_temporal_state = true`

This is now the narrowest known implementation target for exact Stage 5 present parity.

Current deliberate limitation:
- only top-gate behavior is modeled
- lower cleanup flags are not yet consumed
- no software `0x36A0` present implementation yet
- still no final-pixel renderer in the clean architecture

That is acceptable at this stage. The point is to make Stage 1 and Stage 2 branch structure explicit and data-driven before rebuilding rendering behavior on top of it.

## What To Avoid

- do not keep layering estimated stages on top of primitive fallback without isolating which stage they replace
- do not prefer heuristic chunk candidates just because they produce more pixels
- do not use moving-camera comparisons to judge parity unless depth-shift normalization is applied

## Current Baseline

Current baseline for comparison remains the hybrid prototype:
- `scratch/render_map_3d_owner_prototype.py`

But it should now be treated as:
- a RE harness
- a trace exporter
- a staging ground for isolated stage experiments

It should not be treated as the architecture of the final renderer.
