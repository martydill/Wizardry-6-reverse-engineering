# Wall Mapping Data - Test Results

## Test 1: Cross Pattern (4 walls)
**Editor location**: Quadrant 5, cells (6,7), (7,7), (6,6), (7,6)
**Type**: 2 horizontal + 2 vertical walls forming a "+" cross

### Encoding:
| Wall # | Cell | Byte | Bit | Value | Type      |
|--------|------|------|-----|-------|-----------|
| 1      | 30   | 3    | 7   | 0x80  | ?         |
| 2      | 30   | 3    | 5   | 0x20  | ?         |
| 3      | 39   | 15   | 5   | 0x20  | ?         |
| 4      | 39   | 17   | 5   | 0x20  | ?         |

**Total**: Cell 30 Byte 3 = 0xA0, Cell 39 Byte 15 = 0x20, Cell 39 Byte 17 = 0x20

## Test 2: Added Single Vertical Wall
**Editor location**: Top left section of cross pattern
**Type**: 1 vertical wall

### Encoding:
| Wall # | Cell | Byte | Bit | Value | Type     |
|--------|------|------|-----|-------|----------|
| 5      | 39   | 17   | 3   | 0x08  | Vertical |

**Result**: Cell 39 Byte 17 changed from 0x20 to 0x28 (added bit 3)

## Combined Data (5 walls total)

### File State:
- **Cell 30, Byte 3**: 0xA0 (bits 7,5) = 2 walls
- **Cell 39, Byte 15**: 0x20 (bit 5) = 1 wall
- **Cell 39, Byte 17**: 0x28 (bits 5,3) = 2 walls

### All Walls:
| Wall # | Cell | Col | Row | Byte | Bit | Binary Position | Decimal Value |
|--------|------|-----|-----|------|-----|-----------------|---------------|
| 1      | 30   | 1   | 10  | 3    | 7   | 10000000        | 128 (0x80)    |
| 2      | 30   | 1   | 10  | 3    | 5   | 00100000        | 32 (0x20)     |
| 3      | 39   | 1   | 19  | 15   | 5   | 00100000        | 32 (0x20)     |
| 4      | 39   | 1   | 19  | 17   | 5   | 00100000        | 32 (0x20)     |
| 5      | 39   | 1   | 19  | 17   | 3   | 00001000        | 8 (0x08)      |

## Patterns Observed

### 1. Cell Usage
- Only 2 cells used: **30** and **39**
- Both in Column 1
- Row difference: 19 - 10 = 9
- Cell difference: 39 - 30 = 9

### 2. Byte Usage
- Only ODD bytes: **3, 15, 17**
- Multiple walls can share the same byte
- Byte 3: 2 walls (bits 7,5)
- Byte 15: 1 wall (bit 5)
- Byte 17: 2 walls (bits 5,3)

### 3. Bit Usage
- Bit 7: used 1× (Cell 30, Byte 3)
- Bit 5: used 4× (Cell 30 Byte 3, Cell 39 Bytes 15,17)
- Bit 3: used 1× (Cell 39, Byte 17)

### 4. Same Bit in Different Bytes
Bit 5 appears in 4 different locations:
- Cell 30, Byte 3, Bit 5
- Cell 39, Byte 15, Bit 5
- Cell 39, Byte 17, Bit 5 (twice in byte 17 doesn't make sense, so these must be different walls)

**This suggests**: The combination of (Cell + Byte + Bit) uniquely identifies a wall position!

## Encoding Hypothesis

### Three-Level Address:
```
WALL_ADDRESS = (Cell_Index, Byte_Position, Bit_Position)
```

Each wall has a unique 3-part address:
- **Cell Index**: Which of the 400 20-byte "cells" (0-399)
- **Byte Position**: Which of the 20 bytes within that cell (0-19)
- **Bit Position**: Which of the 8 bits within that byte (0-7)

### Theoretical Maximum:
- 400 cells × 20 bytes × 8 bits = **64,000 possible wall positions**
- But only ODD bytes used = 400 × 10 × 8 = **32,000 possible wall positions**

This is WAY more than needed for a 20×20 map (400 cells × 4 walls/cell = 1,600 walls max).

**Conclusion**: The data structure might support MUCH larger maps, or encode additional wall properties (door types, secret doors, etc.)

## Questions to Answer

1. **Coordinate Mapping**: How do editor coords (6,7) map to cell 30/39?
2. **Byte Meaning**: Why bytes 3, 15, 17 specifically?
3. **Bit Meaning**: Why bits 3, 5, 7 specifically?
4. **Orientation**: Does bit position or byte position indicate H/V orientation?
5. **Pattern**: Is there a formula to convert wall position → (cell, byte, bit)?

## Next Tests Needed

### Test 3: Single Horizontal Wall
Add ONE horizontal wall (not vertical) to see:
- Does it use different bits (not 3, 5, 7)?
- Same cells or different cells?
- Same bytes or different bytes?

This would show if orientation is encoded in bit position!

### Test 4: Different Location
Add walls in a completely different map area (different quadrant) to see:
- Does it use different cells (not 30, 39)?
- How does the cell number relate to map position?

### Test 5: Systematic Grid
Add walls in a regular pattern (like a checkerboard) to derive the formula.
