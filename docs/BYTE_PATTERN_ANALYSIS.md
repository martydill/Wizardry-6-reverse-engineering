# Byte Pattern Analysis - Major Discovery!

## Latest Test: Horizontal Walls on Top Two Cells

### What Changed:
**Cell 30, Byte 5**: 0x00 → 0xA0 (bits 5, 7)

This added **2 new walls** from 2 new bits.

### Current State (8 walls total):

| Wall | Cell | Byte | Bit | Value | Type       | Source         |
|------|------|------|-----|-------|------------|----------------|
| 1    | 30   | 3    | 7   | 0x80  | ???        | Cross          |
| 2    | 30   | 3    | 5   | 0x20  | Horizontal | Cross          |
| 3    | 39   | 15   | 5   | 0x20  | Horizontal | Cross          |
| 4    | 39   | 17   | 5   | 0x20  | Horizontal | Cross          |
| 5    | 39   | 17   | 3   | 0x08  | Vertical   | Test: vert     |
| 6    | 30   | 1    | 5   | 0x20  | Horizontal | Test: horiz    |
| 7    | 30   | 5    | 5   | 0x20  | Horizontal | Test: top      |
| 8    | 30   | 5    | 7   | 0x80  | ???        | Test: top      |

## BREAKTHROUGH: Consecutive Odd Byte Pattern!

### Cell 30 Byte Usage:
```
Byte 1:  0x20 (bit 5)         ← First odd byte
Byte 3:  0xA0 (bits 5, 7)     ← Second odd byte
Byte 5:  0xA0 (bits 5, 7)     ← Third odd byte (NEW!)
         ^^^^
         SAME VALUE as Byte 3!
```

### Cell 39 Byte Usage:
```
Byte 15: 0x20 (bit 5)         ← First odd byte used
Byte 17: 0x28 (bits 3, 5)     ← Second odd byte used
```

### Pattern Observation:

**Consecutive odd bytes (1, 3, 5, ..., 15, 17, ...) are used sequentially!**

This suggests:
- Each odd byte represents a different wall position
- Bytes 1, 3, 5 might represent three different positions in one region
- Bytes 15, 17 might represent two different positions in another region

## Symmetry Discovery!

**Byte 3 and Byte 5 both = 0xA0**

This is NOT a coincidence! Possible explanations:

### Hypothesis 1: Mirror Positions
Bytes 3 and 5 might encode walls in mirrored/symmetrical positions:
- Byte 3: Left wall of a pair
- Byte 5: Right wall of a pair
- Both having same bits = symmetric configuration

### Hypothesis 2: Paired Walls
The user added walls to TWO cells (top two cells of cross).
- Byte 3 encodes walls for one cell
- Byte 5 encodes walls for the other cell
- Same value = same wall configuration on both cells

## Bit 7 Re-evaluation

**Critical Finding**: Bit 7 appears when user adds HORIZONTAL walls!

Bit 7 appearances:
1. Wall #1: Cross pattern (unknown which wall)
2. Wall #8: User explicitly added horizontal wall

**New Hypothesis**: Bit 7 might NOT be a separate wall type!

Possibilities:
- **Bit 7 = Horizontal wall in certain positions** (like bit 5)
- **Bit 7 = Wall property flag** (e.g., door, secret, locked)
- **Bits 5+7 together = Special horizontal wall** (e.g., wall with door)

## Byte Position Theory

### Theory: 10 ODD bytes = 10 wall positions

ODD bytes available: 1, 3, 5, 7, 9, 11, 13, 15, 17, 19 (10 total)

Possible mapping for a 2x2 cell block:
```
       ?     ?
    +-----+-----+
  ? |     |     | ?
    +-----+-----+
  ? |     |     | ?
    +-----+-----+
       ?     ?
```

A 2x2 block has:
- 4 outer edges (top, bottom, left, right)
- 2 internal edges (horizontal middle, vertical middle)
- 4 corners

But we have 10 bytes available, more than enough!

### Bytes Used So Far:
- **Cell 30**: Bytes 1, 3, 5
- **Cell 39**: Bytes 15, 17

**Why the gap?** (bytes 7, 9, 11, 13 not used yet)

This suggests cells 30 and 39 encode **different regions** of the map!

## Cell Assignment Theory

### Theory: Different cells encode different map regions

- **Cell 30** (Col 1, Row 10): Encodes walls for one region (bytes 1,3,5,...)
- **Cell 39** (Col 1, Row 19): Encodes walls for another region (bytes 15,17,...)

The 20x20 map might be divided into regions, and each "cell" in the file
is actually a REGION DESCRIPTOR, not a game cell!

### Evidence:
1. Only 2 file cells used (30, 39) for walls in a 2x2 game area
2. Each file cell uses consecutive odd bytes
3. File cells are far apart (row 10 vs row 19, 9 rows difference)

## Remaining Questions

### 1. Byte-to-Position Mapping
Which byte represents which wall position?
- Need systematic test: add walls to all edges of 2x2 block
- Map each wall to its (cell, byte, bit) address

### 2. Bit 7 True Meaning
- Is it a wall type or a wall property?
- Why does it appear with bit 5 (both set to 0xA0)?

### 3. Cell-to-Region Formula
How do file cells (30, 39) map to game regions?
- Editor shows: Quadrant 5, cells (6,7)-(7,6)
- File shows: Cells 30, 39
- Formula needed!

### 4. Why Bytes 3 and 5 Have Same Value?
0xA0 appears in both bytes. Is this:
- Symmetry in the map?
- Identical wall configurations?
- Something else?

## Next Test Suggestions

### Test A: Complete the 2x2 Block
Add walls to ALL edges of the 2x2 block:
- All 4 outer edges
- Both inner cross walls
- Map each wall to its byte

### Test B: Different 2x2 Block
Create a similar pattern in a different map location:
- See which cells (not 30, 39) are used
- Derive the cell assignment formula

### Test C: Remove Walls
Delete specific walls to confirm:
- Which bit corresponds to which actual wall
- Verify our bit 3/5/7 hypothesis

### Test D: Single Wall Each Edge
Add exactly one wall to each of the 4 outer edges:
- Top edge
- Bottom edge
- Left edge
- Right edge
- See which bytes and bits each uses
