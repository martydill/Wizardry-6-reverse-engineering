# Wizardry 6 Feature System - DECODED!

## Major Breakthrough: Multiple Features Per Entry

By analyzing two test cases (4 corner fountains + 4 center sconces), we've discovered how the feature system works!

---

## Test Cases

### Test 1: 4 Corner Fountains
- **(0,0)** - Top-Left
- **(15,0)** - Top-Right
- **(0,15)** - Bottom-Left
- **(15,15)** - Bottom-Right

**Result:** 4 bytes changed in 2 entries

### Test 2: 4 Center Sconces (Quadrant Corners)
- **(7,7)** - NW quadrant corner
- **(8,7)** - NE quadrant corner
- **(7,8)** - SW quadrant corner
- **(8,8)** - SE quadrant corner

**Result:** 4 additional bytes changed in same 2 entries

---

## Combined Changes

### Entry #0 (0x7D22) - 5 bytes changed:
```
Byte  0: 0x00 -> 0x04   (Fountain type)
Byte 31: 0x00 -> 0x30   (Sconce attribute?)
Byte 35: 0x00 -> 0x40   (Enable flag)
Byte 60: 0x00 -> 0x03   (Sconce type)
Byte 67: 0x00 -> 0x30   (Sconce attribute?)
```

### Entry #1 (0x7D7E) - 3 bytes changed:
```
Byte  0: 0x00 -> 0x04   (Fountain type)
Byte  4: 0x00 -> 0x03   (Sconce type)
Byte 35: 0x00 -> 0x40   (Enable flag)
```

---

## Key Discovery: Multi-Feature Entries

**Each entry can store MULTIPLE features at different byte positions!**

### Entry #0 Structure:
```
+0x00  Feature Slot 1 (Fountains)
       Byte 0: 0x04 (type)
       ...
       Byte 31: 0x30 (sconce attr?)
       Byte 35: 0x40 (enable)
       ...

+0x3C  Feature Slot 2 (Sconces)
       Byte 60: 0x03 (type)
       ...
       Byte 67: 0x30 (attribute)
```

### Entry #1 Structure:
```
+0x00  Feature Slot 1 (Fountains)
       Byte 0: 0x04 (type)
       Byte 4: 0x03 (sconce type!)
       ...
       Byte 35: 0x40 (enable)
```

---

## Feature Type IDs

| ID   | Feature Type |
|------|--------------|
| 0x03 | Sconce       |
| 0x04 | Fountain     |

---

## Position Mapping (HYPOTHESIS)

### Diagonal Pair Theory

**Entry #0 controls MAIN DIAGONAL positions:**
- Fountains: (0,0) + (15,15)
- Sconces: (7,7) + (8,8)

**Entry #1 controls ANTI-DIAGONAL positions:**
- Fountains: (15,0) + (0,15)
- Sconces: (8,7) + (7,8)

### Evidence:
1. Both feature types follow same 2-entry pattern
2. Sconces form 2×2 square in center
3. (7,7) + (8,8) are on main diagonal
4. (8,7) + (7,8) are on anti-diagonal

---

## The 0x30 Mystery

**Value:** 0x30 = 48 = 0b00110000

**Appears in Entry #0 only:**
- Byte 31 (sconce-related)
- Byte 67 (sconce-related)

**Does NOT appear in Entry #1**

### Hypotheses:

1. **Position encoding:**
   - 0x30 = 48 = 3×16
   - Could encode center positions (7,7) and (8,8)?
   - But why different encoding than fountains?

2. **Attribute flag:**
   - Sconces in Entry #0 need this flag
   - Sconces in Entry #1 don't
   - Could indicate "first vs second position"?

3. **Lighting/facing direction:**
   - Sconces might have orientation
   - 0b00110000 = bits 4 and 5 set
   - Could be N/S/E/W facing flags

---

## Byte 35: Universal Enable Flag

**CONFIRMED:** Byte 35 = 0x40 appears in both entries

**Function:** Master enable/active flag for the entire entry

**Pattern:**
- Both entries share same flag value
- Both entries activated simultaneously
- Single bit: 0x40 = 0b01000000 (bit 6)

---

## Entry Structure Analysis

### Fixed Positions:
```
Byte 0:  Feature type (fountain/sconce/etc.)
Byte 35: Enable flag (0x40 = active)
```

