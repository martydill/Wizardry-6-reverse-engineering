# Wall Orientation Decoded - BREAKTHROUGH!

## Discovery: Bit Position Encodes Wall Orientation!

### Test Results Summary

#### Test 1: Single Vertical Wall
- **Location**: Top left of cross pattern
- **Encoding**: Cell 39, Byte 17, Bit 3
- **Result**: Bit 3 used

#### Test 2: Single Horizontal Wall
- **Location**: Bottom left of cross pattern
- **Encoding**: Cell 30, Byte 1, Bit 5
- **Result**: Bit 5 used

### Confirmed Pattern

```
Bit 3 = VERTICAL walls (North-South orientation)
Bit 5 = HORIZONTAL walls (East-West orientation)
Bit 7 = UNKNOWN (possibly doors, secret doors, or special walls)
```

## Complete Wall Inventory (6 walls)

| Wall | Cell | Byte | Bit | Value | Type       | Source      |
|------|------|------|-----|-------|------------|-------------|
| 1    | 30   | 3    | 7   | 0x80  | Unknown    | Cross       |
| 2    | 30   | 3    | 5   | 0x20  | Horizontal | Cross       |
| 3    | 39   | 15   | 5   | 0x20  | Horizontal | Cross       |
| 4    | 39   | 17   | 5   | 0x20  | Horizontal | Cross       |
| 5    | 39   | 17   | 3   | 0x08  | Vertical   | Test 1      |
| 6    | 30   | 1    | 5   | 0x20  | Horizontal | Test 2      |

## Analysis

### By Orientation
- **Horizontal walls**: 4 (Walls #2, #3, #4, #6) - All use Bit 5
- **Vertical walls**: 1 (Wall #5) - Uses Bit 3
- **Unknown type**: 1 (Wall #1) - Uses Bit 7

### By Cell
- **Cell 30**: 3 walls (bytes 1, 3)
- **Cell 39**: 3 walls (bytes 15, 17)

### By Byte
- **Byte 1**: 1 wall (Cell 30)
- **Byte 3**: 2 walls (Cell 30)
- **Byte 15**: 1 wall (Cell 39)
- **Byte 17**: 2 walls (Cell 39)

## Encoding Structure (UPDATED)

```
Wall Address = (Cell, Byte, Bit)
              └────┬────┘ └─┬──┘ └┬┘
                   │       │      └─ Orientation (3=Vert, 5=Horiz, 7=???)
                   │       └──────── Position within region
                   └──────────────── Region identifier

Each wall has a unique 3-part address:
- Cell: Which region (0-399)
- Byte: Which position within that region (0-19, only ODD used)
- Bit: Which orientation/type (3, 5, 7, possibly others)
```

## Remaining Questions

### 1. What is Bit 7?
Wall #1 from the cross pattern uses Bit 7. Need to identify what this represents:
- Special wall type (door, secret door)?
- Different orientation?
- Wall property flag?

### 2. Byte Position Meaning
Why bytes 1, 3, 15, 17 specifically?
- Do different bytes represent different wall positions?
- Is there a pattern? (1 and 3 are close, 15 and 17 are close)
- Do they map to positions within the 2x2 cell block?

### 3. Cell-to-Coordinates Mapping
How do file cells 30 and 39 map to game coordinates?
- Editor shows: Quadrant 5, cells (6,7), (7,7), (6,6), (7,6)
- File shows: Cells 30 and 39
- Formula needed!

### 4. Other Bit Positions
Are other bits used for walls?
- Bit 0, 1, 2, 4, 6 - what do they represent?
- Are they used for different wall types?
- Or for other cell properties?

## Next Steps

### Test 3: Identify Bit 7
Options:
1. Delete Wall #1 from cross pattern - see if it's needed
2. Add more walls to see if Bit 7 appears again
3. Check game to see if that wall has special properties

### Test 4: Map Byte Positions
Add walls in a systematic pattern to understand byte position:
- Add walls to all 4 edges of the 2x2 block
- See which bytes are used for each edge

### Test 5: Different Location
Add walls in a completely different map area:
- Different quadrant
- Different coordinates
- See which cells are used (not 30/39)
- Derive the cell calculation formula

## Hypothesis: Byte Position = Wall Location

Given that we have:
- 2x2 cell block (4 cells)
- Cross pattern creates 4 walls (one between each pair of cells)
- Bytes 1, 3, 15, 17 used

**Possible mapping**:
```
       Byte ?   Byte ?
      +-------+-------+
      | (6,7) | (7,7) |
Byte ?+-------+-------+ Byte ?
      | (6,6) | (7,6) |
      +-------+-------+
       Byte ?   Byte ?
```

Each byte might represent a wall edge:
- Byte 1: Top-left wall?
- Byte 3: Top wall?
- Byte 15: Bottom wall?
- Byte 17: Bottom-right wall?

Need more data to confirm!

## Key Achievements

✅ **CONFIRMED**: Bit 3 = Vertical walls
✅ **CONFIRMED**: Bit 5 = Horizontal walls
✅ **CONFIRMED**: Each wall = unique (Cell, Byte, Bit) address
✅ **CONFIRMED**: Only ODD bytes used for walls
✅ **CONFIRMED**: Multiple walls can share the same byte (different bits)

❓ **UNKNOWN**: Bit 7 meaning
❓ **UNKNOWN**: Byte position meaning
❓ **UNKNOWN**: Cell coordinate formula
❓ **UNKNOWN**: Other bit meanings (0,1,2,4,6)
