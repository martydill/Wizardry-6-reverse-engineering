"""Parser for SCENARIO.DBS — the master game data file.

SCENARIO.DBS contains all game world data: monsters, items, spells, maps,
loot tables, class/race definitions, events, and sprites.

The file format is not publicly documented. This parser is built through
reverse engineering using:
- The Cosmic Forge Editor as a behavioral reference
- The Wizardry-6-API (.NET library) for format clues
- Binary diffing of save files before/after known changes
- Cross-referencing parsed values against community wikis

The file appears to use a section-based layout with a header containing
offsets to each data section.
"""

from __future__ import annotations

import logging
from pathlib import Path

from bane.data.binary_reader import BinaryReader, BinaryReaderError
from bane.data.enums import (
    AttackMode,
    ItemFlag,
    ItemType,
    Profession,
    Race,
    Skill,
    SpellSchool,
    SpellTarget,
    TileSpecial,
    WallType,
)
from bane.data.models import (
    DungeonLevel,
    ItemDef,
    LootEntry,
    LootTable,
    MapEventDef,
    MonsterDef,
    ProfessionDef,
    RaceDef,
    ScenarioData,
    SpellDef,
    TileData,
)

logger = logging.getLogger(__name__)


class ScenarioParseError(Exception):
    """Raised when SCENARIO.DBS parsing fails."""


# ---------------------------------------------------------------------------
# Section header offsets (to be discovered through reverse engineering)
# These are placeholder structures that will be refined as we analyze real data.
# ---------------------------------------------------------------------------

# Expected magic bytes or signature at the start of SCENARIO.DBS
SCENARIO_EXPECTED_SIGNATURES: list[bytes] = []  # TBD from real data analysis


