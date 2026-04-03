"""Parser for `PCFILE.DBS` party data.

This parser now follows the record layout confirmed from `WPCVW.OVR`:

- fixed record size `0x01B0`
- active characters identified by non-empty 8-byte name
- age stored as a 32-bit value at `+0x08`
- HP current/max at `+0x18/+0x1A`
- stamina current/max at `+0x1C/+0x1E`
- load current/max at `+0x20/+0x22`
- six raw spell-point pairs at `+0x28..+0x3F`
- known-spell packed bitset at `+0x188..+0x193`
- inventory entries as 8-byte records starting at `+0x40`
- stats at `+0x12C..+0x133`
- race/gender/class at `+0x19D/+0x19E/+0x19F`

Important limitation:

- the broader engine still models a simplified 4-school spell system
- the real PCFILE format stores six raw schools (`fire/water/air/earth/mental/magic`)
- this parser preserves the raw school-point words and the explicit spell-id
  bitset instead of forcing an incorrect conversion
"""

from __future__ import annotations

import logging
from pathlib import Path

from bane.data.enums import (
    Condition,
    EquipSlot,
    Profession,
    Race,
    Sex,
    Skill,
)
from bane.data.models import CharacterData
from bane.data.pcfile_editor import (
    AGE_RAW_OFFSET,
    CLASS_OFFSET,
    GOLD_OFFSET,
    HP_OFFSET,
    NAME_OFFSET,
    NAME_SIZE,
    PCFileEditor,
    RACE_OFFSET,
    SKILL_NAMES,
    SPELL_KNOWN_BLOCK_OFFSET,
    SPELL_KNOWN_BLOCK_SIZE,
    PORTRAIT_OFFSET,
    SPELL_SCHOOLS,
    STAMINA_OFFSET,
    STAT_BLOCK_OFFSET,
    XP_OFFSET,
)
from bane.data.pcfile_spell_catalog import known_spell_ids_from_block

logger = logging.getLogger(__name__)


class CharacterParseError(Exception):
    """Raised when PCFILE.DBS parsing fails."""


