"""
wizardry_charcreate.py
======================
Python reimplementation of the Wizardry for Windows character-creation logic.

All data tables are loaded DIRECTLY from the wpcmk.ovr binary overlay at
runtime — nothing is hard-coded except the structural constants (field
widths, entry counts) that are intrinsic to the data format itself.

Usage
-----
    # Interactive session:
    python wizardry_charcreate.py wpcmk.ovr

    # Demo / batch test:
    python wizardry_charcreate.py wpcmk.ovr --demo

    # Dump raw extracted tables:
    python wizardry_charcreate.py wpcmk.ovr --dump

    # API usage:
    from wizardry_charcreate import load_tables, CharacterCreator

Binary format (wpcmk.ovr)
--------------------------
The character-creation data lives in a contiguous segment anchored by the
null-terminated string "PCFILE.DBS" followed by 3-4 bytes of padding.

From that anchor the loader walks through five sequential tables:

  Table 1 – Class-restriction table
    • 14 groups × 4 null-terminated strings of '0'/'1' characters
    • Field widths: 10, 7, 5, 8 bits respectively
    • Field 1 (10-bit): class-availability bitmask
                        bit 9=Fighter … bit 0=Valkyrie
    • Field 2 ( 7-bit): alignment/gender flags (partially decoded)
    • Field 3 ( 5-bit): always "00000" — padding / unused
    • Field 4 ( 8-bit): alignment restriction flags
                        bits 7-5 → Good, Neutral, Evil permitted
    • Terminated by sentinel string "***\\0"

  Table 2 – Race stat-bonus table (male characters)
    • 14 entries × 8 uppercase letters (A–P), then \\0
    • Value = ord(letter) – ord('A')  →  range 0–15
    • Columns: STR  IQ  PIE  VIT  DEX  SPD  LUK  <unused>

  Table 3 – Race stat-bonus table (female characters)
    • Identical layout to Table 2; in this binary the values are the same

  Table 4 – Class base-stat floor table
    • 11 entries × 8 uppercase letters, then \\0
    • Rows correspond to Fighter, Mage, Priest, Thief, Bishop,
      Samurai, Lord, Ninja, Alchemist, Valkyrie, plus one extra row

  Table 5 – Class × Race AP-cost modifier table
    • 10 entries × 14 uppercase letters, then \\0
    • mod ≤ 2 (letters A/B/C) means this is a "primary" stat for
      that class/race combo → costs 1 bonus pt per +1
    • mod >  2 → costs 2 bonus pts per +1
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURAL CONSTANTS
# These reflect the on-disk format and must not be changed unless the binary
# format itself changes.
# ─────────────────────────────────────────────────────────────────────────────

NUM_RACES       = 14    # rows in the race tables
NUM_CLASSES     = 10    # columns in the class mask / rows in class tables
NUM_STATS       =  7    # STR IQ PIE VIT DEX SPD LUK  (8th byte unused)
CLASS_STAT_ROWS = 11    # Table 4 has 10 classes + 1 extra row

FIELD_LENGTHS   = (10, 7, 5, 8)   # bit-widths of the 4 binary fields per race

ANCHOR_SIGNATURE = b'PCFILE.DBS\x00'
TABLE1_SENTINEL  = b'***\x00'

LETTER_BASE = ord('A')   # 'A'→0, 'B'→1, …, 'P'→15

STAT_NAMES = ("STR", "IQ", "PIE", "VIT", "DEX", "SPD", "LUK")

CLASS_NAMES = (
    "Fighter", "Mage", "Priest", "Thief", "Bishop",
    "Samurai", "Lord", "Ninja", "Alchemist", "Valkyrie",
)

# Default race names (label only; extraction never depends on them)
RACE_NAMES = (
    "Human", "Elf", "Dwarf", "Gnome", "Hobbit",
    "Faerie", "Pixie", "Draken", "Lizardman", "Felpurr",
    "Rawulf", "Mook", "Trang", "Drakon",
)

# Bits 7, 6, 5 of Field 4 (MSB-first) → Good, Neutral, Evil
_ALIGN_BIT_POSITIONS = (0, 1, 2)   # index into the 8-char binary string

# HP base by class index 0-9
_HP_BASE = (10, 4, 8, 6, 6, 9, 10, 8, 5, 9)

# Bonus-point pool: 3d6, re-rolled until >= minimum
_POOL_DICE  = 3
_POOL_SIDES = 6
_POOL_MIN   = 5


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLE ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class Alignment(IntEnum):
    GOOD    = 0
    NEUTRAL = 1
    EVIL    = 2

class Gender(IntEnum):
    MALE   = 0
    FEMALE = 1


# ─────────────────────────────────────────────────────────────────────────────
# PARSED TABLE CONTAINER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CreationTables:
    """
    All character-creation data parsed from wpcmk.ovr.

    Every field is populated by extract_tables(); callers should treat this
    as read-only after construction.
    """

    # ── raw extracted fields ──────────────────────────────────────────────────

    # class_mask[race_idx]  → int  10-bit; bit N set = class N available
    class_mask:              list[int]         # len = NUM_RACES

    # field2[race_idx]  → int  7-bit
    field2:                  list[int]         # len = NUM_RACES

    # field4[race_idx]  → int  8-bit  (alignment flags)
    field4:                  list[int]         # len = NUM_RACES

    # race_stat_min_male[race_idx]     → list[int]  len = NUM_STATS  (stat minimums, not additive bonuses)
    race_stat_bonus_male:    list[list[int]]   # NUM_RACES × NUM_STATS

    # race_stat_min_female[race_idx]   → list[int]  len = NUM_STATS  (stat minimums, not additive bonuses)
    race_stat_bonus_female:  list[list[int]]   # NUM_RACES × NUM_STATS

    # class_base_stats[class_idx] → list[int]  len = NUM_STATS
    class_base_stats:        list[list[int]]   # CLASS_STAT_ROWS × NUM_STATS

    # class_race_mod[class_idx][race_idx] → int
    class_race_mod:          list[list[int]]   # NUM_CLASSES × NUM_RACES

    # portrait_files: WPORT1.EGA etc. found after the data tables
    portrait_files:          list[str]

    # ── derived helpers ───────────────────────────────────────────────────────

    def allowed_class_indices(self, race_idx: int) -> list[int]:
        """Return sorted list of class indices (0=Fighter…9=Valkyrie) for this race."""
        mask = self.class_mask[race_idx]
        return [i for i in range(NUM_CLASSES)
                if (mask >> (NUM_CLASSES - 1 - i)) & 1]

    def allowed_alignments(self, race_idx: int) -> list[Alignment]:
        """
        Decode alignment restrictions from Field 4.
        Bits at positions 0,1,2 of the 8-bit value (MSB-first) correspond to
        Good, Neutral, Evil.  '1' = permitted.
        """
        bits = f"{self.field4[race_idx]:08b}"
        result = [align
                  for bit_pos, align in zip(_ALIGN_BIT_POSITIONS, Alignment)
                  if bits[bit_pos] == '1']
        return result or list(Alignment)   # fallback: all alignments permitted

    def stat_point_cost(self, class_idx: int, race_idx: int) -> int:
        """
        Bonus-point cost per +1 for any stat for this class/race combination.

        The class×race modifier table (Table 5) encodes a weight per combo.
        Weight ≤ 2 (letters A/B/C) → primary stat → 1 pt.
        Weight > 2                  → secondary    → 2 pts.

        Note: the original binary applies this as a single cost for the whole
        combo rather than per individual stat, so all stats cost the same for
        a given class/race pair.
        """
        if class_idx < len(self.class_race_mod):
            row = self.class_race_mod[class_idx]
            val = row[race_idx] if race_idx < len(row) else 2
            return 1 if val <= 2 else 2
        return 2


# ─────────────────────────────────────────────────────────────────────────────
# BINARY EXTRACTOR
# ─────────────────────────────────────────────────────────────────────────────

def _read_cstring(data: bytes, pos: int) -> tuple[bytes, int]:
    """Read a null-terminated byte string at pos.  Returns (string, next_pos)."""
    end = data.index(b'\x00', pos)
    return data[pos:end], end + 1


def _skip_nulls_and_spaces(data: bytes, pos: int) -> int:
    """Advance pos past any 0x00 or 0x20 bytes."""
    while pos < len(data) and data[pos] in (0x00, 0x20):
        pos += 1
    return pos


def _parse_binary_string(raw: bytes, expected_len: int, label: str) -> int:
    """
    Decode a binary string like b'1111111110' → integer bitmask.
    Raises ValueError on wrong length or non-binary characters.
    """
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError(f"{label}: cannot decode {raw!r} as ASCII")

    if len(text) != expected_len:
        raise ValueError(
            f"{label}: expected {expected_len}-char binary string, "
            f"got {len(text)!r}: {text!r}"
        )
    if not all(c in '01' for c in text):
        raise ValueError(f"{label}: non-binary characters in {text!r}")

    return int(text, 2)


def _parse_letter_string(raw: bytes, min_len: int, label: str) -> list[int]:
    """
    Decode a letter-encoded string like b'MAAAAAAA' → list of ints.
    Returns exactly min_len values (truncates if longer).
    Raises ValueError on non-uppercase or too-short strings.
    """
    try:
        text = raw.decode('ascii')
    except UnicodeDecodeError:
        raise ValueError(f"{label}: cannot decode {raw!r} as ASCII")

    if len(text) < min_len:
        raise ValueError(
            f"{label}: expected >= {min_len} letters, got {len(text)}: {text!r}"
        )
    if not all('A' <= c <= 'Z' for c in text):
        raise ValueError(f"{label}: non-uppercase chars in {text!r}")

    return [ord(c) - LETTER_BASE for c in text[:min_len]]


def _read_next_nonempty_cstring(data: bytes, pos: int) -> tuple[bytes, int]:
    """Read cstrings until a non-empty one is found (skips padding nulls)."""
    raw = b''
    while raw == b'' and pos < len(data):
        raw, pos = _read_cstring(data, pos)
    return raw, pos


def extract_tables(data: bytes) -> CreationTables:
    """
    Parse all character-creation tables from raw wpcmk.ovr bytes.

    Parameters
    ----------
    data : raw bytes of wpcmk.ovr

    Returns
    -------
    CreationTables

    Raises
    ------
    ValueError  if the anchor is missing or a table entry is malformed
    """

    # ── 1. Find anchor ────────────────────────────────────────────────────────
    anchor = data.find(ANCHOR_SIGNATURE)
    if anchor == -1:
        raise ValueError(
            f"Anchor {ANCHOR_SIGNATURE!r} not found. "
            "Is this really wpcmk.ovr?"
        )

    pos = anchor + len(ANCHOR_SIGNATURE)
    pos = _skip_nulls_and_spaces(data, pos)

    # ── 2. Table 1: class-restriction binary strings ──────────────────────────
    # 14 race groups × 4 binary-string fields each.
    # Stops at sentinel "***\0" or after NUM_RACES groups.
    class_mask_list: list[int] = []
    field2_list:     list[int] = []
    field3_list:     list[int] = []
    field4_list:     list[int] = []

    for race_idx in range(NUM_RACES):
        # Guard against early sentinel
        if data[pos:pos + len(TABLE1_SENTINEL)] == TABLE1_SENTINEL:
            raise ValueError(
                f"Sentinel found after only {race_idx} races "
                f"(expected {NUM_RACES})"
            )

        group_ints: list[int] = []
        for field_idx, expected_len in enumerate(FIELD_LENGTHS):
            raw, pos = _read_next_nonempty_cstring(data, pos)
            label = f"Table1 race={race_idx} field={field_idx+1}"
            group_ints.append(_parse_binary_string(raw, expected_len, label))

        class_mask_list.append(group_ints[0])
        field2_list.append(group_ints[1])
        field3_list.append(group_ints[2])
        field4_list.append(group_ints[3])

    # Consume sentinel if present
    if data[pos:pos + len(TABLE1_SENTINEL)] == TABLE1_SENTINEL:
        pos += len(TABLE1_SENTINEL)

    pos = _skip_nulls_and_spaces(data, pos)

    # ── 3. Helper: read a letter-encoded table ────────────────────────────────
    def _read_letter_table(
        pos: int,
        num_rows: int,
        cols: int,
        table_name: str,
    ) -> tuple[list[list[int]], int]:
        rows: list[list[int]] = []
        for row_idx in range(num_rows):
            raw, pos = _read_next_nonempty_cstring(data, pos)
            label = f"{table_name}[{row_idx}]"
            rows.append(_parse_letter_string(raw, cols, label))
        return rows, pos

    # ── 4. Table 2: race stat bonuses (male) ──────────────────────────────────
    # NUM_RACES rows, each NUM_STATS+1 letters (last column unused → take :NUM_STATS)
    bonus_male, pos = _read_letter_table(pos, NUM_RACES, NUM_STATS, "Table2_male")

    # ── 5. Table 3: race stat bonuses (female, duplicate) ─────────────────────
    bonus_female, pos = _read_letter_table(pos, NUM_RACES, NUM_STATS, "Table3_female")

    # ── 6. Table 4: class base-stat floors ────────────────────────────────────
    class_base, pos = _read_letter_table(pos, CLASS_STAT_ROWS, NUM_STATS, "Table4_classbase")

    # ── 7. Table 5: class × race modifier ─────────────────────────────────────
    # NUM_CLASSES rows, each NUM_RACES letters long.
    class_race_mod, pos = _read_letter_table(pos, NUM_CLASSES, NUM_RACES, "Table5_mod")

    # ── 8. Portrait filenames (epilogue) ──────────────────────────────────────
    portrait_files: list[str] = []
    while pos < len(data):
        try:
            raw, pos = _read_cstring(data, pos)
        except ValueError:
            break
        if not raw:
            continue
        try:
            s = raw.decode('ascii')
        except UnicodeDecodeError:
            break
        if s.startswith('WPORT') and '.' in s:
            portrait_files.append(s)
        elif b'PCFILE' in raw:
            break   # second PCFILE.DBS block = we've gone too far

    return CreationTables(
        class_mask=class_mask_list,
        field2=field2_list,
        field4=field4_list,
        race_stat_bonus_male=bonus_male,
        race_stat_bonus_female=bonus_female,
        class_base_stats=class_base,
        class_race_mod=class_race_mod,
        portrait_files=portrait_files,
    )


def load_tables(ovr_path: str | Path) -> CreationTables:
    """
    Load and parse character-creation tables from a wpcmk.ovr file.

    Parameters
    ----------
    ovr_path : path-like pointing to wpcmk.ovr

    Returns
    -------
    CreationTables

    Raises
    ------
    FileNotFoundError  if the file does not exist
    ValueError         if the binary format is not recognised
    """
    path = Path(ovr_path)
    if not path.exists():
        raise FileNotFoundError(f"Overlay file not found: {path}")
    return extract_tables(path.read_bytes())


# ─────────────────────────────────────────────────────────────────────────────
# CHARACTER DATACLASS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Character:
    name:       str
    race_idx:   int
    class_idx:  int
    gender:     Gender
    alignment:  Alignment
    stats:      list[int]         # STR IQ PIE VIT DEX SPD LUK
    bonus_pool: int
    _tables:    CreationTables    # back-reference for derived properties

    @property
    def race_name(self) -> str:
        return RACE_NAMES[self.race_idx] if self.race_idx < len(RACE_NAMES) else f"Race{self.race_idx}"

    @property
    def class_name(self) -> str:
        return CLASS_NAMES[self.class_idx] if self.class_idx < NUM_CLASSES else f"Class{self.class_idx}"

    @property
    def hp(self) -> int:
        base    = _HP_BASE[self.class_idx] if self.class_idx < len(_HP_BASE) else 6
        vit_mod = (self.stats[3] - 10) // 2   # VIT is index 3
        return max(1, base + vit_mod)

    @property
    def mp(self) -> int:
        # Spellcasting classes: Mage(1), Priest(2), Bishop(4), Samurai(5),
        #                       Lord(6), Ninja(7), Alchemist(8), Valkyrie(9)
        if self.class_idx not in {1, 2, 4, 5, 6, 7, 8, 9}:
            return 0
        return max(0, (self.stats[1] + self.stats[2]) // 4)

    def stat_dict(self) -> dict[str, int]:
        return dict(zip(STAT_NAMES, self.stats))

    def __str__(self) -> str:
        stat_str = "  ".join(f"{n}:{v:>3}" for n, v in zip(STAT_NAMES, self.stats))
        return (
            f"{'─'*64}\n"
            f"  {self.name}  "
            f"[{self.race_name} {self.class_name}  "
            f"{self.gender.name}  {self.alignment.name}]\n"
            f"  {stat_str}\n"
            f"  HP:{self.hp:>3}   MP:{self.mp:>3}   "
            f"Bonus pts remaining: {self.bonus_pool}\n"
            f"{'─'*64}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CHARACTER CREATOR
# ─────────────────────────────────────────────────────────────────────────────

def _roll_bonus_pool() -> int:
    """Roll 3d6 re-rolling until >= _POOL_MIN."""
    while True:
        total = sum(random.randint(1, _POOL_SIDES) for _ in range(_POOL_DICE))
        if total >= _POOL_MIN:
            return total


class CharacterCreator:
    """
    Drives character creation using tables extracted live from wpcmk.ovr.

    Parameters
    ----------
    tables : CreationTables  (from load_tables())
    """

    def __init__(self, tables: CreationTables) -> None:
        self.t = tables

    # ── eligibility ───────────────────────────────────────────────────────────

    def available_class_indices(self, race_idx: int) -> list[int]:
        return self.t.allowed_class_indices(race_idx)

    def can_be_class(self, race_idx: int, class_idx: int) -> bool:
        return class_idx in self.t.allowed_class_indices(race_idx)

    def available_alignments(self, race_idx: int) -> list[Alignment]:
        return self.t.allowed_alignments(race_idx)

    def can_be_alignment(self, race_idx: int, alignment: Alignment) -> bool:
        return alignment in self.t.allowed_alignments(race_idx)

    # ── stat generation ───────────────────────────────────────────────────────

    def base_stats(self, race_idx: int, class_idx: int, gender: Gender) -> list[int]:
        """
        Compute guaranteed base stats for a race/class/gender combination.

        Algorithm (corrected from binary analysis):
          - Table 4 = CLASS BASELINE: the rolled starting value per stat for
            a character of that class.
          - Table 2/3 = RACE STAT MINIMUMS: the floor each stat must meet for
            that race, regardless of class choice.
          - Final base stat = max(class_baseline, race_minimum) per stat.

        Example: Human Fighter STR = max(class=9, race_min=12) = 12.
        The race table does NOT add to stats; it only raises a stat when the
        class baseline falls below the race's required minimum. Adding them
        together (the old code) would give an incorrect STR of 21.
        """
        # Table 4: class baseline values
        if class_idx < len(self.t.class_base_stats):
            class_baseline = self.t.class_base_stats[class_idx]
        else:
            class_baseline = [8] * NUM_STATS

        # Table 2 (male) / Table 3 (female): race stat minimums
        if gender == Gender.FEMALE:
            race_minimums = self.t.race_stat_bonus_female[race_idx]
        else:
            race_minimums = self.t.race_stat_bonus_male[race_idx]

        # Each stat is the higher of class baseline and race minimum
        return [max(c, r) for c, r in zip(class_baseline, race_minimums)]

    def roll_stats(
        self, race_idx: int, class_idx: int, gender: Gender
    ) -> tuple[list[int], int]:
        """Return (base_stats, bonus_pool)."""
        return self.base_stats(race_idx, class_idx, gender), _roll_bonus_pool()

    # ── bonus point spending ──────────────────────────────────────────────────

    def spend_bonus(
        self, char: Character, stat_idx: int, amount: int = 1
    ) -> bool:
        """
        Spend bonus points to raise char.stats[stat_idx] by *amount*.

        Point cost per +1 is determined by the class×race modifier table
        (Table 5): ≤ 2 → 1 pt ("primary"), > 2 → 2 pts ("secondary").

        Returns True on success, False if the pool is too small or
        stat_idx is out of range.
        """
        if not (0 <= stat_idx < NUM_STATS):
            return False
        cost_each  = self.t.stat_point_cost(char.class_idx, char.race_idx)
        total_cost = cost_each * amount
        if char.bonus_pool < total_cost:
            return False
        char.stats[stat_idx] += amount
        char.bonus_pool       -= total_cost
        return True

    def auto_spend_bonus(self, char: Character) -> None:
        """Spend all remaining bonus points randomly into affordable stats."""
        while char.bonus_pool > 0:
            cost = self.t.stat_point_cost(char.class_idx, char.race_idx)
            if char.bonus_pool < cost:
                break
            self.spend_bonus(char, random.randrange(NUM_STATS))

    # ── full creation ──────────────────────────────────────────────────────────

    def create(
        self,
        name:       str,
        race_idx:   int,
        class_idx:  int,
        gender:     Gender,
        alignment:  Alignment,
        auto_spend: bool = False,
    ) -> Character:
        """
        Create a fully initialised Character, validating eligibility first.

        Raises ValueError if the race/class or race/alignment combination is
        forbidden by the tables extracted from the binary.
        """
        race_lbl  = RACE_NAMES[race_idx]   if race_idx  < len(RACE_NAMES)  else str(race_idx)
        class_lbl = CLASS_NAMES[class_idx] if class_idx < len(CLASS_NAMES) else str(class_idx)

        if not self.can_be_class(race_idx, class_idx):
            allowed = [CLASS_NAMES[i] for i in self.available_class_indices(race_idx)]
            raise ValueError(
                f"{race_lbl} cannot be a {class_lbl}. "
                f"Allowed classes: {', '.join(allowed)}"
            )
        if not self.can_be_alignment(race_idx, alignment):
            allowed = [a.name for a in self.available_alignments(race_idx)]
            raise ValueError(
                f"{race_lbl} cannot be {alignment.name}. "
                f"Allowed alignments: {', '.join(allowed)}"
            )

        stats, pool = self.roll_stats(race_idx, class_idx, gender)
        char = Character(
            name=name,
            race_idx=race_idx,
            class_idx=class_idx,
            gender=gender,
            alignment=alignment,
            stats=stats,
            bonus_pool=pool,
            _tables=self.t,
        )
        if auto_spend:
            self.auto_spend_bonus(char)
        return char

    def reroll(self, char: Character) -> None:
        """Re-roll stats and bonus pool in place (player pressed 'Reroll')."""
        stats, pool     = self.roll_stats(char.race_idx, char.class_idx, char.gender)
        char.stats      = stats
        char.bonus_pool = pool


# ─────────────────────────────────────────────────────────────────────────────
# TABLE DUMP  (debug / verification)
# ─────────────────────────────────────────────────────────────────────────────

def dump_tables(t: CreationTables) -> None:
    """Pretty-print all extracted tables to stdout."""

    div = "═" * 72
    print(f"\n{div}\n  EXTRACTED CHARACTER CREATION TABLES\n{div}")

    # Class restriction matrix
    print("\n── Table 1: Class Restriction Matrix " + "─"*35)
    hdr = f"  {'Race':<14}" + "".join(f"{n[:4]:>6}" for n in CLASS_NAMES)
    print(hdr)
    print("  " + "─"*(14 + 6*NUM_CLASSES))
    for ri in range(NUM_RACES):
        allowed = set(t.allowed_class_indices(ri))
        row = f"  {RACE_NAMES[ri]:<14}"
        for ci in range(NUM_CLASSES):
            row += "   YES" if ci in allowed else "    ─ "
        print(row)

    # Alignment restrictions
    print("\n── Table 1 Field 4: Alignment Restrictions " + "─"*28)
    for ri in range(NUM_RACES):
        aligns = ", ".join(a.name for a in t.allowed_alignments(ri))
        f4_bits = f"{t.field4[ri]:08b}"
        print(f"  {RACE_NAMES[ri]:<14}  f4={f4_bits}  →  {aligns}")

    # Race stat bonuses
    print("\n── Table 2: Race Stat Bonuses (Male) " + "─"*35)
    print(f"  {'Race':<14}" + "".join(f"{s:>5}" for s in STAT_NAMES))
    print("  " + "─"*(14 + 5*NUM_STATS))
    for ri in range(NUM_RACES):
        print(f"  {RACE_NAMES[ri]:<14}" + "".join(f"{v:>5}" for v in t.race_stat_bonus_male[ri]))

    print("\n── Table 3: Race Stat Bonuses (Female) " + "─"*33)
    print(f"  {'Race':<14}" + "".join(f"{s:>5}" for s in STAT_NAMES))
    print("  " + "─"*(14 + 5*NUM_STATS))
    for ri in range(NUM_RACES):
        print(f"  {RACE_NAMES[ri]:<14}" + "".join(f"{v:>5}" for v in t.race_stat_bonus_female[ri]))

    # Class base stats
    print("\n── Table 4: Class Base-Stat Floors " + "─"*37)
    print(f"  {'Class':<14}" + "".join(f"{s:>5}" for s in STAT_NAMES))
    print("  " + "─"*(14 + 5*NUM_STATS))
    for ci, row in enumerate(t.class_base_stats):
        nm = CLASS_NAMES[ci] if ci < NUM_CLASSES else f"Extra{ci}"
        print(f"  {nm:<14}" + "".join(f"{v:>5}" for v in row))

    # Class×race modifier
    print("\n── Table 5: Class×Race AP-Cost Modifier " + "─"*32)
    short = [n[:4] for n in RACE_NAMES]
    print(f"  {'Class':<14}" + "".join(f"{n:>5}" for n in short))
    print("  " + "─"*(14 + 5*NUM_RACES))
    for ci, row in enumerate(t.class_race_mod):
        nm = CLASS_NAMES[ci] if ci < NUM_CLASSES else f"Extra{ci}"
        print(f"  {nm:<14}" + "".join(f"{v:>5}" for v in row))

    # Portraits
    if t.portrait_files:
        print("\n── Portrait Files " + "─"*54)
        for f in t.portrait_files:
            print(f"  {f}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────────────────────

def demo(creator: CharacterCreator) -> None:
    t = creator.t
    print("\n" + "═"*64)
    print("  WIZARDRY — AUTO-GENERATED SAMPLE PARTY")
    print("═"*64)

    # (name, race_idx, class_idx, gender, alignment)
    party_spec = [
        ("Aldric",  0, 0, Gender.MALE,   Alignment.GOOD),    # Human   Fighter
        ("Sylvara", 1, 0, Gender.FEMALE, Alignment.GOOD),    # Elf     Fighter
        ("Borin",   2, 3, Gender.MALE,   Alignment.NEUTRAL), # Dwarf   Thief
        ("Nim",     4, 3, Gender.FEMALE, Alignment.GOOD),    # Hobbit  Thief
        ("Zyx",     9, 4, Gender.MALE,   Alignment.NEUTRAL), # Felpurr Bishop
        ("Kragg",   7, 0, Gender.MALE,   Alignment.EVIL),    # Draken  Fighter
    ]

    for name, ri, ci, gender, alignment in party_spec:
        try:
            char = creator.create(name, ri, ci, gender, alignment, auto_spend=True)
            print(char)
        except ValueError as e:
            print(f"  [SKIP] {name}: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# INTERACTIVE SESSION
# ─────────────────────────────────────────────────────────────────────────────

def _pick(prompt: str, options: list, label_fn=None) -> any:
    label_fn = label_fn or str
    print(f"\n{prompt}")
    for i, opt in enumerate(options):
        print(f"  {i+1:>2}. {label_fn(opt)}")
    while True:
        try:
            choice = int(input("  Choice: ").strip())
            if 1 <= choice <= len(options):
                return options[choice - 1]
        except (ValueError, KeyboardInterrupt):
            pass
        print("  Invalid, try again.")


def interactive_session(creator: CharacterCreator) -> Character:
    print("\n" + "═"*64)
    print("  WIZARDRY  ─  CHARACTER CREATION")
    print("═"*64)

    char_name = input("\n  Enter character name: ").strip() or "Hero"

    race_idx = _pick(
        "Choose race:",
        list(range(NUM_RACES)),
        lambda i: RACE_NAMES[i] if i < len(RACE_NAMES) else f"Race{i}",
    )

    gender = _pick("Choose gender:", list(Gender), lambda g: g.name)

    alignments = creator.available_alignments(race_idx)
    alignment  = _pick("Choose alignment:", alignments, lambda a: a.name)

    class_indices = creator.available_class_indices(race_idx)
    class_idx = _pick(
        f"Choose class (available to {RACE_NAMES[race_idx]}):",
        class_indices,
        lambda i: CLASS_NAMES[i] if i < len(CLASS_NAMES) else f"Class{i}",
    )

    char = creator.create(char_name, race_idx, class_idx, gender, alignment)

    while True:
        print(f"\n  Stats:\n{char}")
        action = input("\n  [R]eroll  [S]pend bonus points  [D]one: ").strip().upper()

        if action == 'R':
            creator.reroll(char)

        elif action == 'S':
            if char.bonus_pool == 0:
                print("  No bonus points remaining.")
                continue
            cost = creator.t.stat_point_cost(char.class_idx, char.race_idx)
            print(f"\n  Bonus pool: {char.bonus_pool} pts  ({cost} pt per +1 for this class/race)")
            for si, (sname, val) in enumerate(zip(STAT_NAMES, char.stats)):
                print(f"    {si+1}. {sname}: {val:>3}")
            try:
                si  = int(input("  Stat (1-7): ").strip()) - 1
                amt = int(input("  Amount:    ").strip())
                if creator.spend_bonus(char, si, amt):
                    print(f"  ✓ {STAT_NAMES[si]} raised by {amt}.")
                else:
                    print("  ✗ Not enough points or invalid stat.")
            except (ValueError, IndexError):
                print("  Invalid input.")

        elif action == 'D':
            break

    print(f"\n  Character finalised!\n{char}")
    return char


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    positional = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags      = {a for a in sys.argv[1:] if a.startswith('--')}

    if not positional:
        print("Usage: python wizardry_charcreate.py <wpcmk.ovr> [--demo] [--dump]")
        sys.exit(1)

    ovr_path = positional[0]
    print(f"  Loading tables from: {ovr_path}")
    tables  = load_tables(ovr_path)
    creator = CharacterCreator(tables)
    print(
        f"  ✓ Extracted {NUM_RACES} races × {NUM_CLASSES} classes × {NUM_STATS} stats. "
        f"Portrait files: {tables.portrait_files or 'none found'}"
    )

    if '--dump' in flags:
        dump_tables(tables)

    if '--demo' in flags:
        demo(creator)
    else:
        interactive_session(creator)


if __name__ == "__main__":
    main()