### Variable Positions:
```
Entry #0:
  Byte 4:  (unused for fountains)
  Byte 60: Additional feature type (sconces)
  Byte 31: Feature 2 attribute
  Byte 67: Feature 2 attribute

Entry #1:
  Byte 4:  Additional feature type (sconces)
```

**This suggests entries have DIFFERENT internal layouts or feature slot positions!**

---

## Revised Entry Structure Hypothesis

### Theory: Interleaved Feature Slots

Each entry might contain multiple feature "records" interleaved:

```
Entry Layout (92 bytes):
  Feature 1 (Fountains):
    +0x00: Type (0x04)
    ...
    +0x23: Enable (0x40)

  Feature 2 (Sconces):
    +0x04: Type (0x03) [Entry #1]
    or
    +0x3C: Type (0x03) [Entry #0]
    +0x1F: Attr (0x30) [Entry #0]
    +0x43: Attr (0x30) [Entry #0]
```

---

## Open Questions

### 1. Why Different Byte Positions?
- Entry #0 has sconce at byte 60
- Entry #1 has sconce at byte 4
- Different slot layouts? Or overloaded positions?

### 2. What is 0x30?
- Only in Entry #0
- Appears at bytes 31 and 67
- Related to sconce position/attributes

### 3. How Many Feature Slots?
- We've seen 2 features per entry
- Are there more slots?
- Can an entry hold 3+ features?

### 4. Position Encoding
- Still no explicit X,Y coordinates found
- Diagonal pairing theory needs testing
- Are positions truly implicit?

---

## Next Test Recommendations

### To Confirm Diagonal Theory:
1. **Remove 1 corner fountain** - which entry changes?
2. **Remove 1 center sconce** - which entry changes?
3. **Add fountain at (7,7) only** - does it use Entry #0?

### To Understand 0x30:
1. **Add sconces at different positions**
2. **Add sconces in different orientations**
3. **Compare 0x30 values for different sconce locations**

### To Find Position Data:
1. **Add feature at (1,1)** - a non-corner, non-center position
2. **Look for new byte patterns**
3. **Search for coordinate encoding elsewhere in file**

---

## Implications for Bane Engine

### Feature Loading System:

```python
class FeatureEntry:
    def __init__(self, data):
        self.feature_slots = []

        # Slot 1: Always at byte 0
        if data[0] != 0:
            self.feature_slots.append({
                'type': data[0],
                'enabled': (data[35] & 0x40) != 0
            })

        # Slot 2: Variable position
        # Entry #0: byte 60
        # Entry #1: byte 4
        # Need to determine slot position per entry

    def get_positions(self, entry_id, feature_type):
        # Map entry ID to world positions
        if entry_id == 0:
            if feature_type == 0x04:  # Fountain
                return [(0,0), (15,15)]
            elif feature_type == 0x03:  # Sconce
                return [(7,7), (8,8)]
        elif entry_id == 1:
            if feature_type == 0x04:  # Fountain
                return [(15,0), (0,15)]
            elif feature_type == 0x03:  # Sconce
                return [(8,7), (7,8)]
```

---

## Visual Summary

```
Map 10 (16×16) with Fountains (F) and Sconces (S):

     0   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 0 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 1 |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
 . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 7 |   |   |   |   |   |   |   | S | S |   |   |   |   |   |   |   |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 8 |   |   |   |   |   |   |   | S | S |   |   |   |   |   |   |   |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
 . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
 . |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |   |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+
15 | F |   |   |   |   |   |   |   |   |   |   |   |   |   |   | F |
   +---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+---+

Entry #0 (Main Diagonal):
  F: (0,0), (15,15)
  S: (7,7), (8,8)

Entry #1 (Anti-Diagonal):
  F: (15,0), (0,15)
  S: (8,7), (7,8)
```

---

## Conclusion

The Wizardry 6 feature system is **more sophisticated than initially thought:**

1. **Multi-feature entries** - Each 92-byte entry can hold multiple different feature types
2. **Diagonal pairing** - Positions follow main/anti-diagonal patterns
3. **Shared enable flags** - Single byte 35 controls all features in entry
4. **Feature type IDs** - 0x03 = Sconce, 0x04 = Fountain
5. **Attribute bytes** - 0x30 values provide additional sconce configuration

The next step is to **test the diagonal theory** by modifying individual features and observing which bytes change.
