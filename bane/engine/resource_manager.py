"""Resource manager for loading and caching game data.

Loads original Wizardry 6 data files once, caches the parsed results,
and provides typed access to all game data (monsters, items, spells, maps, sprites).
"""

from __future__ import annotations

import logging
from pathlib import Path

from bane.data.character_parser import CharacterParser
from bane.data.map_loader import DungeonMap
from bane.data.models import (
    CharacterData,
    DungeonLevel,
    ItemDef,
    LootTable,
    MonsterDef,
    ProfessionDef,
    RaceDef,
    SaveGameData,
    ScenarioData,
    SpellDef,
)
from bane.data.savegame_parser import SaveGameParser
from bane.data.scenario_parser import ScenarioParser
from bane.data.sprite_decoder import SpriteAtlas
from bane.engine.config import EngineConfig

logger = logging.getLogger(__name__)


class ResourceManager:
    """Centralized resource loading and caching.

    Usage:
        rm = ResourceManager(config)
        rm.load_all()
        goblin = rm.get_monster(42)
        sword = rm.get_item(7)
    """

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self._scenario: ScenarioData | None = None
        self._characters: list[CharacterData] | None = None
        self._save: SaveGameData | None = None
        self._dungeon_map: DungeonMap | None = None
        self._sprite_atlas: SpriteAtlas | None = None

    @property
    def is_loaded(self) -> bool:
        return self._scenario is not None

    @property
    def scenario(self) -> ScenarioData:
        assert self._scenario is not None, "Scenario not loaded — call load_all() first"
        return self._scenario

    @property
    def dungeon_map(self) -> DungeonMap:
        if self._dungeon_map is None:
            self._dungeon_map = DungeonMap()
            if self._scenario is not None:
                self._dungeon_map.load_levels(self._scenario.dungeon_levels)
        return self._dungeon_map

    @property
    def sprite_atlas(self) -> SpriteAtlas:
        if self._sprite_atlas is None:
            self._sprite_atlas = SpriteAtlas()
        return self._sprite_atlas

    def load_all(self) -> list[str]:
        """Load all game data. Returns list of warnings/errors."""
        warnings: list[str] = []

        # Validate game data files exist
        missing = self.config.validate_gamedata()
        if missing:
            for m in missing:
                warnings.append(f"Missing file: {m}")
            logger.warning("Missing game data files: %s", missing)

        # Load scenario data
        if self.config.scenario_dbs_path.exists():
            try:
                parser = ScenarioParser(self.config.scenario_dbs_path)
                self._scenario = parser.parse()
                logger.info("Loaded scenario data")
            except Exception as e:
                warnings.append(f"Failed to load SCENARIO.DBS: {e}")
                logger.exception("Failed to load SCENARIO.DBS")
                self._scenario = ScenarioData()
        else:
            self._scenario = ScenarioData()

        # Load dungeon map
        self._dungeon_map = DungeonMap()
        self._dungeon_map.load_levels(self._scenario.dungeon_levels)

        # Load characters (if save exists)
        if self.config.pcfile_dbs_path.exists():
            try:
                char_parser = CharacterParser(self.config.pcfile_dbs_path)
                self._characters = char_parser.parse()
                logger.info("Loaded %d characters", len(self._characters))
            except Exception as e:
                warnings.append(f"Failed to load PCFILE.DBS: {e}")
                logger.exception("Failed to load PCFILE.DBS")

        # Load save game (if exists)
        if self.config.savegame_dbs_path.exists():
            try:
                save_parser = SaveGameParser(self.config.savegame_dbs_path)
                self._save = save_parser.parse()
                logger.info("Loaded save game")
            except Exception as e:
                warnings.append(f"Failed to load SAVEGAME.DBS: {e}")
                logger.exception("Failed to load SAVEGAME.DBS")

        return warnings

    # ----- Typed accessors -----

    def get_monster(self, monster_id: int) -> MonsterDef | None:
        return self.scenario.monsters.get(monster_id)

    def get_item(self, item_id: int) -> ItemDef | None:
        return self.scenario.items.get(item_id)

    def get_spell(self, spell_id: int) -> SpellDef | None:
        return self.scenario.spells.get(spell_id)

    def get_loot_table(self, table_id: int) -> LootTable | None:
        return self.scenario.loot_tables.get(table_id)

    def get_race_def(self, race: int) -> RaceDef | None:
        from bane.data.enums import Race
        return self.scenario.races.get(Race(race))

    def get_profession_def(self, prof: int) -> ProfessionDef | None:
        from bane.data.enums import Profession
        return self.scenario.professions.get(Profession(prof))

    def get_dungeon_level(self, level_id: int) -> DungeonLevel | None:
        return self.scenario.dungeon_levels.get(level_id)

    def get_characters(self) -> list[CharacterData]:
        return self._characters or []

    def get_save(self) -> SaveGameData | None:
        return self._save