class ScenarioParser:
    """Parses the SCENARIO.DBS file into structured game data.

    Usage:
        parser = ScenarioParser(Path("gamedata/SCENARIO.DBS"))
        scenario = parser.parse()
        print(scenario.monsters[0].name)
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._reader: BinaryReader | None = None
        self._section_offsets: dict[str, int] = {}

    def parse(self) -> ScenarioData:
        """Parse the entire SCENARIO.DBS file and return structured data."""
        logger.info("Parsing SCENARIO.DBS from %s", self.path)
        self._reader = BinaryReader.from_file(self.path)

        scenario = ScenarioData()

        try:
            self._parse_header()
            scenario.monsters = self._parse_monsters()
            scenario.items = self._parse_items()
            scenario.spells = self._parse_spells()
            scenario.loot_tables = self._parse_loot_tables()
            scenario.races = self._parse_races()
            scenario.professions = self._parse_professions()
            scenario.dungeon_levels = self._parse_dungeon_levels()
            scenario.events = self._parse_events()
        except BinaryReaderError as e:
            raise ScenarioParseError(f"Failed to parse SCENARIO.DBS: {e}") from e

        logger.info(
            "Parsed SCENARIO.DBS: %d monsters, %d items, %d spells, %d levels",
            len(scenario.monsters),
            len(scenario.items),
            len(scenario.spells),
            len(scenario.dungeon_levels),
        )
        return scenario

    def _parse_header(self) -> None:
        """Parse the file header to discover section offsets.

        The header structure needs to be reverse-engineered from real data files.
        This method will be updated as the format is discovered.

        Strategy:
        1. Read first N bytes and look for recognizable patterns
        2. Identify pointer table (array of uint32 offsets to sections)
        3. Map each offset to a section type based on content analysis
        """
        assert self._reader is not None
        reader = self._reader
        reader.seek(0)

        # Log the first 256 bytes for analysis
        logger.debug("SCENARIO.DBS header hex dump:\n%s", reader.hex_dump(0, 256))

        # TODO: Reverse-engineer the actual header format.
        # For now, store the file size for validation.
        self._section_offsets["file_size"] = reader.size
        logger.info("SCENARIO.DBS file size: %d bytes (0x%X)", reader.size, reader.size)

    def _parse_monsters(self) -> dict[int, MonsterDef]:
        """Parse all monster definitions from the monster data section.

        Each monster record contains:
        - Name (null-terminated or fixed-length string)
        - Level, HP range, AC per attack mode (9 values)
        - Attack data: num attacks, damage range, attack mode
        - Resistances per attack mode (9 values)
        - Spell casting data
        - Loot table reference
        - Sprite ID
        - Group size range
        - HP regeneration rate
        - Double-damage type byte
        - Special abilities bitfield
        """
        assert self._reader is not None
        monsters: dict[int, MonsterDef] = {}

        offset = self._section_offsets.get("monsters")
        if offset is None:
            logger.warning("Monster section offset not found; skipping monster parsing")
            return monsters

        reader = self._reader
        reader.seek(offset)

        # Read monster count
        count = reader.read_u16()
        logger.info("Parsing %d monsters starting at offset 0x%X", count, offset)

        for i in range(count):
            monster = self._parse_single_monster(i)
            monsters[monster.id] = monster

        return monsters

    def _parse_single_monster(self, monster_id: int) -> MonsterDef:
        """Parse a single monster record."""
        assert self._reader is not None
        reader = self._reader

        monster = MonsterDef(id=monster_id)

        # Name (assumed 20 bytes, null-padded — to be verified)
        monster.name = reader.read_string(20)

        # Core stats
        monster.level = reader.read_u16()
        monster.hp_min = reader.read_u16()
        monster.hp_max = reader.read_u16()

        # AC per attack mode (9 values, signed bytes)
        for mode in AttackMode:
            monster.ac[mode] = reader.read_i8()

        monster.xp_reward = reader.read_u32()
        monster.gold_min = reader.read_u16()
        monster.gold_max = reader.read_u16()

        # Attack data
        monster.num_attacks = reader.read_u8()
        monster.damage_min = reader.read_u16()
        monster.damage_max = reader.read_u16()
        monster.attack_mode = AttackMode(reader.read_u8() % len(AttackMode))

        # Resistances per attack mode (9 values, unsigned bytes 0-100)
        for mode in AttackMode:
            monster.resistances[mode] = reader.read_u8()

        # Spell casting
        monster.spell_cast_chance = reader.read_u8()
        monster.can_cast_spells = monster.spell_cast_chance > 0
        num_spells = reader.read_u8()
        for _ in range(num_spells):
            monster.spell_list.append(reader.read_u16())

        # Loot and sprite
        monster.loot_table_id = reader.read_u16()
        monster.sprite_id = reader.read_u16()

        # Group size
        monster.group_size_min = reader.read_u8()
        monster.group_size_max = reader.read_u8()

        # HP regeneration
        monster.hp_regen_rate = reader.read_u8()

        # Double damage type (NOTE: type 0 = FIGHTER, known bug)
        monster.double_damage_type = reader.read_u8()

        # Special abilities bitfield
        monster.special_abilities = reader.read_u16()

        # Breath weapon
        breath = reader.read_u8()
        if breath > 0 and breath <= len(AttackMode):
            monster.breath_weapon = AttackMode(breath - 1)

        return monster

    def _parse_items(self) -> dict[int, ItemDef]:
        """Parse all item definitions."""
        assert self._reader is not None
        items: dict[int, ItemDef] = {}

        offset = self._section_offsets.get("items")
        if offset is None:
            logger.warning("Item section offset not found; skipping item parsing")
            return items

        reader = self._reader
        reader.seek(offset)
        count = reader.read_u16()
        logger.info("Parsing %d items starting at offset 0x%X", count, offset)

        for i in range(count):
            item = self._parse_single_item(i)
            items[item.id] = item

        return items

    def _parse_single_item(self, item_id: int) -> ItemDef:
        """Parse a single item record."""
        assert self._reader is not None
        reader = self._reader

        item = ItemDef(id=item_id)

        # Names
        item.name = reader.read_string(20)
        item.unidentified_name = reader.read_string(20)

        # Type and slot
        item.item_type = ItemType(reader.read_u8() % len(ItemType))
        equip_slot_raw = reader.read_u8()
        if equip_slot_raw < 8:
            from bane.data.enums import EquipSlot
            item.equip_slot = EquipSlot(equip_slot_raw)

        item.flags = ItemFlag(reader.read_u16())
        item.weight = reader.read_u16()
        item.value = reader.read_u32()

        # Weapon stats
        item.damage_min = reader.read_u8()
        item.damage_max = reader.read_u8()
        item.to_hit_bonus = reader.read_i8()
        item.attack_mode = AttackMode(reader.read_u8() % len(AttackMode))
        item.num_attacks = reader.read_u8()

        # Armor AC bonuses per attack mode
        for mode in AttackMode:
            item.ac_bonus[mode] = reader.read_i8()

        # Restrictions (bitfields)
        class_restrict = reader.read_u16()
        for prof in Profession:
            if class_restrict & (1 << prof.value):
                item.class_restrictions.add(prof)

        race_restrict = reader.read_u16()
        for race in Race:
            if race_restrict & (1 << race.value):
                item.race_restrictions.add(race)

        sex_restrict = reader.read_u8()
        if sex_restrict in (0, 1):
            item.sex_restriction = Sex(sex_restrict) if sex_restrict < 2 else None
        else:
            item.sex_restriction = None

        # Spell effect
        castable = reader.read_u16()
        if castable > 0:
            item.castable_spell_id = castable
        item.charges = reader.read_u8()
        item.spell_power = reader.read_u8()

        item.sprite_id = reader.read_u16()

        return item

    def _parse_spells(self) -> dict[int, SpellDef]:
        """Parse all spell definitions."""
        assert self._reader is not None
        spells: dict[int, SpellDef] = {}

        offset = self._section_offsets.get("spells")
        if offset is None:
            logger.warning("Spell section offset not found; skipping spell parsing")
            return spells

        reader = self._reader
        reader.seek(offset)
        count = reader.read_u16()
        logger.info("Parsing %d spells starting at offset 0x%X", count, offset)

        for i in range(count):
            spell = SpellDef(id=i)
            spell.name = reader.read_string(20)
            spell.school = SpellSchool(reader.read_u8() % len(SpellSchool))
            spell.level = reader.read_u8()
            spell.sp_cost = reader.read_u16()
            spell.target_type = SpellTarget(reader.read_u8() % len(SpellTarget))

            attack_mode_raw = reader.read_u8()
            if attack_mode_raw < len(AttackMode):
                spell.attack_mode = AttackMode(attack_mode_raw)

            spell.damage_min = reader.read_u16()
            spell.damage_max = reader.read_u16()
            spell.damage_per_level = reader.read_u8()
            spell.status_effect = Condition(reader.read_u16())
            spell.duration_rounds = reader.read_u8()
            spells[spell.id] = spell

        return spells

    def _parse_loot_tables(self) -> dict[int, LootTable]:
        """Parse loot drop tables."""
        assert self._reader is not None
        tables: dict[int, LootTable] = {}

        offset = self._section_offsets.get("loot_tables")
        if offset is None:
            logger.warning("Loot table section offset not found; skipping")
            return tables

        reader = self._reader
        reader.seek(offset)
        count = reader.read_u16()
        logger.info("Parsing %d loot tables starting at offset 0x%X", count, offset)

        for i in range(count):
            table = LootTable(id=i)
            num_entries = reader.read_u8()
            for _ in range(num_entries):
                entry = LootEntry(
                    item_id=reader.read_u16(),
                    drop_chance=reader.read_u8(),
                    min_count=reader.read_u8(),
                    max_count=reader.read_u8(),
                )
                table.entries.append(entry)
            tables[table.id] = table

        return tables

    def _parse_races(self) -> dict[Race, RaceDef]:
        """Parse race definitions (stat modifiers, resistances, abilities)."""
        assert self._reader is not None
        races: dict[Race, RaceDef] = {}

        offset = self._section_offsets.get("races")
        if offset is None:
            logger.warning("Race section offset not found; skipping")
            return races

        reader = self._reader
        reader.seek(offset)

        for race in Race:
            rdef = RaceDef(race=race)
            # 7 stat modifiers (signed bytes)
            for ability in range(7):
                rdef.stat_modifiers[ability] = reader.read_i8()
            # 7 stat minimums
            for ability in range(7):
                rdef.stat_minimums[ability] = reader.read_u8()
            # 7 stat maximums
            for ability in range(7):
                rdef.stat_maximums[ability] = reader.read_u8()
            # Resistances per attack mode
            for mode in AttackMode:
                rdef.resistances[mode] = reader.read_i8()
            races[race] = rdef

        return races

    def _parse_professions(self) -> dict[Profession, ProfessionDef]:
        """Parse class/profession definitions."""
        assert self._reader is not None
        professions: dict[Profession, ProfessionDef] = {}

        offset = self._section_offsets.get("professions")
        if offset is None:
            logger.warning("Profession section offset not found; skipping")
            return professions

        reader = self._reader
        reader.seek(offset)

        for prof in Profession:
            pdef = ProfessionDef(profession=prof)
            # 7 stat requirements
            for ability in range(7):
                pdef.stat_requirements[ability] = reader.read_u8()
            # Spell schools (bitmask)
            school_mask = reader.read_u8()
            for school in SpellSchool:
                if school_mask & (1 << school.value):
                    pdef.spell_schools.append(school)
            # HP/Stamina/SP per level
            pdef.hp_per_level_min = reader.read_u8()
            pdef.hp_per_level_max = reader.read_u8()
            pdef.stamina_per_level_min = reader.read_u8()
            pdef.stamina_per_level_max = reader.read_u8()
            pdef.sp_per_level_min = reader.read_u8()
            pdef.sp_per_level_max = reader.read_u8()
            # Skills (bitmask of learnable skills)
            skill_mask = reader.read_u32()
            for skill in Skill:
                if skill_mask & (1 << skill.value):
                    pdef.learnable_skills.append(skill)
            # XP table (20 levels)
            for _ in range(20):
                pdef.xp_table.append(reader.read_u32())
            professions[prof] = pdef

        return professions

    def _parse_dungeon_levels(self) -> dict[int, DungeonLevel]:
        """Parse all dungeon level map data."""
        assert self._reader is not None
        levels: dict[int, DungeonLevel] = {}

        offset = self._section_offsets.get("maps")
        if offset is None:
            logger.warning("Map section offset not found; skipping")
            return levels

        reader = self._reader
        reader.seek(offset)
        count = reader.read_u16()
        logger.info("Parsing %d dungeon levels starting at offset 0x%X", count, offset)

        for i in range(count):
            level = self._parse_single_level(i)
            levels[level.level_id] = level

        return levels

    def _parse_single_level(self, level_id: int) -> DungeonLevel:
        """Parse a single dungeon level's tile data.

        Map tile encoding (per the Wizardry Legacy research):
        - First byte: 4 walls encoded in 2-bit pairs
          bits 0-1: North wall
          bits 2-3: East wall
          bits 4-5: South wall
          bits 6-7: West wall
        - Additional bytes: floor/ceiling textures, special properties, events
        """
        assert self._reader is not None
        reader = self._reader

        level = DungeonLevel(level_id=level_id)
        level.width = reader.read_u16()
        level.height = reader.read_u16()
        level.texture_palette = reader.read_u8()
        level.name = reader.read_string(20)

        level.tiles = []
        for y in range(level.height):
            row: list[TileData] = []
            for x in range(level.width):
                tile = self._parse_tile(x, y)
                row.append(tile)
            level.tiles.append(row)

        return level

    def _parse_tile(self, x: int, y: int) -> TileData:
        """Parse a single tile's data."""
        assert self._reader is not None
        reader = self._reader

        tile = TileData(x=x, y=y)

        # Wall byte: 4 walls × 2 bits
        wall_byte = reader.read_u8()
        tile.north_wall = WallType((wall_byte >> 0) & 0x03)
        tile.east_wall = WallType((wall_byte >> 2) & 0x03)
        tile.south_wall = WallType((wall_byte >> 4) & 0x03)
        tile.west_wall = WallType((wall_byte >> 6) & 0x03)

        # Floor and ceiling textures
        tile.floor_texture = reader.read_u8()
        tile.ceiling_texture = reader.read_u8()

        # Special tile type
        special_byte = reader.read_u8()
        if special_byte < len(TileSpecial):
            tile.special = TileSpecial(special_byte)
        tile.special_param = reader.read_u8()

        # Encounter probability
        tile.encounter_chance = reader.read_u8()

        # Fixed encounter (0 = none)
        fixed_enc = reader.read_u16()
        tile.fixed_encounter_id = fixed_enc if fixed_enc > 0 else None

        # Event reference (0 = none)
        event_ref = reader.read_u16()
        tile.event_id = event_ref if event_ref > 0 else None

        # Texture zone
        tile.texture_zone = reader.read_u8()

        return tile

    def _parse_events(self) -> dict[int, MapEventDef]:
        """Parse map events/triggers."""
        assert self._reader is not None
        events: dict[int, MapEventDef] = {}

        offset = self._section_offsets.get("events")
        if offset is None:
            logger.warning("Event section offset not found; skipping")
            return events

        reader = self._reader
        reader.seek(offset)
        count = reader.read_u16()
        logger.info("Parsing %d events starting at offset 0x%X", count, offset)

        for i in range(count):
            event = MapEventDef(event_id=i)
            event.level = reader.read_u8()
            event.x = reader.read_u8()
            event.y = reader.read_u8()
            event.event_type = reader.read_u8()
            event.condition_flags = reader.read_u16()
            data_len = reader.read_u16()
            event.action_data = reader.read_bytes(data_len)
            events[event.event_id] = event

        return events

    def dump_header(self, num_bytes: int = 512) -> str:
        """Dump the first N bytes of the file for analysis."""
        reader = BinaryReader.from_file(self.path)
        return reader.hex_dump(0, min(num_bytes, reader.size))
