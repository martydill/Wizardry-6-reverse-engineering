# Wizardry 6 - Fountain Discovery (Map 10)

## BREAKTHROUGH: Fountain Marker Found!

**Byte 18 = 0xA0** marks fountain positions!

## The 4 Fountains

| Cell | File Col | File Row | Game Position | Quadrant |
|------|----------|----------|---------------|----------|
| 4    | 0        | 4        | ?             | Quad 8?  |
| 200  | 12       | 8        | ?             | Quad 9?  |
| 237  | 14       | 13       | ?             | Quad 10? |
| 255  | 15       | 15       | ?             | Quad 11? |

## Expected Fountain Positions (from editor)

- **Bottom-left**: Quad 8 (0,0) → global (0, 0)
- **Bottom-right**: Quad 9 (7,0) → global (15, 0)
- **Top-left**: Quad 10 (0,7) → global (0, 15)
- **Top-right**: Quad 11 (7,7) → global (15, 15)

## Key Finding: Quadrant-Based Storage

The file columns 0, 12, 14, 15 for the 4 fountains suggests the map uses **quadrant-based storage** rather than simple linear column mapping.

### Hypothesis: Quadrant Storage Pattern

For a 16×16 map divided into 4 quadrants (8×8 each):

```
Map layout:
┌─────────┬─────────┐
│ Quad 10 │ Quad 11 │  Y: 8-15
│  (0-7,  │  (8-15, │
│   8-15) │   8-15) │
├─────────┼─────────┤
│ Quad 8  │ Quad 9  │  Y: 0-7
│  (0-7,  │  (8-15, │
│   0-7)  │   0-7)  │
└─────────┴─────────┘
  X: 0-7    X: 8-15
```

Possible file organization:
- Each quadrant stored in specific file columns?
- File row encodes position within quadrant?
- Not a simple X→file_col, Y→file_row mapping!

## Cell Data

### Cell 4 (Fountain 1)
- **File position**: col=0, row=4
- **Even bytes**: 88 88 88 2A A8 A8 08 22 02 A0
- **Byte 18**: 0xA0 ← Fountain marker!
- **Also has**: Byte 0 = 0x88 (unique to cells 0 and 4)

### Cell 200 (Fountain 2)
- **File position**: col=12, row=8
- **Even bytes**: AA 8A AA 20 AA 28 0A 0A 0A A0
- **Byte 18**: 0xA0 ← Fountain marker!

### Cell 237 (Fountain 3)
- **File position**: col=14, row=13
- **Even bytes**: 00 00 00 00 00 00 00 00 C8 A0
- **Byte 18**: 0xA0 ← Fountain marker!
- **Mostly zeros** except byte 16 (0xC8) and byte 18 (0xA0)

### Cell 255 (Fountain 4)
- **File position**: col=15, row=15
- **Even bytes**: 00 00 00 00 00 80 80 80 A0 A0
- **Byte 18**: 0xA0 ← Fountain marker!

## Implications for Coordinate Mapping

The file→game coordinate mapping is **NOT** simple:
- ❌ file_col ≠ game_col (directly)
- ❌ file_row ≠ game_row (directly)
- ✅ Quadrant-based organization (likely)

### Next Steps to Decode Mapping:

1. **Map each fountain cell to its quadrant**
   - Cell 4 → which quadrant?
   - Cell 200 → which quadrant?
   - Cell 237 → which quadrant?
   - Cell 255 → which quadrant?

2. **Find the formula**
   - How does (file_col, file_row) → (game_col, game_row)?
   - How are quadrants distributed across file columns?

3. **Test with more features**
   - Add objects at known positions
   - Track which cells change
   - Build complete mapping table

## Other Discoveries

### Byte 0 = 0x88
- Appears in cells 0 and 4 only
- Cell 4 is a fountain
- Cell 0 also has high data activity
- Might indicate special floor type?

### Byte 18 Usage
- **ONLY** 4 cells in entire map have byte 18 = 0xA0
- Perfect match for 4 fountains!
- High confidence this is the fountain marker

---

**Status**: Fountain marker CONFIRMED (byte 18 = 0xA0)
**Confidence**: 95%+ - exactly 4 occurrences matching 4 fountains
**Remaining**: Decode file position → game position formula
**Last Updated**: 2026-02-12
