"""Data models for all Wizardry 6 game entities.

These dataclasses represent the structured data parsed from original binary files.
They are pure data containers with no game logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bane.data.enums import (
    AttackMode,
    Condition,
    Direction,
    EquipSlot,
    ItemFlag,
    ItemType,
    Profession,
    Race,
    Sex,
    Skill,
    SpellSchool,
    SpellTarget,
    TileSpecial,
    WallType,
)


# ---------------------------------------------------------------------------
# Monster Definition (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class MonsterDef:
    """A monster type definition as stored in SCENARIO.DBS."""

    id: int = 0
    name: str = ""
    plural_name: str = ""
    short_name: str = ""
    short_plural_name: str = ""
    strength: int = 0
    intelligence: int = 0
    dexterity: int = 0
    speed: int = 0
    hp_min: int = 0
    hp_max: int = 0
    stamina_min: int = 0
    stamina_max: int = 0
    group_size_min: int = 1
    group_size_max: int = 1
    evasion: int = 0
    level: int = 0
    ac_min: int = 0
    ac_max: int = 0
    ac: dict[AttackMode, int] = field(default_factory=dict)  # 9 attack mode ACs
    xp_reward: int = 0
    gold_min: int = 0
    gold_max: int = 0
    num_attacks: int = 1
    damage_min: int = 0
    damage_max: int = 0
    attack_mode: AttackMode = AttackMode.PHYSICAL
    special_attack_mode: AttackMode = AttackMode.PHYSICAL
    resistances: dict[AttackMode, int] = field(default_factory=dict)  # 0-100%
    hp_regen_rate: int = 0
    double_damage_type: int = 0  # NOTE: type 0 = FIGHTER (the known bug)
    can_cast_spells: bool = False
    spell_list: list[int] = field(default_factory=list)
    spell_cast_chance: int = 0  # percent
    loot_table_id: int = 0
    sprite_id: int = 0
    special_abilities: int = 0  # bitfield
    breath_weapon: AttackMode | None = None


# ---------------------------------------------------------------------------
# Item Definition (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class ItemDef:
    """An item type definition as stored in SCENARIO.DBS."""

    id: int = 0
    name: str = ""
    unidentified_name: str = ""
    item_type: ItemType = ItemType.MISC
    equip_slot: EquipSlot | None = None
    flags: ItemFlag = ItemFlag.NONE
    weight: int = 0
    value: int = 0  # base gold value
    # Weapon stats
    damage_min: int = 0
    damage_max: int = 0
    to_hit_bonus: int = 0
    attack_mode: AttackMode = AttackMode.PHYSICAL
    num_attacks: int = 1
    # Armor stats
    ac_bonus: dict[AttackMode, int] = field(default_factory=dict)
    # Restrictions
    class_restrictions: set[Profession] = field(default_factory=set)
    race_restrictions: set[Race] = field(default_factory=set)
    sex_restriction: Sex | None = None
    # Special
    castable_spell_id: int | None = None
    charges: int = 0
    spell_power: int = 0
    sprite_id: int = 0
    # Special effect chances (percent)
    paralyze_chance: int = 0
    critical_chance: int = 0
    knockout_chance: int = 0
    # Armor class bonus (negative = better AC per Wiz6 conventions)
    armor_class: int = 0


# ---------------------------------------------------------------------------
# Spell Definition (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class SpellDef:
    """A spell definition as stored in SCENARIO.DBS."""

    id: int = 0
    name: str = ""
    school: SpellSchool = SpellSchool.MAGE
    level: int = 1  # 1-7
    sp_cost: int = 0
    target_type: SpellTarget = SpellTarget.SINGLE_ENEMY
    attack_mode: AttackMode | None = None  # for damage spells
    damage_min: int = 0
    damage_max: int = 0
    damage_per_level: int = 0  # bonus damage per caster level
    status_effect: Condition = Condition.NONE
    duration_rounds: int = 0
    description: str = ""


# ---------------------------------------------------------------------------
# Loot Table (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class LootEntry:
    """A single entry in a loot table."""

    item_id: int = 0
    drop_chance: int = 0  # percent 0-100
    min_count: int = 1
    max_count: int = 1


@dataclass
class LootTable:
    """A loot table defining possible drops for a monster or chest."""

    id: int = 0
    entries: list[LootEntry] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Race Definition (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class RaceDef:
    """Race definition with stat modifiers and special abilities."""

    race: Race = Race.HUMAN
    stat_modifiers: dict[int, int] = field(default_factory=dict)  # Ability -> modifier
    stat_minimums: dict[int, int] = field(default_factory=dict)
    stat_maximums: dict[int, int] = field(default_factory=dict)
    resistances: dict[AttackMode, int] = field(default_factory=dict)
    special_abilities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Class/Profession Definition (from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class ProfessionDef:
    """Class/profession definition with requirements and progression."""

    profession: Profession = Profession.FIGHTER
    stat_requirements: dict[int, int] = field(default_factory=dict)  # Ability -> min
    spell_schools: list[SpellSchool] = field(default_factory=list)
    learnable_skills: list[Skill] = field(default_factory=list)
    use_improvable_skills: list[Skill] = field(default_factory=list)
    hp_per_level_min: int = 1
    hp_per_level_max: int = 6
    stamina_per_level_min: int = 1
    stamina_per_level_max: int = 4
    sp_per_level_min: int = 0
    sp_per_level_max: int = 0
    xp_table: list[int] = field(default_factory=list)  # XP needed per level
    starting_items: list[int] = field(default_factory=list)  # item IDs


# ---------------------------------------------------------------------------
# Character (from PCFILE.DBS / runtime)
# ---------------------------------------------------------------------------
@dataclass
class CharacterData:
    """A player character as stored in PCFILE.DBS."""

    name: str = ""
    race: Race = Race.HUMAN
    sex: Sex = Sex.MALE
    profession: Profession = Profession.FIGHTER
    portrait_id: int = 0

    # Core ability scores
    strength: int = 0
    intelligence: int = 0
    piety: int = 0
    vitality: int = 0
    dexterity: int = 0
    speed: int = 0
    personality: int = 0

    # Vitals
    hp_current: int = 0
    hp_max: int = 0
    stamina_current: int = 0
    stamina_max: int = 0
    sp_current: int = 0
    sp_max: int = 0

    # Progression
    level: int = 1
    experience: int = 0
    age: int = 18
    age_raw: int = 0
    gold: int = 0
    kills: int = 0
    rebirths: int = 0  # number of class changes

    # Skills (Skill enum -> skill level)
    skills: dict[Skill, int] = field(default_factory=dict)

    # Equipment (EquipSlot -> item instance)
    equipment: dict[EquipSlot, int | None] = field(default_factory=dict)  # item IDs

    # Inventory (swag bag, up to 12 items)
    inventory: list[int] = field(default_factory=list)  # item IDs
    inventory_raw: list[dict[str, int]] = field(default_factory=list)

    # Spells known (bitfield per school)
    spells_known: dict[SpellSchool, list[bool]] = field(default_factory=dict)
    spell_bits_known_raw: dict[str, int] = field(default_factory=dict)
    spell_bits_prepared_raw: dict[str, int] = field(default_factory=dict)
    known_spell_ids: list[int] = field(default_factory=list)

    # Status
    conditions: Condition = Condition.NONE
    resistances: dict[AttackMode, int] = field(default_factory=dict)

    # Carrying capacity
    carrying_capacity: int = 0
    current_weight: int = 0

    # Hidden stats
    base_miss_chance: int = 0  # per class/level, doesn't reset on class change until exceeded
    mana_recovery_rate: int = 0  # determined at character creation

    def is_alive(self) -> bool:
        return not bool(self.conditions & Condition.DEAD)

    def is_active(self) -> bool:
        """Can this character act in combat?"""
        blocking = (
            Condition.DEAD
            | Condition.STONED
            | Condition.PARALYZED
            | Condition.ASLEEP
        )
        return not bool(self.conditions & blocking)

    @property
    def stats(self) -> dict[int, int]:
        """Return all 7 ability scores as a dict keyed by Ability enum value."""
        from bane.data.enums import Ability
        return {
            Ability.STRENGTH: self.strength,
            Ability.INTELLIGENCE: self.intelligence,
            Ability.PIETY: self.piety,
            Ability.VITALITY: self.vitality,
            Ability.DEXTERITY: self.dexterity,
            Ability.SPEED: self.speed,
            Ability.PERSONALITY: self.personality,
        }


# ---------------------------------------------------------------------------
# Map / Maze Data
# ---------------------------------------------------------------------------
@dataclass
class TileData:
    """Data for a single map tile."""

    x: int = 0
    y: int = 0
    # Walls for each direction (2-bit encoding)
    north_wall: WallType = WallType.NONE
    south_wall: WallType = WallType.NONE
    east_wall: WallType = WallType.NONE
    west_wall: WallType = WallType.NONE
    # Floor/ceiling
    floor_texture: int = 0
    ceiling_texture: int = 0
    # Special properties
    special: TileSpecial = TileSpecial.NONE
    special_param: int = 0  # e.g., destination level for stairs/teleporter
    # Encounter data
    encounter_chance: int = 0  # 0-100, probability of random encounter per step
    fixed_encounter_id: int | None = None
    # Event
    event_id: int | None = None
    # Texture zone
    texture_zone: int = 0

    def get_wall(self, direction: Direction) -> WallType:
        """Get the wall type for a given direction."""
        return {
            Direction.NORTH: self.north_wall,
            Direction.SOUTH: self.south_wall,
            Direction.EAST: self.east_wall,
            Direction.WEST: self.west_wall,
        }[direction]

    def is_passable(self, direction: Direction) -> bool:
        """Check if the player can move through this wall."""
        wall = self.get_wall(direction)
        return wall in (WallType.NONE, WallType.DOOR)


@dataclass
class DungeonLevel:
    """A single level of the dungeon."""

    level_id: int = 0
    name: str = ""
    width: int = 0
    height: int = 0
    tiles: list[list[TileData]] = field(default_factory=list)  # [y][x]
    texture_palette: int = 0

    def get_tile(self, x: int, y: int) -> TileData | None:
        """Get the tile at (x, y), or None if out of bounds."""
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.tiles[y][x]
        return None


@dataclass
class MapEventDef:
    """An event trigger at a specific map location."""

    event_id: int = 0
    level: int = 0
    x: int = 0
    y: int = 0
    event_type: int = 0  # to be mapped to specific event types
    condition_flags: int = 0
    action_data: bytes = field(default_factory=bytes)


# ---------------------------------------------------------------------------
# Save Game State (from SAVEGAME.DBS)
# ---------------------------------------------------------------------------
@dataclass
class SaveGameData:
    """Game state data from SAVEGAME.DBS."""

    # Party position
    current_level: int = 0
    position_x: int = 0
    position_y: int = 0
    facing: Direction = Direction.NORTH

    # Party members (indices into character list)
    party_member_ids: list[int] = field(default_factory=list)

    # World state
    quest_flags: dict[int, int] = field(default_factory=dict)
    chests_opened: set[int] = field(default_factory=set)
    doors_opened: set[int] = field(default_factory=set)
    npcs_met: set[int] = field(default_factory=set)

    # Time
    game_time: int = 0  # in-game time counter
    total_steps: int = 0


# ---------------------------------------------------------------------------
# Scenario Data (aggregated from SCENARIO.DBS)
# ---------------------------------------------------------------------------
@dataclass
class ScenarioData:
    """All game data parsed from SCENARIO.DBS."""

    monsters: dict[int, MonsterDef] = field(default_factory=dict)
    items: dict[int, ItemDef] = field(default_factory=dict)
    spells: dict[int, SpellDef] = field(default_factory=dict)
    loot_tables: dict[int, LootTable] = field(default_factory=dict)
    races: dict[Race, RaceDef] = field(default_factory=dict)
    professions: dict[Profession, ProfessionDef] = field(default_factory=dict)
    dungeon_levels: dict[int, DungeonLevel] = field(default_factory=dict)
    events: dict[int, MapEventDef] = field(default_factory=dict)
