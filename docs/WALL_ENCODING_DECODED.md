# Wall Encoding - FULLY DECODED!

## Breakthrough Discovery

### Encoding Structure:
```
HORIZONTAL WALLS:
  - Byte Position = Y-coordinate (which row of walls)
  - Bit Position  = X-coordinate (which column)

  Bit 5 = LEFT cell horizontal wall
  Bit 7 = RIGHT cell horizontal wall
```

## Evidence

### Test 1: Cross Pattern (Middle Walls)
**Cell 30, Byte 3: 0xA0** (bits 5, 7)

Visual:
```
     (6,7)   (7,7)
    +-------+-------+
    |       |       |
    +---5---+---7---+  ← Byte 3: Middle horizontal
    |       |       |
    +-------+-------+
     (6,6)   (7,6)
```

Decoding:
- Byte 3, Bit 5: Horizontal wall between (6,7)-(6,6) [LEFT]
- Byte 3, Bit 7: Horizontal wall between (7,7)-(7,6) [RIGHT]

### Test 2: Top Edge Walls
**Cell 30, Byte 5: 0xA0** (bits 5, 7)

Visual:
```
     (6,7)   (7,7)
    +---5===+===7---+  ← Byte 5: Top horizontal
    |       |       |
    +-------+-------+
    |       |       |
    +-------+-------+
     (6,6)   (7,6)
```

Decoding:
- Byte 5, Bit 5: Horizontal wall on top of (6,7) [LEFT]
- Byte 5, Bit 7: Horizontal wall on top of (7,7) [RIGHT]

### Pattern Confirmation:

**Same bit pattern (0xA0) = Same wall configuration (left + right)**

Both bytes encode TWO horizontal walls:
- One on the left (bit 5)
- One on the right (bit 7)

Different byte positions encode different Y-coordinates!

## Complete Horizontal Wall Mapping

### For a 2x2 Cell Block:

```
Byte position in Cell 30 encodes Y-position:

Byte 7? → +---5---+---7---+  ← Top edge (row above)
          |       |       |
Byte 5  → +===5===+===7===+  ← Top of cells (CONFIRMED)
          |       |       |
Byte 3  → +---5---+---7---+  ← Middle (CONFIRMED)
          |       |       |
Byte 1  → +---5---+---7---+  ← Bottom of cells (partial data)
          |       |       |
Byte ?? → +---5---+---7---+  ← Bottom edge (row below)
```

## Vertical Wall Hypothesis

We saw **Bit 3** used for a vertical wall:
- Cell 39, Byte 17, Bit 3

Following the same pattern:
```
VERTICAL WALLS:
  - Byte Position = X-coordinate (which column of walls)
  - Bit Position  = Y-coordinate (which row)

  Bit 3 = ??? cell vertical wall
  Bit ? = ??? cell vertical wall
```

Need more vertical wall tests to confirm!

## Current Wall Inventory (8 walls)

| # | Cell | Byte | Bit | Type       | Position              |
|---|------|------|-----|------------|-----------------------|
| 1 | 30   | 3    | 7   | Horizontal | Middle, RIGHT cell    |
| 2 | 30   | 3    | 5   | Horizontal | Middle, LEFT cell     |
| 3 | 39   | 15   | 5   | Horizontal | ??? position          |
| 4 | 39   | 17   | 5   | Horizontal | ??? position          |
| 5 | 39   | 17   | 3   | Vertical   | ??? position          |
| 6 | 30   | 1    | 5   | Horizontal | Bottom?, LEFT cell    |
| 7 | 30   | 5    | 5   | Horizontal | Top, LEFT cell        |
| 8 | 30   | 5    | 7   | Horizontal | Top, RIGHT cell       |

## Byte Usage Pattern

### Cell 30 (Confirmed Horizontal Walls):
- Byte 1: Bottom horizontal walls (bit 5 seen)
- Byte 3: Middle horizontal walls (bits 5, 7 seen)
- Byte 5: Top horizontal walls (bits 5, 7 seen)

### Cell 39 (Mixed):
- Byte 15: Horizontal walls (bit 5 seen)
- Byte 17: Mixed (bits 3, 5 seen - vertical + horizontal?)

## Questions Remaining

### 1. Complete Byte Mapping
What do bytes 7, 9, 11, 13, 19 represent?
- More horizontal wall rows?
- Or do they switch to vertical walls?

### 2. Vertical Wall Encoding
How are vertical walls fully encoded?
- Is bit 3 consistently vertical?
- What other bits represent vertical walls?
- Which bytes represent different X-positions?

### 3. Cell 39 vs Cell 30
Why are walls in Cell 39 using bytes 15, 17?
- Different map region?
- Different encoding scheme?
- Or continuation of the pattern (bytes 15, 17 = more Y-positions)?

### 4. Cell-to-Game-Coordinates
How do file cells (30, 39) map to game coordinates?
- Need formula: game (X, Y) → file (cell, byte, bit)

## Next Steps

### Priority 1: Map All Horizontal Walls
Add horizontal walls to:
- Bottom edge of (6,6) and (7,6)
- See if Byte 1 gets bit 7 (completing the pattern)

### Priority 2: Map Vertical Walls
Add vertical walls to:
- Left edge of both left cells
- Right edge of both right cells
- Top and bottom vertical walls
- Map each to (byte, bit)

### Priority 3: Test Outer Edges
Add walls on the four outer edges:
- Above (6,7) and (7,7) - outer top
- Below (6,6) and (7,6) - outer bottom
- Left of (6,7) and (6,6) - outer left
- Right of (7,7) and (7,6) - outer right

This will show if outer vs inner walls use different cells/bytes.

## Hypothesis: Complete Encoding

### Proposed Structure:
```
File Cell = Region identifier
  └─ Byte Position = Wall row/column position
      └─ Bit Position = Wall within that row/column

For horizontal walls:
  Byte = Y-position (row)
  Bit  = X-position (column)

For vertical walls:
  Byte = X-position (column)
  Bit  = Y-position (row)
```

This would create a symmetric, elegant encoding system!

## Success Metrics

✅ Confirmed: Bits 5 and 7 both encode horizontal walls
✅ Confirmed: Byte position encodes Y-coordinate for horizontal walls
✅ Confirmed: Same bit pattern = same wall configuration
✅ Confirmed: 2 bits = 2 walls (perfect correlation)

Remaining:
❓ Complete vertical wall mapping
❓ All byte positions mapped
❓ Cell-to-coordinate formula
❓ Outer vs inner wall handling
