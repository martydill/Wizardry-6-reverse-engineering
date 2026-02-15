# Wizardry 6 Map 10 - Coordinate Mapping Breakthrough

## Feature Markers Discovered

### Fountains
**Byte 18 = 0xA0** (4 occurrences)
- Cell 4, Cell 200, Cell 237, Cell 255

### Sconces
**Byte 0 = 0xA0** (4 occurrences)
- Cell 65, Cell 69, Cell 72, Cell 136

## Known Mappings

### Sconces (Confirmed Positions)

| Cell | File (col,row) | Game (x,y) | Delta (Δx,Δy) |
|------|----------------|------------|---------------|
| 65   | (4, 1)         | (7, 7)     | (+3, +6)      |
| 69   | (4, 5)         | (8, 7)     | (+4, +2)      |
| 72   | (4, 8)         | (7, 8)     | (+3, +0)      |
| 136  | (8, 8)         | (8, 8)     | (+0, +0) ✓    |

### Fountains (Expected at corners)

| Cell | File (col,row) | Game (x,y) Expected |
|------|----------------|---------------------|
| 4    | (0, 4)         | (0, 0) or (0, 15)?  |
| 200  | (12, 8)        | ?                   |
| 237  | (14, 13)       | ?                   |
| 255  | (15, 15)       | (15, 15)?           |

Expected fountain corners: (0,0), (15,0), (0,15), (15,15)

## Critical Discoveries

### 1. Interleaved Column Storage

**File column 4 stores MULTIPLE game X coordinates!**
- File (4, 1) → game X=7
- File (4, 5) → game X=8
- File (4, 8) → game X=7

The game X depends on BOTH file_col AND file_row, not file_col alone!

### 2. Center Point is 1:1

**Cell 136: file (8,8) → game (8,8)** - Perfect match!

File column 8 and row 8 appear to be the "center" with direct mapping.

### 3. Variable Deltas

The delta between file and game coordinates is NOT constant:
- Δx ranges from +0 to +4
- Δy ranges from +0 to +6

No simple linear formula like `game_x = file_col + offset`.

## Hypotheses

### Hypothesis 1: Quadrant-Based Interleaving

The 16×16 map is divided into 4 quadrants (8×8 each). Each file column might store data for positions in multiple quadrants in an interleaved pattern.

For example, file column 4 might store:
- Even rows: game X=7 (left of center)
- Odd rows: game X=8 (right of center)

But this doesn't fully match the data (cells 65, 69, 72 have rows 1, 5, 8).

### Hypothesis 2: Tiled Storage

Map stored in 8×8 tiles, with file positions encoding tile + offset within tile.

### Hypothesis 3: Overlapping Coverage

Similar to how walls in map 0 had overlapping coverage (multiple file cells for same game column), the coordinate mapping might use overlapping regions.

## Pattern Observations

### File Row → Game Y Pattern

Looking at file column 4:
- Row 1 → game Y=7 (delta +6)
- Row 5 → game Y=7 (delta +2)
- Row 8 → game Y=8 (delta +0)

Delta decreases as file_row increases! Possible formula:
```
game_y = file_row + (offset - something based on position?)
```

### File Col → Game X Pattern

File column 4:
- With row 1 or 8 → game X=7
- With row 5 → game X=8

File column 8:
- With row 8 → game X=8 (1:1)

## Next Test Needed

To crack the formula, we need more data points. Suggested test:

**Add a feature at game position (0, 0)** (or verify which fountain is there)

This would give us a corner position in the bottom-left, completing our corner coverage:
- (0, 0) - bottom-left ← NEED THIS
- (15, 0) - bottom-right
- (0, 15) - top-left
- (15, 15) - top-right

With one corner from each quadrant + the center sconces, we could derive:
1. How each quadrant maps to file positions
2. The interleaving pattern
3. Complete file→game formula

## Summary

**Solved**:
- ✅ Fountain marker: byte 18 = 0xA0
- ✅ Sconce marker: byte 0 = 0xA0
- ✅ Center point mapping: (8,8) → (8,8)
- ✅ Interleaved storage confirmed

**Remaining**:
- ❓ Complete file→game coordinate formula
- ❓ Which fountain is at which corner
- ❓ Quadrant storage organization

**Confidence**: 70% - We have key data but need formula

---

**Last Updated**: 2026-02-12
