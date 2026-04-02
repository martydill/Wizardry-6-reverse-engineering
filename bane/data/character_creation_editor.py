"""Patchable editor for Wizardry 6 character-creation stat tables.

Important: after checking the shipped binaries in this workspace, the starting
character stat rules are stored in `WPCMK.OVR`, not `NEWGAME.DBS`.

This module edits the stable, already-decoded tables extracted by
`loaders.character_creation`:

- race stat minimums / baselines (male and female tables)
- class base-stat floors
- class availability by race

The editor patches the original overlay bytes in place and preserves all other
data in the file.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

NUM_RACES = 14
NUM_CLASSES = 10
NUM_STATS = 7

FIELD_LENGTHS = (10, 7, 5, 8)
ANCHOR_SIGNATURE = b"PCFILE.DBS\x00"
TABLE1_SENTINEL = b"***\x00"

STAT_NAMES = ("STR", "IQ", "PIE", "VIT", "DEX", "SPD", "LUK")
CLASS_NAMES = (
    "Fighter", "Mage", "Priest", "Thief", "Bishop",
    "Samurai", "Lord", "Ninja", "Alchemist", "Valkyrie",
)
RACE_NAMES = (
    "Human", "Elf", "Dwarf", "Gnome", "Hobbit",
    "Faerie", "Lizardman", "Dracon", "Felpurr",
    "Rawulf", "Mook", "unused_race_11", "unused_race_12", "unused_race_13",
)


class Gender(IntEnum):
    MALE = 0
    FEMALE = 1


@dataclass
class CreationTables:
    class_mask: list[int]
    field2: list[int]
    field4: list[int]
    race_stat_bonus_male: list[list[int]]
    race_stat_bonus_female: list[list[int]]
    class_base_stats: list[list[int]]
    class_race_mod: list[list[int]]

    def allowed_class_indices(self, race_idx: int) -> list[int]:
        mask = self.class_mask[race_idx]
        return [i for i in range(NUM_CLASSES) if (mask >> (NUM_CLASSES - 1 - i)) & 1]


LETTER_BASE = ord("A")


class CharacterCreationEditError(Exception):
    """Raised when character-creation tables cannot be located or patched."""


@dataclass(frozen=True)
class _CStringField:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


def _skip_nulls_and_spaces(data: bytes, pos: int) -> int:
    while pos < len(data) and data[pos] in (0x00, 0x20):
        pos += 1
    return pos


def _read_cstring_field(data: bytes, pos: int) -> tuple[_CStringField, int]:
    end = data.index(b"\x00", pos)
    return _CStringField(start=pos, end=end), end + 1


def _read_next_nonempty_field(data: bytes, pos: int) -> tuple[_CStringField, int]:
    field = _CStringField(pos, pos)
    while field.length == 0 and pos < len(data):
        field, pos = _read_cstring_field(data, pos)
    return field, pos


def _field_text(data: bytes, field: _CStringField) -> str:
    return data[field.start:field.end].decode("ascii")


def _encode_letter_value(value: int) -> int:
    if not 0 <= value <= 25:
        raise CharacterCreationEditError(f"value {value} out of range 0..25 for letter table")
    return LETTER_BASE + value


def _normalize_index(value: int | str, names: tuple[str, ...], kind: str) -> int:
    if isinstance(value, int):
        idx = value
    else:
        lowered = value.strip().lower()
        matches = [i for i, name in enumerate(names) if name.lower() == lowered]
        if not matches:
            short_matches = [i for i, name in enumerate(names) if name.lower().startswith(lowered)]
            matches = short_matches
        if len(matches) != 1:
            raise CharacterCreationEditError(f"unknown {kind}: {value!r}")
        idx = matches[0]
    if not 0 <= idx < len(names):
        raise CharacterCreationEditError(f"{kind} index {idx} out of range 0..{len(names) - 1}")
    return idx


@dataclass
class _CharacterCreationLayout:
    table1_fields: list[list[_CStringField]]
    male_rows: list[_CStringField]
    female_rows: list[_CStringField]
    class_rows: list[_CStringField]
    mod_rows: list[_CStringField]


def _parse_binary_string(text: str, expected_len: int) -> int:
    if len(text) != expected_len:
        raise CharacterCreationEditError(
            f"expected {expected_len} binary chars, got {len(text)}: {text!r}"
        )
    if not all(ch in "01" for ch in text):
        raise CharacterCreationEditError(f"invalid binary field: {text!r}")
    return int(text, 2)


def _parse_letter_row(text: str, expected_len: int) -> list[int]:
    if len(text) < expected_len:
        raise CharacterCreationEditError(
            f"expected at least {expected_len} letter chars, got {len(text)}: {text!r}"
        )
    if not all("A" <= ch <= "Z" for ch in text[:expected_len]):
        raise CharacterCreationEditError(f"invalid letter row: {text!r}")
    return [ord(ch) - LETTER_BASE for ch in text[:expected_len]]


def extract_tables(data: bytes) -> CreationTables:
    layout = _scan_layout(data)

    class_mask: list[int] = []
    field2: list[int] = []
    field4: list[int] = []
    for row in layout.table1_fields:
        values = [_parse_binary_string(_field_text(data, field), expected_len)
                  for field, expected_len in zip(row, FIELD_LENGTHS)]
        class_mask.append(values[0])
        field2.append(values[1])
        field4.append(values[3])

    race_stat_bonus_male = [
        _parse_letter_row(_field_text(data, row), NUM_STATS) for row in layout.male_rows
    ]
    race_stat_bonus_female = [
        _parse_letter_row(_field_text(data, row), NUM_STATS) for row in layout.female_rows
    ]
    class_base_stats = [
        _parse_letter_row(_field_text(data, row), NUM_STATS) for row in layout.class_rows
    ]
    class_race_mod = [
        _parse_letter_row(_field_text(data, row), NUM_RACES) for row in layout.mod_rows
    ]

    return CreationTables(
        class_mask=class_mask,
        field2=field2,
        field4=field4,
        race_stat_bonus_male=race_stat_bonus_male,
        race_stat_bonus_female=race_stat_bonus_female,
        class_base_stats=class_base_stats,
        class_race_mod=class_race_mod,
    )


def _scan_layout(data: bytes) -> _CharacterCreationLayout:
    anchor = data.find(ANCHOR_SIGNATURE)
    if anchor == -1:
        raise CharacterCreationEditError("PCFILE.DBS anchor not found in overlay")

    pos = _skip_nulls_and_spaces(data, anchor + len(ANCHOR_SIGNATURE))

    table1_fields: list[list[_CStringField]] = []
    for _ in range(NUM_RACES):
        row_fields: list[_CStringField] = []
        for _expected_len in FIELD_LENGTHS:
            field, pos = _read_next_nonempty_field(data, pos)
            row_fields.append(field)
        table1_fields.append(row_fields)

    if data[pos:pos + len(TABLE1_SENTINEL)] == TABLE1_SENTINEL:
        pos += len(TABLE1_SENTINEL)
    pos = _skip_nulls_and_spaces(data, pos)

    def read_rows(count: int) -> tuple[list[_CStringField], int]:
        rows: list[_CStringField] = []
        cursor = pos
        for _ in range(count):
            field, cursor = _read_next_nonempty_field(data, cursor)
            rows.append(field)
        return rows, cursor

    male_rows, pos = read_rows(NUM_RACES)
    female_rows, pos = read_rows(NUM_RACES)
    class_rows, pos = read_rows(NUM_CLASSES + 1)
    mod_rows, pos = read_rows(NUM_CLASSES)

    return _CharacterCreationLayout(
        table1_fields=table1_fields,
        male_rows=male_rows,
        female_rows=female_rows,
        class_rows=class_rows,
        mod_rows=mod_rows,
    )


class CharacterCreationEditor:
    """Editable view over `WPCMK.OVR` character-creation tables."""

    def __init__(self, data: bytes, source_path: Path | None = None) -> None:
        self._data = bytearray(data)
        self.source_path = source_path
        self._layout = _scan_layout(data)
        self._tables = extract_tables(bytes(self._data))

    @classmethod
    def from_file(cls, path: Path | str) -> CharacterCreationEditor:
        path = Path(path)
        return cls(path.read_bytes(), source_path=path)

    @property
    def tables(self) -> CreationTables:
        return self._tables

    def to_bytes(self) -> bytes:
        return bytes(self._data)

    def write(self, path: Path | str) -> None:
        Path(path).write_bytes(self._data)

    def _refresh_tables(self) -> None:
        self._tables = extract_tables(bytes(self._data))

    def _row_for_gender(self, gender: Gender | int | str) -> list[_CStringField]:
        if isinstance(gender, str):
            gender = Gender[gender.strip().upper()]
        elif isinstance(gender, int):
            gender = Gender(gender)
        return self._layout.female_rows if gender == Gender.FEMALE else self._layout.male_rows

    def get_race_stats(self, gender: Gender | int | str, race: int | str) -> dict[str, int]:
        race_idx = _normalize_index(race, RACE_NAMES, "race")
        rows = self._row_for_gender(gender)
        text = _field_text(self._data, rows[race_idx])
        return {name: ord(text[i]) - LETTER_BASE for i, name in enumerate(STAT_NAMES)}

    def set_race_stat(
        self,
        gender: Gender | int | str,
        race: int | str,
        stat: int | str,
        value: int,
    ) -> None:
        race_idx = _normalize_index(race, RACE_NAMES, "race")
        stat_idx = _normalize_index(stat, STAT_NAMES, "stat")
        row = self._row_for_gender(gender)[race_idx]
        if row.length < NUM_STATS:
            raise CharacterCreationEditError(f"race row too short at offset 0x{row.start:X}")
        self._data[row.start + stat_idx] = _encode_letter_value(value)
        self._refresh_tables()

    def get_class_base_stats(self, class_name: int | str) -> dict[str, int]:
        class_idx = _normalize_index(class_name, CLASS_NAMES, "class")
        row = self._layout.class_rows[class_idx]
        text = _field_text(self._data, row)
        return {name: ord(text[i]) - LETTER_BASE for i, name in enumerate(STAT_NAMES)}

    def set_class_base_stat(self, class_name: int | str, stat: int | str, value: int) -> None:
        class_idx = _normalize_index(class_name, CLASS_NAMES, "class")
        stat_idx = _normalize_index(stat, STAT_NAMES, "stat")
        row = self._layout.class_rows[class_idx]
        if row.length < NUM_STATS:
            raise CharacterCreationEditError(f"class row too short at offset 0x{row.start:X}")
        self._data[row.start + stat_idx] = _encode_letter_value(value)
        self._refresh_tables()

    def is_class_allowed(self, race: int | str, class_name: int | str) -> bool:
        race_idx = _normalize_index(race, RACE_NAMES, "race")
        class_idx = _normalize_index(class_name, CLASS_NAMES, "class")
        return class_idx in self._tables.allowed_class_indices(race_idx)

    def set_class_allowed(self, race: int | str, class_name: int | str, allowed: bool) -> None:
        race_idx = _normalize_index(race, RACE_NAMES, "race")
        class_idx = _normalize_index(class_name, CLASS_NAMES, "class")
        field = self._layout.table1_fields[race_idx][0]
        bits = list(_field_text(self._data, field))
        bit_index = class_idx
        bits[bit_index] = "1" if allowed else "0"
        self._data[field.start:field.end] = "".join(bits).encode("ascii")
        self._refresh_tables()

    def get_effective_starting_stats(
        self,
        gender: Gender | int | str,
        race: int | str,
        class_name: int | str,
    ) -> dict[str, int]:
        race_idx = _normalize_index(race, RACE_NAMES, "race")
        class_idx = _normalize_index(class_name, CLASS_NAMES, "class")
        if isinstance(gender, str):
            gender = Gender[gender.strip().upper()]
        elif isinstance(gender, int):
            gender = Gender(gender)
        class_base = self._tables.class_base_stats[class_idx]
        race_min = (
            self._tables.race_stat_bonus_female[race_idx]
            if gender == Gender.FEMALE
            else self._tables.race_stat_bonus_male[race_idx]
        )
        return {
            stat_name: max(class_base[i], race_min[i])
            for i, stat_name in enumerate(STAT_NAMES)
        }
