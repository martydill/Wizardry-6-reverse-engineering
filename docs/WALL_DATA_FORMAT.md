# Wizardry 6 Wall Data Format

## Discovery Method

Compared two save files (`newgame.dbs` vs `newgameold.dbs`) where the only difference was walls added in the top-right corner of the first map.

## File Structure

Maps are stored with **8 bytes per cell** in a **20×20 grid** (400 cells total).

## Map Cell Format (8 bytes per cell)

```
Offset  Description
------  -----------
0-2     Unknown (various properties)
3       Wall flags (byte 3)
4       Unknown
5       Wall flags (byte 5)
6-7     Unknown
```

## Wall Encoding Discovery

### Changed Bytes

Only **3 bytes changed** between the two files:

| Offset   | Cell     | Position | Byte | Old  | New  | XOR  | Bits Changed    |
|----------|----------|----------|------|------|------|------|-----------------|
| 0x00025B | Cell 75  | (3, 15)  | 3    | 0x00 | 0x80 | 0x80 | Bit 7           |
| 0x00025D | Cell 75  | (3, 15)  | 5    | 0x00 | 0x80 | 0x80 | Bit 7           |
| 0x0003 1D | Cell 99  | (4, 19)  | 5    | 0x00 | 0xA0 | 0xA0 | Bits 7 and 5    |

### Cell Data (from newgameold.dbs with walls)

**Cell (3,15):** `02 00 00 80 00 80 00 00`
- Byte 3: 0x80 = `10000000` (bit 7)
- Byte 5: 0x80 = `10000000` (bit 7)

**Cell (4,19):** `02 00 00 00 00 A0 00 00`
- Byte 5: 0xA0 = `10100000` (bits 7, 5)

## Hypotheses

### Hypothesis 1: Directional Wall Bits

Each byte controls different wall directions:

**Byte 3** (north/south walls?):
- Bit 7 (0x80): North wall
- Bit 6 (0x40): South wall
- Bits 0-5: Other properties/special walls

**Byte 5** (east/west walls?):
- Bit 7 (0x80): East wall
- Bit 6 (0x40): ???
- Bit 5 (0x20): West wall
- Bits 0-4: Other properties

### Hypothesis 2: Horizontal/Vertical Walls

- **Byte 3**: Horizontal walls (north/south edges)
- **Byte 5**: Vertical walls (east/west edges)

## Bit Usage Statistics

Across all 400 cells in the map:

**Byte 3 bit usage:**
- Bit 0: 14.8% | Bit 1: 17.2% | Bit 2: 13.8% | Bit 3: 11.5%
- Bit 4:  7.2% | Bit 5: 10.0% | Bit 6:  4.5% | Bit 7:  6.8%

**Byte 5 bit usage:**
- Bit 0: 17.0% | Bit 1: 18.8% | Bit 2: 11.5% | Bit 3: 10.2%
- Bit 4:  9.2% | Bit 5:  9.2% | Bit 6:  7.0% | Bit 7:  4.8%

## Common Values

**Byte 3 (non-zero):**
- 0x01, 0x02, 0x04: Low bits (most common)
- 0x28 = `00101000`: Bits 5,3
- 0xAA = `10101010`: Bits 7,5,3,1
- 0x80 = `10000000`: **Only bit 7** (rare - only 5 cells including added walls)

**Byte 5 (non-zero):**
- 0x01, 0x02, 0x03, 0x04: Low bits (most common)
- 0x28 = `00101000`: Bits 5,3
- 0x80 = `10000000`: **Only bit 7** (rare - only 5 cells including added walls)
- 0xA0 = `10100000`: Bits 7,5

## Key Observations

1. **Pure 0x80 value is rare** - appears in only 5 cells total (including the 2 we added)
2. **Cells changed are in top-right region:**
   - Cell (3,15) - column 15 of 0-19
   - Cell (4,19) - column 19 (right edge)
3. **Only 2 cells changed for "walls on all 4 sides"** suggests walls may be shared between adjacent cells
4. **Lower bits (0-4)** are much more common than high bits (6-7), suggesting:
   - High bits = actual walls (rare)
   - Low bits = other properties (common)

## Open Questions

1. Why only 2 cells changed for "walls on all 4 sides"?
   - Could walls be edge-based rather than cell-based?
   - Are walls shared between adjacent cells?
2. What do bytes 0-2 and 6-7 represent?
3. What do the lower bits (0-4) encode?
4. How do we distinguish between different wall types (stone, secret, etc.)?

## Next Steps

1. Test the hypothesis by:
   - Creating walls in different configurations
   - Examining the resulting byte patterns
2. Map out all wall locations in the base map to validate the bit assignments
3. Decode the other 6 bytes in the cell structure
4. Look for door, trap, and special tile encodings

## Tools Created

- `tools/compare_newgame_files.py` - Byte-level file comparison
- `tools/analyze_wall_encoding.py` - Wall encoding analysis
- `tools/decode_map_structure.py` - Map structure hypothesis testing
- `tools/visualize_map_walls.py` - Map grid visualization
- `tools/examine_region.py` - Regional cell data examination
- `tools/decode_wall_bits.py` - Bit pattern analysis

## Summary

**CONFIRMED:** Wizardry 6 maps use **8 bytes per cell** with wall data stored in **bytes 3 and 5** as bit flags. The value **0x80** (bit 7 only) appears to mark walls, and is relatively rare in the map data. The exact bit-to-direction mapping needs further validation, but the structure is clear.
