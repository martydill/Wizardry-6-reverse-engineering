# Wizardry 6 - Map 10 (16x16) Analysis

## Map Location

- **File**: `gamedata/SCENARIO.DBS`
- **Offset**: 40960 (0xA000)
- **Dimensions**: 16x16 (256 cells)
- **Format**: 20 bytes per cell, column-major storage

## Key Findings

### 1. Column Mapping CONFIRMED

**File column = Game column** for the 16x16 map!

- Map 10 uses exactly file columns 0-15
- Perfect 1:1 mapping between file position and game position
- All 16 columns contain wall data

### 2. Byte Usage ANOMALY

**Problem**: Map uses bytes 17-19 which represent rows 16-19!

```
Expected bytes for 16x16: 1, 3, 5, 7, 9, 11, 13, 15 (rows 0-15)
Actual bytes used:        1, 3, 5, 7, 9, 11, 13, 15, 17, 19

Extra bytes: 17 (rows 16-17), 19 (rows 18-19)
```

Usage statistics:
- Byte 17: 63 cell-occurrences
- Byte 19: 65 cell-occurrences

These bytes represent rows BEYOND the 16x16 map boundary!

### 3. No Clear Row Mapping Pattern

Tested hypothesis: "File row N stores game row N"
- **Result**: FAILED - only 2 out of 16 rows matched
- Byte usage is fairly uniform across all file rows
- No correlation between file row and most-used byte

### 4. Wraparound Hypothesis

Tested: Do bytes 17-19 wrap to rows 0-5?
- Byte 17 → Byte 1: 20 matches observed
- Byte 19 → Byte 3: 21 matches observed
- **Result**: Weak correlation, NOT confirmed
- Some matches exist but not consistent enough

### 5. Wall Distribution

Decoding results:
- **Using all bytes (1-19)**: 396 walls across 228 cells
- **Using valid bytes (1-15)**: ~330 walls across ~190 cells
- **Difference**: ~66 walls come from bytes 17-19

## Comparison with Map 0 (20x20)

### Similarities
- Both use column-major storage
- Both use odd bytes for wall encoding
- Both use bits 5 and 7 for left/right positions

### Differences
- Map 0 (20x20): Uses 19 file columns, bytes 1-19 (all valid)
- Map 10 (16x16): Uses 16 file columns, BUT also uses bytes 17-19 (invalid!)

## Hypotheses

### Hypothesis A: Standardized Format
The map file format is standardized for 20x20 maps regardless of actual size:
- All maps allocate 20 bytes per cell
- Extra bytes (17-19) are used even if they extend beyond the map
- This would explain why a 16x16 map uses 20-row encoding

**Evidence**: Strong - explains the anomaly simply

### Hypothesis B: Complex Cell Assignment
File cells don't map directly to game positions:
- Each file cell is "responsible" for specific Y-ranges
- Multiple file cells contribute to the same game area
- Similar to how cells 26-30, 35-39 all stored column 19 in map 0

**Evidence**: Medium - explains overlapping coverage but is complex

### Hypothesis C: Wraparound (UNLIKELY)
Bytes 17-19 wrap to rows 0-5:
- Byte 17 (rows 16-17) → rows 0-1
- Byte 19 (rows 18-19) → rows 2-3

**Evidence**: Weak - some matches but not consistent

## Next Steps

### To Fully Understand the Encoding:

1. **Test middle columns in map 0 (20x20)**
   - Add walls in columns 5, 10, 15
   - Discover which file cells store these columns
   - Derive the complete file cell → game column formula

2. **Render map 10 with correct decoding**
   - Determine if bytes 17-19 should be included
   - Visual comparison may reveal which is correct
   - Compare with actual in-game appearance if possible

3. **Analyze other maps**
   - Check if other 16x16 maps also use bytes 17-19
   - Check if 28x28 maps use bytes beyond 27
   - Pattern might reveal the standardization approach

4. **Row mapping formula**
   - Test adding walls at specific Y-positions in map 10
   - Track which file rows/bytes change
   - Derive the row assignment formula

## Current Understanding: 40%

**What we know:**
- ✅ File column = game column (for map 10)
- ✅ Bits 5,7 = left/right positions
- ✅ Odd bytes store wall data
- ✅ Bytes correlate to Y-positions

**What we don't know:**
- ❓ Why bytes 17-19 are used in 16x16 map
- ❓ How file row maps to game row
- ❓ Complete cell → coordinate formula for map 0
- ❓ Whether to include or exclude bytes 17-19

## Files Created

- `tools/find_map_10.py` - Scans SCENARIO.DBS for maps
- `tools/render_map_10.py` - Renders map 10
- `tools/compare_map_structures.py` - Compares map 0 and map 10
- `tools/analyze_map10_bytes.py` - Analyzes byte usage patterns
- `tools/render_map10_comparison.py` - Side-by-side comparison
- `tools/test_wraparound_hypothesis.py` - Tests byte wraparound

---

**Status**: Partial Understanding
**Confidence**: 40% - Column mapping works, row mapping unclear
**Last Updated**: 2026-02-12
