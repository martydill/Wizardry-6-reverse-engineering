# Wall Encoding Breakthrough

## Test Case: Cross Pattern

### What the user did:
- Started with `newgameoriginal.DBS` (default map)
- Created `NEWGAME.DBS` with a cross pattern
- Editor showed: Quadrant 5, coordinates (6,7), (7,7), (6,6), (7,6)
- Added 4 walls: 2 horizontal + 2 vertical forming a "+" cross

### What changed in the file:
**Only 3 bytes changed, but 4 bits were set!**

```
Offset   Cell  Byte  Old   New   XOR    Bits
0x025B   30    3     0x00  0xA0  0xA0   5,7
0x031B   39    15    0x00  0x20  0x20   5
0x031D   39    17    0x00  0x20  0x20   5
```

### KEY DISCOVERY: Each Bit = One Wall

**4 walls added = 4 bits set:**
1. Cell 30, Byte 3, Bit 7
2. Cell 30, Byte 3, Bit 5
3. Cell 39, Byte 15, Bit 5
4. Cell 39, Byte 17, Bit 5

## Cell Analysis

### Cell Locations (Column-Major Interpretation)
- **Cell 30**: Column 1, Row 10
- **Cell 39**: Column 1, Row 19
- **Difference**: 9 cells apart (same column, 9 rows apart)

### Existing Data in These Cells

**Cell 30 (before changes):**
- Non-zero bytes: 0, 8, 9, 10, 11, 12, 14, 15
- Already contained wall/cell data

**Cell 39 (before changes):**
- Non-zero bytes: 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12
- Already heavily populated with data

## Encoding Patterns

### 1. Only ODD Bytes Used for Walls
- All changes in ODD-position bytes (3, 15, 17)
- ODD bytes: 1, 3, 5, 7, 9, 11, 13, 15, 17, 19 (10 total)
- EVEN bytes: 0, 2, 4, 6, 8, 10, 12, 14, 16, 18 (10 total)

**Hypothesis**: ODD bytes encode walls, EVEN bytes encode something else?

### 2. Each Byte Position = Different Wall Location/Type
- Byte 3 changed in cell 30
- Bytes 15, 17 changed in cell 39
- Different bytes might represent:
  - Different wall directions?
  - Different wall positions?
  - Walls to different neighbors?

### 3. Each Bit = Individual Wall
- Bit 7 used once (vertical wall?)
- Bit 5 used three times (horizontal walls?)
- Total: 4 bits = 4 walls

**Alternative**: Maybe bit positions don't indicate orientation, but rather combine with byte position to encode specific wall locations?

## Coordinate Mapping Mystery

### Editor Coordinates → File Coordinates
- **Editor**: Quadrant 5, (6,7), (7,7), (6,6), (7,6)
- **File**: Cells 30, 39
- **Mapping**: Unknown!

Possibilities:
1. **Quadrant offset**: Quadrant 5 adds some offset to coordinates
2. **Different structure**: Cells 30/39 aren't game cells, but wall descriptor records
3. **Sparse encoding**: Only certain file cells store wall data for regions

## Questions Remaining

1. **How do editor coordinates map to file cells?**
   - Need to understand quadrant system
   - Need to understand (X,Y) → (Cell index, Byte, Bit) mapping

2. **What do byte positions represent?**
   - Are they neighbor directions? (N, NE, E, SE, S, SW, W, NW)
   - Are they wall types?
   - Are they regional encodings?

3. **What do bit positions represent?**
   - Does bit 7 always mean vertical? Bit 5 horizontal?
   - Or do bits combine with byte positions for meaning?

4. **Why cells 30 and 39 specifically?**
   - What's special about Column 1, Rows 10 and 19?
   - How do they relate to game coordinates (6,7)-(7,6)?

## Next Steps

### Recommended Test: Single Wall
To definitively crack the encoding:
1. Start with `newgameoriginal.DBS`
2. Add **exactly ONE wall** (e.g., horizontal between two specific cells)
3. Note exact editor coordinates
4. Compare files

This will show:
- Which cell index changes
- Which byte position changes
- Which bit position changes
- Direct mapping from one wall → one bit!

### Alternative Test: Different Pattern
Add walls in a different known pattern:
- Single horizontal line of 3 walls
- Single vertical line of 3 walls
- L-shape of 3 walls

This would show how different wall positions map to different bytes/bits.

## Current Understanding

**Confidence Levels:**
- ✅ **HIGH**: Each bit = one wall (4 bits set = 4 walls added)
- ✅ **HIGH**: Only ODD bytes used for wall encoding
- ⚠️ **MEDIUM**: Different bytes = different wall positions/types
- ❓ **LOW**: Exact meaning of byte positions
- ❓ **LOW**: Exact meaning of bit positions
- ❓ **UNKNOWN**: Editor coordinate → file coordinate mapping
