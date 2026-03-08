"""Parser for PCFILE.DBS — character/party data.

PCFILE.DBS stores all player characters. Each character record contains:
- Name, race, sex, profession, portrait
- 7 core ability scores
- HP, Stamina, SP (current and max)
- Level, XP, age, gold, kills, rebirths
- All skill levels
- Equipment (8 slots, stored as item IDs)
- Inventory (12 slots)
- Known spells (bitfield per school)
- Conditions, resistances
- Carrying capacity, base miss chance, mana recovery rate

The format is uncompressed with stats stored directly as hex values.
Cross-reference: Wizardry-6-API (github.com/dsx75/Wizardry-6-API)
"""

from __future__ import annotations

import logging
from pathlib import Path

from bane.data.binary_reader import BinaryReader, BinaryReaderError, BinaryWriter
from bane.data.enums import (
    AttackMode,
    Condition,
    EquipSlot,
    Profession,
    Race,
    Sex,
    Skill,
    SpellSchool,
)
from bane.data.models import CharacterData

logger = logging.getLogger(__name__)


class CharacterParseError(Exception):
    """Raised when PCFILE.DBS parsing fails."""


# Number of spell bits per school (7 levels, multiple spells per level)
# Exact count TBD from reverse engineering
SPELLS_PER_SCHOOL = 49  # 7 levels × 7 spells (estimated)

# Character record size for Wizardry 6
CHAR_RECORD_SIZE = 432
HEADER_SIZE = 24


