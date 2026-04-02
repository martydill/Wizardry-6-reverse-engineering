"""Patchable editor for Wizardry 6 `PCFILE.DBS`.

This module is intentionally conservative: it only exposes fields that are
stable in the shipped sample file and can be patched in place without
rewriting the whole file format.

Confirmed from `gamedata/PCFILE.DBS` in this workspace:

- file header:
  - `0x00`: record size (`0x01B0` = 432 bytes)
  - `0x02`: slot count (`0x0010` = 16)
  - `0x04`: first record offset (`0x0018`)
- each record is fixed-size and can be edited independently
- active records are identified by a non-empty name field

Stable record fields used here:

- `+0x00..+0x07`: name (8-byte null-padded ASCII)
- `+0x08..+0x0B`: 32-bit age counter
- `+0x18..+0x19`: HP current
- `+0x1A..+0x1B`: HP max
- `+0x1C..+0x1D`: stamina current
- `+0x1E..+0x1F`: stamina max
- `+0x20..+0x21`: current load
- `+0x22..+0x23`: max load
- `+0x24..+0x25`: rank
- `+0x26..+0x27`: level
- `+0x28..+0x3F`: six school current/max spell-point pairs
- `+0x188..+0x193`: 12-byte known-spell packed bitset
- `+0x12C..+0x133`: contiguous 8-byte stat block

The first six stat bytes line up with the expected Wizardry creation stats:
STR, IQ, PIE, VIT, DEX, SPD. The final two bytes remain provisional.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


HEADER_RECORD_SIZE_OFFSET = 0x00
HEADER_SLOT_COUNT_OFFSET = 0x02
HEADER_FIRST_RECORD_OFFSET = 0x04

DEFAULT_RECORD_SIZE = 0x01B0
DEFAULT_SLOT_COUNT = 0x0010
DEFAULT_FIRST_RECORD_OFFSET = 0x0018

NAME_OFFSET = 0x00
NAME_SIZE = 8
AGE_RAW_OFFSET = 0x08
HP_OFFSET = 0x18
STAMINA_OFFSET = 0x1C
GOLD_OFFSET = 0x20
XP_OFFSET = 0x22
SPELL_KNOWN_BLOCK_OFFSET = 0x188
SPELL_KNOWN_BLOCK_SIZE = 12
STAT_BLOCK_OFFSET = 0x12C
STAT_BLOCK_SIZE = 8
SKILL_BLOCK_OFFSET = 0x134
SKILL_BLOCK_SIZE = 30  # indices 0-29; 24 skill slots + 6 non-skill bytes at 10, 17-21
GENDER_OFFSET = 0x19E   # 0 = male, 1 = female
RACE_OFFSET = 0x19D     # internal race ID (see RACE_NAMES_INTERNAL)
CLASS_OFFSET = 0x19F    # internal class ID (see CLASS_NAMES_INTERNAL)

# Internal race IDs (differ from character_creation_editor.py RACE_NAMES order).
# Confirmed: Human=0, Dwarf=2, Lizardman=6, Felpurr=8, Mook=10.
# Remaining entries are provisional based on the shifted ordering observed in save data.
RACE_NAMES_INTERNAL: dict[int, str] = {
    0:  "Human",
    1:  "Elf",
    2:  "Dwarf",
    3:  "Gnome",
    4:  "Hobbit",
    5:  "Faerie",
    6:  "Lizardman",
    7:  "Dracon",
    8:  "Felpurr",
    9:  "Rawulf",
    10: "Mook",
    11: "unused_race_11",
    12: "unused_race_12",
    13: "unused_race_13",
}

# Internal class IDs (differ from character_creation_editor.py CLASS_NAMES order for
# advanced classes).  Confirmed: 0-7 are the 8 basic classes; Lord=10, Samurai=11,
# Ninja=13.  IDs 8, 9, 12 are unknown (likely Bishop/Valkyrie/Monk or similar).
CLASS_NAMES_INTERNAL: dict[int, str] = {
    0:  "Fighter",
    1:  "Mage",
    2:  "Priest",
    3:  "Thief",
    4:  "Ranger",
    5:  "Alchemist",
    6:  "Bard",
    7:  "Psionic",
    8:  "Valkyrie",
    9:  "Bishop",
    10: "Lord",
    11: "Samurai",
    12: "Monk",
    13: "Ninja",
}

# Spell-point pools per school: [current_u16, max_u16] at each offset.
SPELL_SCHOOLS: tuple[tuple[str, int], ...] = (
    ("fire",   0x028),
    ("water",  0x02C),
    ("air",    0x030),
    ("earth",  0x034),
    ("mental", 0x038),
    ("magic",  0x03C),
)

STAT_NAMES = (
    "strength",
    "intelligence",
    "piety",
    "vitality",
    "dexterity",
    "speed",
    "personality",
    "karma",
)

# Skill index → name. None entries are non-skill bytes within the block (24 skills total).
SKILL_NAMES: tuple[str | None, ...] = (
    "wand_and_dagger",   # 0
    "sword",             # 1
    "axe",               # 2
    "mace_and_flail",    # 3
    "pole_and_staff",    # 4
    "throwing",          # 5
    "sling",             # 6
    "bow",               # 7
    "shield",            # 8
    "hands_and_feet",    # 9
    None,                # 10  (not a skill)
    "artifacts",         # 11
    "music",             # 12
    "oratory",           # 13
    "legerdemain",       # 14
    "skulduggery",       # 15
    "ninjutsu",          # 16
    None,                # 17  (not a skill)
    None,                # 18  (not a skill)
    None,                # 19  (not a skill)
    None,                # 20  (not a skill)
    None,                # 21  (not a skill)
    "scouting",          # 22
    "mythology",         # 23
    "scribe",            # 24
    "alchemy",           # 25
    "theology",          # 26
    "theosophy",         # 27
    "thaumaturgy",       # 28
    "kirijutsu",         # 29
    None,                # 30
)


class PCFileEditError(Exception):
    """Raised when `PCFILE.DBS` cannot be parsed or patched safely."""


def _read_u16(buf: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(buf[offset:offset + 2], "little")


def _write_u16(buf: bytearray, offset: int, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise PCFileEditError(f"u16 value out of range: {value}")
    buf[offset:offset + 2] = value.to_bytes(2, "little")


@dataclass
class PCCharacterRecord:
    """One fixed-size record from `PCFILE.DBS`."""

    slot_index: int
    data: bytearray

    @property
    def is_active(self) -> bool:
        return any(self.data[NAME_OFFSET:NAME_OFFSET + NAME_SIZE])

    @property
    def name(self) -> str:
        return self.data[NAME_OFFSET:NAME_OFFSET + NAME_SIZE].split(b"\x00", 1)[0].decode(
            "ascii", errors="replace"
        )

    @name.setter
    def name(self, value: str) -> None:
        encoded = value.encode("ascii", errors="strict")[:NAME_SIZE]
        self.data[NAME_OFFSET:NAME_OFFSET + NAME_SIZE] = encoded.ljust(NAME_SIZE, b"\x00")

    @property
    def gender(self) -> int:
        """0 = male, 1 = female."""
        return self.data[GENDER_OFFSET]

    @property
    def race_id(self) -> int:
        """Internal race ID; look up in RACE_NAMES_INTERNAL for the name."""
        return self.data[RACE_OFFSET]

    @property
    def race_name(self) -> str:
        return RACE_NAMES_INTERNAL.get(self.race_id, f"race_{self.race_id}")

    @property
    def class_id(self) -> int:
        """Internal class ID; look up in CLASS_NAMES_INTERNAL for the name."""
        return self.data[CLASS_OFFSET]

    @property
    def class_name(self) -> str:
        return CLASS_NAMES_INTERNAL.get(self.class_id, f"class_{self.class_id}")

    @property
    def age_raw(self) -> int:
        return int.from_bytes(self.data[AGE_RAW_OFFSET:AGE_RAW_OFFSET + 4], "little")

    @age_raw.setter
    def age_raw(self, value: int) -> None:
        if not 0 <= value <= 0xFFFFFFFF:
            raise PCFileEditError(f"u32 value out of range: {value}")
        self.data[AGE_RAW_OFFSET:AGE_RAW_OFFSET + 4] = value.to_bytes(4, "little")

    @property
    def hp(self) -> int:
        return _read_u16(self.data, HP_OFFSET)

    @hp.setter
    def hp(self, value: int) -> None:
        _write_u16(self.data, HP_OFFSET, value)

    @property
    def stamina(self) -> int:
        return _read_u16(self.data, STAMINA_OFFSET)

    @stamina.setter
    def stamina(self, value: int) -> None:
        _write_u16(self.data, STAMINA_OFFSET, value)
        # In the sample file the mirror at +0x1E matches exactly; keep parity.
        _write_u16(self.data, STAMINA_OFFSET + 2, value)

    @property
    def gold(self) -> int:
        return _read_u16(self.data, GOLD_OFFSET)

    @gold.setter
    def gold(self, value: int) -> None:
        _write_u16(self.data, GOLD_OFFSET, value)

    @property
    def experience(self) -> int:
        return _read_u16(self.data, XP_OFFSET)

    @experience.setter
    def experience(self, value: int) -> None:
        _write_u16(self.data, XP_OFFSET, value)

    @property
    def stats(self) -> dict[str, int]:
        block = self.data[STAT_BLOCK_OFFSET:STAT_BLOCK_OFFSET + STAT_BLOCK_SIZE]
        return {name: block[idx] for idx, name in enumerate(STAT_NAMES)}

    def get_stat(self, stat: str | int) -> int:
        idx = self._normalize_stat(stat)
        return self.data[STAT_BLOCK_OFFSET + idx]

    def set_stat(self, stat: str | int, value: int) -> None:
        idx = self._normalize_stat(stat)
        if not 0 <= value <= 0xFF:
            raise PCFileEditError(f"stat value out of range 0..255: {value}")
        self.data[STAT_BLOCK_OFFSET + idx] = value

    def _normalize_stat(self, stat: str | int) -> int:
        if isinstance(stat, int):
            idx = stat
        else:
            lowered = stat.strip().lower()
            aliases = {name: i for i, name in enumerate(STAT_NAMES)}
            aliases.update(
                {
                    "str": 0,
                    "iq": 1,
                    "int": 1,
                    "pie": 2,
                    "vit": 3,
                    "dex": 4,
                    "spd": 5,
                    "per": 6,
                    "luk": 6,
                    "kar": 7,
                }
            )
            if lowered not in aliases:
                raise PCFileEditError(f"unknown stat {stat!r}")
            idx = aliases[lowered]
        if not 0 <= idx < STAT_BLOCK_SIZE:
            raise PCFileEditError(f"stat index out of range 0..{STAT_BLOCK_SIZE - 1}: {idx}")
        return idx

    @property
    def spells(self) -> dict[str, int]:
        """Return current school-point pools for schools with non-zero current value."""
        return {
            name: _read_u16(self.data, offset)
            for name, offset in SPELL_SCHOOLS
            if _read_u16(self.data, offset)
        }

    def get_spell_school(self, school: str) -> int:
        offset = self._spell_offset(school)
        return _read_u16(self.data, offset)

    def set_spell_school(self, school: str, bitmask: int) -> None:
        if not 0 <= bitmask <= 0xFFFF:
            raise PCFileEditError(f"spell school value out of range: {bitmask}")
        offset = self._spell_offset(school)
        _write_u16(self.data, offset, bitmask)
        _write_u16(self.data, offset + 2, bitmask)

    @property
    def known_spells_block(self) -> bytes:
        return bytes(
            self.data[SPELL_KNOWN_BLOCK_OFFSET:SPELL_KNOWN_BLOCK_OFFSET + SPELL_KNOWN_BLOCK_SIZE]
        )

    def has_known_spell(self, spell_id: int) -> bool:
        if spell_id < 0 or spell_id >= SPELL_KNOWN_BLOCK_SIZE * 8:
            raise PCFileEditError(f"spell id out of range: {spell_id}")
        byte_index = spell_id >> 3
        bit_mask = 1 << (spell_id & 7)
        return bool(self.data[SPELL_KNOWN_BLOCK_OFFSET + byte_index] & bit_mask)

    def set_known_spell(self, spell_id: int, known: bool = True) -> None:
        if spell_id < 0 or spell_id >= SPELL_KNOWN_BLOCK_SIZE * 8:
            raise PCFileEditError(f"spell id out of range: {spell_id}")
        byte_index = spell_id >> 3
        bit_mask = 1 << (spell_id & 7)
        off = SPELL_KNOWN_BLOCK_OFFSET + byte_index
        if known:
            self.data[off] |= bit_mask
        else:
            self.data[off] &= (~bit_mask) & 0xFF

    def _spell_offset(self, school: str) -> int:
        lowered = school.strip().lower()
        mapping = {name: offset for name, offset in SPELL_SCHOOLS}
        if lowered not in mapping:
            raise PCFileEditError(f"unknown spell school {school!r}")
        return mapping[lowered]

    @property
    def skills(self) -> dict[str, int]:
        block = self.data[SKILL_BLOCK_OFFSET:SKILL_BLOCK_OFFSET + SKILL_BLOCK_SIZE]
        return {
            name: block[idx]
            for idx, name in enumerate(SKILL_NAMES)
            if name is not None and block[idx]
        }

    def get_skill(self, skill: str | int) -> int:
        idx = self._normalize_skill(skill)
        return self.data[SKILL_BLOCK_OFFSET + idx]

    def set_skill(self, skill: str | int, value: int) -> None:
        idx = self._normalize_skill(skill)
        if not 0 <= value <= 0xFF:
            raise PCFileEditError(f"skill value out of range 0..255: {value}")
        self.data[SKILL_BLOCK_OFFSET + idx] = value

    def _normalize_skill(self, skill: str | int) -> int:
        if isinstance(skill, int):
            idx = skill
        else:
            lowered = skill.strip().lower().replace(" ", "_").replace("&", "and")
            name_map = {name: i for i, name in enumerate(SKILL_NAMES) if name is not None}
            if lowered not in name_map:
                raise PCFileEditError(f"unknown skill {skill!r}")
            idx = name_map[lowered]
        if not 0 <= idx < SKILL_BLOCK_SIZE:
            raise PCFileEditError(f"skill index out of range 0..{SKILL_BLOCK_SIZE - 1}: {idx}")
        return idx

    def to_bytes(self) -> bytes:
        return bytes(self.data)


@dataclass
class PCFileEditor:
    """Editable view over a `PCFILE.DBS` file."""

    header: bytes
    records: list[PCCharacterRecord]
    record_size: int
    slot_count: int
    first_record_offset: int

    @classmethod
    def from_bytes(cls, data: bytes) -> PCFileEditor:
        if len(data) < DEFAULT_FIRST_RECORD_OFFSET:
            raise PCFileEditError("file too small for PCFILE header")

        record_size = _read_u16(data, HEADER_RECORD_SIZE_OFFSET)
        slot_count = _read_u16(data, HEADER_SLOT_COUNT_OFFSET)
        first_record_offset = _read_u16(data, HEADER_FIRST_RECORD_OFFSET)

        if record_size == 0:
            record_size = DEFAULT_RECORD_SIZE
        if slot_count == 0:
            slot_count = DEFAULT_SLOT_COUNT
        if first_record_offset == 0:
            first_record_offset = DEFAULT_FIRST_RECORD_OFFSET

        expected_size = first_record_offset + slot_count * record_size
        if len(data) < expected_size:
            raise PCFileEditError(
                f"file size 0x{len(data):X} smaller than expected 0x{expected_size:X}"
            )

        header = data[:first_record_offset]
        records: list[PCCharacterRecord] = []
        for slot_index in range(slot_count):
            start = first_record_offset + slot_index * record_size
            end = start + record_size
            records.append(PCCharacterRecord(slot_index=slot_index, data=bytearray(data[start:end])))

        return cls(
            header=header,
            records=records,
            record_size=record_size,
            slot_count=slot_count,
            first_record_offset=first_record_offset,
        )

    @classmethod
    def from_file(cls, path: Path | str) -> PCFileEditor:
        return cls.from_bytes(Path(path).read_bytes())

    def active_records(self) -> list[PCCharacterRecord]:
        return [record for record in self.records if record.is_active]

    def get_record(self, slot_index: int) -> PCCharacterRecord:
        if not 0 <= slot_index < len(self.records):
            raise PCFileEditError(f"slot index out of range 0..{len(self.records) - 1}: {slot_index}")
        return self.records[slot_index]

    def find_by_name(self, name: str) -> PCCharacterRecord:
        lowered = name.strip().lower()
        matches = [record for record in self.active_records() if record.name.lower() == lowered]
        if len(matches) != 1:
            raise PCFileEditError(f"expected exactly one active character named {name!r}")
        return matches[0]

    def to_bytes(self) -> bytes:
        out = bytearray(self.header)
        for record in self.records:
            out.extend(record.to_bytes())
        return bytes(out)

    def write(self, path: Path | str) -> None:
        Path(path).write_bytes(self.to_bytes())
