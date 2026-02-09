"""Character system — creation, progression, class changing.

Implements the full Wizardry 6 character model:
- 11 races with stat modifiers, resistances, special abilities
- 14 classes with stat requirements and progression
- Character creation (stat rolling, race/class validation)
- Level-up (HP/STA/SP gains, skill points, spell unlocks)
- Class changing (multiclass with spell retention)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from bane.data.enums import (
    Ability,
    AttackMode,
    Condition,
    EquipSlot,
    Profession,
    Race,
    Sex,
    Skill,
    SpellSchool,
    SPELL_LEVEL_THRESHOLDS,
)
from bane.data.models import CharacterData, ProfessionDef, RaceDef

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Race base stats — used when game data files are not available
# These are reference values from community documentation.
# When SCENARIO.DBS is loaded, these are overridden by parsed RaceDef data.
# ---------------------------------------------------------------------------
RACE_BASE_STATS: dict[Race, dict[Ability, int]] = {
    Race.HUMAN: {
        Ability.STRENGTH: 9, Ability.INTELLIGENCE: 9, Ability.PIETY: 9,
        Ability.VITALITY: 9, Ability.DEXTERITY: 9, Ability.SPEED: 9,
        Ability.PERSONALITY: 9,
    },
    Race.ELF: {
        Ability.STRENGTH: 7, Ability.INTELLIGENCE: 10, Ability.PIETY: 10,
        Ability.VITALITY: 7, Ability.DEXTERITY: 9, Ability.SPEED: 9,
        Ability.PERSONALITY: 9,
    },
    Race.DWARF: {
        Ability.STRENGTH: 11, Ability.INTELLIGENCE: 7, Ability.PIETY: 10,
        Ability.VITALITY: 12, Ability.DEXTERITY: 7, Ability.SPEED: 7,
        Ability.PERSONALITY: 7,
    },
    Race.GNOME: {
        Ability.STRENGTH: 10, Ability.INTELLIGENCE: 10, Ability.PIETY: 10,
        Ability.VITALITY: 8, Ability.DEXTERITY: 8, Ability.SPEED: 8,
        Ability.PERSONALITY: 8,
    },
    Race.HOBBIT: {
        Ability.STRENGTH: 6, Ability.INTELLIGENCE: 7, Ability.PIETY: 7,
        Ability.VITALITY: 8, Ability.DEXTERITY: 11, Ability.SPEED: 9,
        Ability.PERSONALITY: 11,
    },
    Race.FAERIE: {
        Ability.STRENGTH: 5, Ability.INTELLIGENCE: 11, Ability.PIETY: 6,
        Ability.VITALITY: 6, Ability.DEXTERITY: 10, Ability.SPEED: 14,
        Ability.PERSONALITY: 12,
    },
    Race.LIZARDMAN: {
        Ability.STRENGTH: 12, Ability.INTELLIGENCE: 5, Ability.PIETY: 5,
        Ability.VITALITY: 14, Ability.DEXTERITY: 8, Ability.SPEED: 8,
        Ability.PERSONALITY: 3,
    },
    Race.DRACON: {
        Ability.STRENGTH: 10, Ability.INTELLIGENCE: 7, Ability.PIETY: 6,
        Ability.VITALITY: 12, Ability.DEXTERITY: 8, Ability.SPEED: 6,
        Ability.PERSONALITY: 6,
    },
    Race.FELPURR: {
        Ability.STRENGTH: 7, Ability.INTELLIGENCE: 8, Ability.PIETY: 7,
        Ability.VITALITY: 7, Ability.DEXTERITY: 12, Ability.SPEED: 12,
        Ability.PERSONALITY: 10,
    },
    Race.RAWULF: {
        Ability.STRENGTH: 8, Ability.INTELLIGENCE: 6, Ability.PIETY: 12,
        Ability.VITALITY: 10, Ability.DEXTERITY: 8, Ability.SPEED: 8,
        Ability.PERSONALITY: 8,
    },
    Race.MOOK: {
        Ability.STRENGTH: 10, Ability.INTELLIGENCE: 10, Ability.PIETY: 6,
        Ability.VITALITY: 10, Ability.DEXTERITY: 8, Ability.SPEED: 8,
        Ability.PERSONALITY: 7,
    },
}

# ---------------------------------------------------------------------------
# Class stat requirements — minimum stats to qualify for each class
# ---------------------------------------------------------------------------
CLASS_REQUIREMENTS: dict[Profession, dict[Ability, int]] = {
    Profession.FIGHTER: {},  # No special requirements
    Profession.MAGE: {Ability.INTELLIGENCE: 11},
    Profession.PRIEST: {Ability.PIETY: 11},
    Profession.THIEF: {Ability.DEXTERITY: 11},
    Profession.RANGER: {Ability.STRENGTH: 11, Ability.INTELLIGENCE: 10, Ability.VITALITY: 10},
    Profession.ALCHEMIST: {Ability.INTELLIGENCE: 11, Ability.DEXTERITY: 10},
    Profession.BARD: {Ability.INTELLIGENCE: 10, Ability.PERSONALITY: 11},
    Profession.PSIONIC: {Ability.INTELLIGENCE: 12, Ability.PERSONALITY: 12},
    Profession.VALKYRIE: {Ability.STRENGTH: 11, Ability.PIETY: 11, Ability.SPEED: 11},
    Profession.BISHOP: {Ability.INTELLIGENCE: 12, Ability.PIETY: 12},
    Profession.LORD: {
        Ability.STRENGTH: 12, Ability.INTELLIGENCE: 10, Ability.PIETY: 10,
        Ability.VITALITY: 10, Ability.DEXTERITY: 10, Ability.SPEED: 10,
        Ability.PERSONALITY: 10,
    },
    Profession.SAMURAI: {
        Ability.STRENGTH: 12, Ability.INTELLIGENCE: 11,
        Ability.VITALITY: 10, Ability.DEXTERITY: 10, Ability.SPEED: 10,
    },
    Profession.MONK: {
        Ability.STRENGTH: 10, Ability.INTELLIGENCE: 10, Ability.PIETY: 10,
        Ability.VITALITY: 10, Ability.DEXTERITY: 12, Ability.SPEED: 10,
    },
    Profession.NINJA: {
        Ability.STRENGTH: 10, Ability.INTELLIGENCE: 10,
        Ability.VITALITY: 10, Ability.DEXTERITY: 12, Ability.SPEED: 10,
        Ability.PERSONALITY: 10,
    },
}

# ---------------------------------------------------------------------------
# Mana recovery base rates per starting class
# ---------------------------------------------------------------------------
MANA_RECOVERY_RATES: dict[Profession, int] = {
    Profession.FIGHTER: 1,
    Profession.MAGE: 5,
    Profession.PRIEST: 5,
    Profession.THIEF: 1,
    Profession.RANGER: 3,
    Profession.ALCHEMIST: 5,
    Profession.BARD: 3,
    Profession.PSIONIC: 5,
    Profession.VALKYRIE: 3,
    Profession.BISHOP: 5,
    Profession.LORD: 3,
    Profession.SAMURAI: 3,
    Profession.MONK: 3,
    Profession.NINJA: 2,
}


class CharacterSystem:
    """Handles character creation, leveling, and class changes."""

    def __init__(
        self,
        race_defs: dict[Race, RaceDef] | None = None,
        profession_defs: dict[Profession, ProfessionDef] | None = None,
    ) -> None:
        self._race_defs = race_defs or {}
        self._profession_defs = profession_defs or {}

    def roll_bonus_points(self) -> int:
        """Roll bonus points for character creation (like the original game)."""
        # Roll 4-24 bonus points (varies by race/class in original)
        return random.randint(5, 20)

    def get_base_stats(self, race: Race) -> dict[Ability, int]:
        """Get base stats for a race."""
        race_def = self._race_defs.get(race)
        if race_def and race_def.stat_modifiers:
            # Use parsed data
            return {Ability(k): v for k, v in race_def.stat_modifiers.items()}
        # Fallback to hardcoded values
        return dict(RACE_BASE_STATS.get(race, RACE_BASE_STATS[Race.HUMAN]))

    def can_select_class(self, stats: dict[Ability, int], profession: Profession) -> bool:
        """Check if stats meet class requirements."""
        reqs = CLASS_REQUIREMENTS.get(profession, {})
        for ability, minimum in reqs.items():
            if stats.get(ability, 0) < minimum:
                return False
        return True

    def get_available_classes(self, stats: dict[Ability, int]) -> list[Profession]:
        """Get all classes the character qualifies for with given stats."""
        return [p for p in Profession if self.can_select_class(stats, p)]

    def create_character(
        self,
        name: str,
        race: Race,
        sex: Sex,
        profession: Profession,
        stats: dict[Ability, int],
        portrait_id: int = 0,
    ) -> CharacterData:
        """Create a new character with the given attributes."""
        char = CharacterData(
            name=name,
            race=race,
            sex=sex,
            profession=profession,
            portrait_id=portrait_id,
            strength=stats.get(Ability.STRENGTH, 8),
            intelligence=stats.get(Ability.INTELLIGENCE, 8),
            piety=stats.get(Ability.PIETY, 8),
            vitality=stats.get(Ability.VITALITY, 8),
            dexterity=stats.get(Ability.DEXTERITY, 8),
            speed=stats.get(Ability.SPEED, 8),
            personality=stats.get(Ability.PERSONALITY, 8),
            level=1,
            experience=0,
            age=18 + random.randint(0, 5),
            gold=0,
            mana_recovery_rate=MANA_RECOVERY_RATES.get(profession, 1),
        )

        # Set initial HP/STA/SP based on class
        prof_def = self._profession_defs.get(profession)
        if prof_def:
            char.hp_max = random.randint(prof_def.hp_per_level_min, prof_def.hp_per_level_max)
            char.stamina_max = random.randint(
                prof_def.stamina_per_level_min, prof_def.stamina_per_level_max
            )
            char.sp_max = random.randint(prof_def.sp_per_level_min, prof_def.sp_per_level_max)
        else:
            # Fallback defaults
            char.hp_max = random.randint(4, 10) + char.vitality // 3
            char.stamina_max = random.randint(2, 6) + char.vitality // 4
            char.sp_max = 0
            if profession in (
                Profession.MAGE, Profession.PRIEST, Profession.ALCHEMIST,
                Profession.PSIONIC, Profession.BISHOP,
            ):
                char.sp_max = random.randint(3, 8) + char.intelligence // 3

        char.hp_current = char.hp_max
        char.stamina_current = char.stamina_max
        char.sp_current = char.sp_max

        # Initialize all skills to 0
        for skill in Skill:
            char.skills[skill] = 0

        # Initialize equipment slots
        for slot in EquipSlot:
            char.equipment[slot] = None

        # Initialize spell schools
        for school in SpellSchool:
            char.spells_known[school] = [False] * 49

        logger.info(
            "Created character: %s (L%d %s %s)",
            char.name, char.level, char.race.name, char.profession.name,
        )
        return char

    def level_up(self, char: CharacterData) -> dict[str, int]:
        """Level up a character. Returns dict of stat changes."""
        char.level += 1
        changes: dict[str, int] = {"level": char.level}

        prof_def = self._profession_defs.get(char.profession)

        # HP gain
        if prof_def:
            hp_gain = random.randint(prof_def.hp_per_level_min, prof_def.hp_per_level_max)
        else:
            hp_gain = random.randint(2, 8)
        hp_gain += char.vitality // 5
        char.hp_max += hp_gain
        char.hp_current += hp_gain
        changes["hp"] = hp_gain

        # Stamina gain
        if prof_def:
            sta_gain = random.randint(
                prof_def.stamina_per_level_min, prof_def.stamina_per_level_max
            )
        else:
            sta_gain = random.randint(1, 4)
        char.stamina_max += sta_gain
        char.stamina_current += sta_gain
        changes["stamina"] = sta_gain

        # SP gain (casters only)
        if prof_def and prof_def.sp_per_level_max > 0:
            sp_gain = random.randint(prof_def.sp_per_level_min, prof_def.sp_per_level_max)
        elif char.sp_max > 0:
            sp_gain = random.randint(1, 4)
        else:
            sp_gain = 0
        if sp_gain > 0:
            char.sp_max += sp_gain
            char.sp_current += sp_gain
            changes["sp"] = sp_gain

        # Skill points to allocate (returned to caller for UI)
        skill_points = 3 + char.intelligence // 5
        changes["skill_points"] = skill_points

        logger.info(
            "%s leveled up to %d: +%d HP, +%d STA, +%d SP, %d skill pts",
            char.name, char.level, hp_gain, sta_gain, sp_gain, skill_points,
        )
        return changes

    def change_class(self, char: CharacterData, new_profession: Profession) -> None:
        """Change a character's class (multiclass).

        - Stats revert to race base values (bonuses from old class are lost)
        - Spells are retained but cast at power level 1 until skill is rebuilt
        - Rebirths counter increments
        - Level resets to 1
        """
        old_profession = char.profession
        char.profession = new_profession
        char.rebirths += 1
        char.level = 1
        char.experience = 0

        # Revert stats to race base + some retained bonus
        base_stats = self.get_base_stats(char.race)
        char.strength = max(base_stats.get(Ability.STRENGTH, 8), char.strength // 2)
        char.intelligence = max(base_stats.get(Ability.INTELLIGENCE, 8), char.intelligence // 2)
        char.piety = max(base_stats.get(Ability.PIETY, 8), char.piety // 2)
        char.vitality = max(base_stats.get(Ability.VITALITY, 8), char.vitality // 2)
        char.dexterity = max(base_stats.get(Ability.DEXTERITY, 8), char.dexterity // 2)
        char.speed = max(base_stats.get(Ability.SPEED, 8), char.speed // 2)
        char.personality = max(base_stats.get(Ability.PERSONALITY, 8), char.personality // 2)

        # HP/STA/SP get halved
        char.hp_max = max(1, char.hp_max // 2)
        char.hp_current = min(char.hp_current, char.hp_max)
        char.stamina_max = max(1, char.stamina_max // 2)
        char.stamina_current = min(char.stamina_current, char.stamina_max)
        # SP depends on new class
        if new_profession not in (
            Profession.MAGE, Profession.PRIEST, Profession.ALCHEMIST,
            Profession.PSIONIC, Profession.BISHOP, Profession.LORD,
            Profession.SAMURAI, Profession.VALKYRIE, Profession.RANGER,
            Profession.BARD, Profession.MONK, Profession.NINJA,
        ):
            char.sp_max = 0
            char.sp_current = 0

        logger.info(
            "%s changed class from %s to %s (rebirth #%d)",
            char.name, old_profession.name, new_profession.name, char.rebirths,
        )

    def get_available_spells(
        self, char: CharacterData, school: SpellSchool
    ) -> list[int]:
        """Get spell level range available based on skill level.

        Returns list of available spell power levels (1-7).
        """
        skill_map = {
            SpellSchool.MAGE: Skill.THAUMATURGY,
            SpellSchool.PRIEST: Skill.THEOLOGY,
            SpellSchool.ALCHEMIST: Skill.ALCHEMY,
            SpellSchool.PSIONIC: Skill.THEOSOPHY,
        }
        skill = skill_map.get(school)
        if skill is None:
            return []

        skill_level = char.skills.get(skill, 0)
        available = []
        for spell_level, threshold in SPELL_LEVEL_THRESHOLDS.items():
            if skill_level >= threshold:
                available.append(spell_level)
        return available
