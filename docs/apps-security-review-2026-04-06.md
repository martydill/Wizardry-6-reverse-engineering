# Apps Security Review (2026-04-06)

Scope: `apps/character_roster_editor` and `apps/pic_editor`.

## Findings

### 1) Unbounded decompression can cause memory exhaustion (High)
- **Location:** `apps/pic_editor/PicEditor/ImageFormats.cs`, `DecodePicRle`.
- **Issue:** The PIC RLE decoder appends bytes to an output buffer without any maximum size guard.
- **Risk:** A crafted `.PIC` file can force very large output growth and trigger out-of-memory conditions (denial of service).
- **Recommendation:** Add a strict upper bound for decompressed bytes (for example based on expected maximum asset dimensions and frame count), and throw a controlled validation exception once exceeded.

### 2) Missing bounds validation before tile decode leads to crash on malformed files (Medium)
- **Location:** `apps/pic_editor/PicEditor/ImageFormats.cs`, `DecodeTiledPlanar`.
- **Issue:** The decoder directly indexes `data[tileOffset + row + plane * 8]` without validating that the underlying array contains all required bytes for every tile.
- **Risk:** Malformed files can cause `IndexOutOfRangeException` and terminate load operations (denial of service).
- **Recommendation:** Validate `offset + (expectedTiles * 32) <= data.Length` before decoding, and reject malformed payloads with a clear `InvalidDataException`.

### 3) User-controlled frame dimensions can force large allocations (Medium)
- **Location:** `apps/pic_editor/PicEditor/ImageFormats.cs`, `ParsePicFrameEntries`, `LoadPic`, `DecodeTiledPlanar`.
- **Issue:** `widthTiles` and `heightTiles` are parsed from file metadata and used to allocate pixel and tile buffers with no maximum constraints.
- **Risk:** Crafted files can request large allocations repeatedly across entries and degrade availability through excessive memory/CPU usage.
- **Recommendation:** Enforce explicit upper bounds on width/height tiles and frame counts before allocation.

## Notes
- No remote code execution primitives were identified in this review.
- Primary concern is robustness against malformed/untrusted asset files causing denial-of-service behavior.
