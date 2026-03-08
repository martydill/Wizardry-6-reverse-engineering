# Render Call Graph

Reference artifact:
- `scratch/render_call_graph.json`

This is the condensed call graph for the rendering pipeline. It complements `docs/render_pipeline_stage_map.md` by listing the actual owner modules and call chains.

## Startup / Ownership

WROOT startup overlay dispatch order:
1. `WINIT.ovr`
2. `WBASE.ovr`
3. `WMAZE.ovr`
4. `WMELE.ovr`
5. `WPOPS.ovr`
6. `WMEXE.ovr`
7. `WTREA.ovr`
8. `WPCMK.ovr`
9. `WPCVW.ovr`
10. `WMNPC.ovr`
11. `WDOPT.ovr`

Important implication:
- `WINIT` runs before `WMAZE`, so graphics init and shared rect/driver state can be treated as preconditions for maze rendering.

## WROOT Wrapper To EGA.DRV Mapping

Main rendering wrappers:
- `0x3664` -> `EGA.DRV:0x1D25`
- `0x3670` -> `EGA.DRV:0x1D94`
- `0x367C` -> driver export `0x012F`
- `0x3688` -> `EGA.DRV:0x0731`
- `0x3694` -> `EGA.DRV:0x0835`
- `0x36A0` -> `EGA.DRV:0x08B3`
- `0x36AC` -> `EGA.DRV:0x0B93`

Interpretation:
- `3664` = resource/chunk load
- `3688` = descriptor-table load/init
- `36AC` = immediate/deferred descriptor draw path
- `3670` = immediate/deferred sprite/attr draw path
- `3694` + `36A0` = shadow/present/update path

## WINIT Graphics Initialization Chain

Key startup graphics edges already confirmed:
- `WINIT -> 0x3688`
  - loads descriptor tables for `36AC`
- `WINIT -> 0x3664`
  - loads graphics chunks / type resources
- `WINIT -> 0x3694`
  - shadow-buffer rectangle helper
- `WINIT -> 0x36A0`
  - present/update using shared rect

Known shared state initialized before maze rendering:
- `[0x4FBC]` viewport rect descriptor
- descriptor tables for `36AC`
- driver chunk/type state loaded via `3664`

## WMAZE Render Chain

### Pass Loop

Top-level pass loop:
- `WMAZE:~0x90C0`

Extracted pass sequence:
1. `0x85D0`
2. `0x8B18`
3. `0x8B18`
4. `0x8D07`
5. `0x85D0`
6. `0x85D0`
7. `0x85D0`
8. `0x85D0`

Cleanup helpers interleaved:
- `0x8DF6`
- `0x8E59`
- `0x8E8A`
- `0x8EBB`
- `0x8EE8`
- `0x8F1A`
- `0x8F4C`

### Helper Draw-Mode Split

Important extracted fact:
- helper branches are not one uniform render path

`0x85D0`
- queue-only: `1,3,4,8,9`
- direct `36AC` only: `0,2,5,6,7,10,11,12,13,14`

`0x8B18`
- queue-only: `8,9`
- direct `36AC` only: `1,3,4,5,6,7,10,11,12,13`

This is one reason the hybrid renderer diverges: primitive fallback is not the original output for many of these branches.

## Deferred Queue Chain

Emission:
- helper handlers -> `WMAZE:0x84F1`

Consumption:
- `WMAZE:0x9761..0x98C5`

Consumer phases:
1. `type == 0xFF` -> `0x36AC`
2. `type != 0xFF` -> `0x3670`
3. post-consume present/update -> `0x36A0`

Important implication:
- queue replay is not the final screen output by itself
- it feeds the driver shadow/present path

## Direct Wrapper Usage By Module

Cross-module direct wrapper counts in `scratch/render_call_graph.json` show:
- `WMAZE` directly uses:
  - `36AC`
  - `3670`
  - `3694`
  - `36A0`
- direct `3664` is absent from `WMAZE`
- `WINIT`, `WBASE`, `WMNPC`, `WDOPT`, `WMELE` participate in graphics init/load paths

Interpretation:
- maze rendering depends on runtime graphics state produced outside `WMAZE`
- `WMAZE` mostly consumes already-initialized driver state

## What This Means For Reimplementation

The clean renderer should be built from these graph segments:

1. startup graphics init
2. `WMAZE` pass/helper stage
3. helper immediate draw stage
4. deferred queue stage
5. shadow/present stage

It should not:
- mix primitive fallback with helper direct-draw paths by default
- treat queue replay as the final present step

## Current Hard Blockers

1. exact `3664 -> 1D25` runtime chunk-state model
2. exact `3670 -> 1D94/220C` replay against that state
3. explicit software shadow/present stage for `3694/36A0`
4. remaining helper-internal state effects that alter immediate-vs-queued output

## Runtime Initialization Contract

Reference artifact:
- `scratch/render_runtime_init_requirements.json`

This is the minimum startup state a clean maze renderer must model before the first frame:

1. `WINIT` has already run before `WMAZE`
- startup overlay order from `WROOT` confirms:
  - `WINIT`
  - `WBASE`
  - `WMAZE`
  - ...

2. `WMAZE` starts from overlay-local DGROUP/BSS state
- `WMAZE.OVR` runtime DGROUP starts at `0x4FEE`
- render-state words/bytes start zero at overlay load, including:
  - `0x5040`
  - `0x5066/0x5067/0x5068`
  - `0x5072/0x507A/0x5082/0x508A`
  - `0x5092/0x509A/0x50A2`
  - `0x50CE/0x50D0`
  - `0x521E`
  - `0x5220/0x5222/0x5224/0x5226/0x5228`

3. Descriptor state for `36AC` must already exist
- `WINIT -> 0x3688 -> EGA.DRV:0x0731`

4. Type/chunk state for `3670` must already exist
- `WINIT` directly calls `0x3664` multiple times before maze rendering

5. `0x0882` bootstrap tables must already exist
- loaded from:
  - `MASTER.HDR`
  - `DISK.HDR`
- these feed:
  - record sizes / flags
  - base offsets
  - type metadata records

6. Shared viewport rect `[0x4FBC]` must already exist
- initialized from `WROOT:0x011A`
- `WINIT` canonical viewport:
  - `x = 72`
  - `y = 4`
  - `w = 176`
  - `h = 112`

Implementation implication:
- a clean renderer cannot start from only map geometry + MAZEDATA tiles
- it must either:
  - emulate these init stages, or
  - load an equivalent precomputed runtime state