class CharacterParser:
    """Parses PCFILE.DBS into a list of CharacterData.

    Usage:
        parser = CharacterParser(Path("gamedata/PCFILE.DBS"))
        characters = parser.parse()
        for char in characters:
            print(f"{char.name} - Level {char.level} {char.profession.name}")
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def parse(self) -> list[CharacterData]:
        """Parse all characters from PCFILE.DBS."""
        logger.info("Parsing PCFILE.DBS from %s", self.path)
        data = self.path.read_bytes()
        reader = BinaryReader(data)
        characters: list[CharacterData] = []

        try:
            # First character offset is at [4:6]
            reader.seek(4)
            first_char_offset = reader.read_u16()
            # Record size can be inferred from gap between characters or known constant
            # For Wiz6 PCFILE.DBS, it's 432 bytes.
            
            # Calculate count based on file size and offset
            count = (len(data) - first_char_offset) // CHAR_RECORD_SIZE
            logger.info("Detected %d characters in PCFILE.DBS", count)

            for i in range(count):
                reader.seek(first_char_offset + i * CHAR_RECORD_SIZE)
                char = self._parse_character(reader, i)
                characters.append(char)

        except BinaryReaderError as e:
            raise CharacterParseError(f"Failed to parse PCFILE.DBS: {e}") from e

        return characters

    def _parse_character(self, reader: BinaryReader, index: int) -> CharacterData:
        """Parse a single character record."""
        char = CharacterData()
        record_start = reader.position

        # Name (16 bytes, null-padded)
        char.name = reader.read_string(16)

        # Race, sex, profession, portrait
        char.race = Race(reader.read_u8() % len(Race))
        char.sex = Sex(reader.read_u8() % len(Sex))
        char.profession = Profession(reader.read_u8() % len(Profession))
        char.portrait_id = reader.read_u8()

        # 7 core ability scores (each 1 byte)
        char.strength = reader.read_u8()
        char.intelligence = reader.read_u8()
        char.piety = reader.read_u8()
        char.vitality = reader.read_u8()
        char.dexterity = reader.read_u8()
        char.speed = reader.read_u8()
        char.personality = reader.read_u8()

        # HP, Stamina, SP (current and max, each 2 bytes)
        char.hp_current = reader.read_u16()
        char.hp_max = reader.read_u16()
        char.stamina_current = reader.read_u16()
        char.stamina_max = reader.read_u16()
        char.sp_current = reader.read_u16()
        char.sp_max = reader.read_u16()

        # Level, XP, age, gold
        char.level = reader.read_u16()
        char.experience = reader.read_u32()
        char.age = reader.read_u16()
        char.gold = reader.read_u32()

        # Kill count, rebirths (class changes)
        char.kills = reader.read_u16()
        char.rebirths = reader.read_u8()

        # Skills (each skill level is 1 byte)
        for skill in Skill:
            char.skills[skill] = reader.read_u8()

        # Equipment (8 slots, each 2-byte item ID, 0 = empty)
        for slot in EquipSlot:
            item_id = reader.read_u16()
            char.equipment[slot] = item_id if item_id > 0 else None

        # Inventory (12 items, each 2-byte item ID, 0 = empty)
        for _ in range(12):
            item_id = reader.read_u16()
            if item_id > 0:
                char.inventory.append(item_id)

        # Spells known (bitfield per school)
        for school in SpellSchool:
            num_bytes = (SPELLS_PER_SCHOOL + 7) // 8
            bits = reader.read_bitfield(num_bytes)
            char.spells_known[school] = bits[:SPELLS_PER_SCHOOL]

        # Conditions (2-byte bitfield)
        char.conditions = Condition(reader.read_u16())

        # Resistances per attack mode (9 × 1 byte)
        for mode in AttackMode:
            char.resistances[mode] = reader.read_i8()

        # Carrying capacity
        char.carrying_capacity = reader.read_u16()
        char.current_weight = reader.read_u16()

        # Hidden stats
        char.base_miss_chance = reader.read_u8()
        char.mana_recovery_rate = reader.read_u8()

        logger.debug(
            "Parsed character #%d: %s (L%d %s %s)",
            index,
            char.name,
            char.level,
            char.race.name,
            char.profession.name,
        )

        return char

    def dump_characters(self) -> str:
        """Return a human-readable summary of all characters."""
        try:
            characters = self.parse()
        except (CharacterParseError, FileNotFoundError) as e:
            return f"Error: {e}"

        lines = [f"PCFILE.DBS — {len(characters)} characters\n"]
        for i, char in enumerate(characters):
            lines.append(f"  [{i}] {char.name}")
            lines.append(
                f"      Level {char.level} {char.race.name} {char.sex.name} "
                f"{char.profession.name}"
            )
            lines.append(
                f"      HP: {char.hp_current}/{char.hp_max}  "
                f"STA: {char.stamina_current}/{char.stamina_max}  "
                f"SP: {char.sp_current}/{char.sp_max}"
            )
            lines.append(
                f"      STR:{char.strength} INT:{char.intelligence} "
                f"PIE:{char.piety} VIT:{char.vitality} "
                f"DEX:{char.dexterity} SPD:{char.speed} PER:{char.personality}"
            )
            lines.append(f"      XP: {char.experience}  Gold: {char.gold}  Age: {char.age}")
            if char.conditions != Condition.NONE:
                lines.append(f"      Conditions: {char.conditions.name}")
            lines.append("")

        return "\n".join(lines)


class CharacterWriter:
    """Writes character data back to PCFILE.DBS format."""

    def write(self, characters: list[CharacterData], path: Path | str) -> None:
        """Write characters to a PCFILE.DBS file."""
        writer = BinaryWriter()

        # Character count
        writer.write_u16(len(characters))

        for char in characters:
            self._write_character(writer, char)

        writer.write_to_file(path)
        logger.info("Wrote %d characters to %s", len(characters), path)

    def _write_character(self, writer: BinaryWriter, char: CharacterData) -> None:
        """Write a single character record."""
        writer.write_string(char.name, 16)
        writer.write_u8(char.race.value)
        writer.write_u8(char.sex.value)
        writer.write_u8(char.profession.value)
        writer.write_u8(char.portrait_id)

        # Stats
        writer.write_u8(char.strength)
        writer.write_u8(char.intelligence)
        writer.write_u8(char.piety)
        writer.write_u8(char.vitality)
        writer.write_u8(char.dexterity)
        writer.write_u8(char.speed)
        writer.write_u8(char.personality)

        # Vitals
        writer.write_u16(char.hp_current)
        writer.write_u16(char.hp_max)
        writer.write_u16(char.stamina_current)
        writer.write_u16(char.stamina_max)
        writer.write_u16(char.sp_current)
        writer.write_u16(char.sp_max)

        # Progression
        writer.write_u16(char.level)
        writer.write_u32(char.experience)
        writer.write_u16(char.age)
        writer.write_u32(char.gold)
        writer.write_u16(char.kills)
        writer.write_u8(char.rebirths)

        # Skills
        for skill in Skill:
            writer.write_u8(char.skills.get(skill, 0))

        # Equipment
        for slot in EquipSlot:
            item_id = char.equipment.get(slot)
            writer.write_u16(item_id if item_id is not None else 0)

        # Inventory (pad to 12 slots)
        inv = char.inventory[:12]
        for item_id in inv:
            writer.write_u16(item_id)
        for _ in range(12 - len(inv)):
            writer.write_u16(0)

        # Spells known
        for school in SpellSchool:
            bits = char.spells_known.get(school, [False] * SPELLS_PER_SCHOOL)
            bits = (bits + [False] * SPELLS_PER_SCHOOL)[:SPELLS_PER_SCHOOL]
            writer.write_bitfield(bits)

        # Conditions
        writer.write_u16(char.conditions.value)

        # Resistances
        for mode in AttackMode:
            writer.write_i8(char.resistances.get(mode, 0))

        # Carrying capacity
        writer.write_u16(char.carrying_capacity)
        writer.write_u16(char.current_weight)

        # Hidden stats
        writer.write_u8(char.base_miss_chance)
        writer.write_u8(char.mana_recovery_rate)