def _u16(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _u32(data: bytes | bytearray, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")


def _iter_inventory_entries(record_data: bytes | bytearray) -> list[tuple[int, bytes | bytearray]]:
    entries: list[tuple[int, bytes | bytearray]] = []
    page1 = record_data[0x1AC]
    page2 = record_data[0x1AD] if 0x1AD < len(record_data) else 0

    for slot in range(max(0, min(page1, 10))):
        off = 0x40 + slot * 8
        entries.append((slot, record_data[off:off + 8]))

    for slot in range(max(0, min(page2, 10))):
        idx = 10 + slot
        off = 0x40 + idx * 8
        entries.append((idx, record_data[off:off + 8]))

    return entries


def parse_pcfile_record(record) -> CharacterData:
    """Parse one PCFILE-format record object into CharacterData.

    The input must expose `.name` and `.data` like `PCCharacterRecord`.
    """
    data = record.data
    char = CharacterData()

    char.name = record.name
    char.race = Race(data[RACE_OFFSET] % len(Race))
    char.sex = Sex.FEMALE if data[0x19E] else Sex.MALE
    char.profession = Profession(data[CLASS_OFFSET] % len(Profession))
    char.portrait_id = data[PORTRAIT_OFFSET]

    stats = data[STAT_BLOCK_OFFSET:STAT_BLOCK_OFFSET + 8]
    char.strength = stats[0]
    char.intelligence = stats[1]
    char.piety = stats[2]
    char.vitality = stats[3]
    char.dexterity = stats[4]
    char.speed = stats[5]
    char.personality = stats[6]

    char.hp_current = _u16(data, HP_OFFSET)
    char.hp_max = _u16(data, HP_OFFSET + 2)
    char.stamina_current = _u16(data, STAMINA_OFFSET)
    char.stamina_max = _u16(data, STAMINA_OFFSET + 2)

    char.age_raw = _u32(data, AGE_RAW_OFFSET)
    char.age = char.age_raw
    char.current_weight = _u16(data, GOLD_OFFSET)
    char.carrying_capacity = _u16(data, XP_OFFSET)

    for skill in Skill:
        char.skills[skill] = 0
    for skill, indices in SKILL_INDEX_MAP.items():
        vals = [data[0x134 + idx] for idx in indices if 0x134 + idx < len(data)]
        char.skills[skill] = max(vals) if vals else 0

    for slot in EquipSlot:
        char.equipment[slot] = None

    for school_name, offset in SPELL_SCHOOLS:
        char.spell_bits_known_raw[school_name] = _u16(data, offset)
        char.spell_bits_prepared_raw[school_name] = _u16(data, offset + 2)
    char.known_spell_ids = known_spell_ids_from_block(
        data,
        offset=SPELL_KNOWN_BLOCK_OFFSET,
        size=SPELL_KNOWN_BLOCK_SIZE,
    )

    for slot_index, entry in _iter_inventory_entries(data):
        item_id = _u16(entry, 0)
        if item_id <= 0:
            continue
        char.inventory.append(item_id)
        char.inventory_raw.append(
            {
                "slot_index": slot_index,
                "item_id": item_id,
                "weight_tenths": _u16(entry, 2),
                "field4": entry[4],
                "field5": entry[5],
                "field6": entry[6],
                "field7": entry[7],
            }
        )

    char.conditions = Condition.NONE
    return char


SKILL_INDEX_MAP: dict[Skill, tuple[int, ...]] = {
    Skill.SWORD: (1,),
    Skill.AXE: (2,),
    Skill.MACE_AND_FLAIL: (3,),
    Skill.POLE_AND_STAFF: (4,),
    Skill.THROWING_AND_SLING: (5, 6),
    Skill.BOW: (7,),
    Skill.SHIELD: (8,),
    Skill.SCOUTING: (22,),
    Skill.SKULDUGGERY: (15,),
    Skill.MUSIC: (12,),
    Skill.ORATORY: (13,),
    Skill.ALCHEMY: (25,),
    Skill.THEOLOGY: (26,),
    Skill.THEOSOPHY: (27,),
    Skill.THAUMATURGY: (28,),
    Skill.NINJUTSU: (16,),
    Skill.KIRIJUTSU: (29,),
    Skill.ARTIFACTS: (11,),
    Skill.MYTHOLOGY: (23,),
    Skill.LEGERDEMAIN: (14,),
}


class CharacterParser:
    """Parses `PCFILE.DBS` into `CharacterData` rows."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def parse(self) -> list[CharacterData]:
        logger.info("Parsing PCFILE.DBS from %s", self.path)
        try:
            editor = PCFileEditor.from_file(self.path)
        except Exception as e:  # pragma: no cover - wrapper path
            raise CharacterParseError(f"Failed to parse PCFILE.DBS: {e}") from e

        characters = [self._parse_record(record) for record in editor.active_records()]
        logger.info("Detected %d active characters in PCFILE.DBS", len(characters))
        return characters

    def _parse_record(self, record) -> CharacterData:
        return parse_pcfile_record(record)

    def dump_characters(self) -> str:
        try:
            characters = self.parse()
        except (CharacterParseError, FileNotFoundError) as e:
            return f"Error: {e}"

        lines = [f"PCFILE.DBS — {len(characters)} active characters\n"]
        for i, char in enumerate(characters):
            lines.append(f"  [{i}] {char.name}")
            lines.append(
                f"      {char.race.name} {char.sex.name} {char.profession.name}  "
                f"HP:{char.hp_current}/{char.hp_max}  "
                f"STA:{char.stamina_current}/{char.stamina_max}"
            )
            lines.append(
                f"      STR:{char.strength} INT:{char.intelligence} PIE:{char.piety} "
                f"VIT:{char.vitality} DEX:{char.dexterity} SPD:{char.speed} PER:{char.personality}"
            )
            lines.append(
                f"      AgeRaw:{char.age_raw}  Load:{char.current_weight}/{char.carrying_capacity}  "
                f"Items:{len(char.inventory)}"
            )
            raw_spells = {
                school: (cur, char.spell_bits_prepared_raw.get(school, 0))
                for school, cur in char.spell_bits_known_raw.items()
                if cur or char.spell_bits_prepared_raw.get(school, 0)
            }
            if raw_spells:
                lines.append(f"      Raw school points: {raw_spells}")
            if char.known_spell_ids:
                lines.append(f"      Known spell ids: {char.known_spell_ids}")
            lines.append("")

        return "\n".join(lines)


class CharacterWriter:
    """Placeholder writer for `PCFILE.DBS`.

    The previous implementation targeted an incorrect layout. Use
    `bane.data.pcfile_editor.PCFileEditor` for in-place edits until the full
    write path is rebuilt against the confirmed record structure.
    """

    def write(self, characters: list[CharacterData], path: Path | str) -> None:
        raise NotImplementedError(
            "CharacterWriter is disabled until the confirmed PCFILE.DBS write layout is rebuilt. "
            "Use PCFileEditor for patching."
        )
