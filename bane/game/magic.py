"""Magic system — spell casting, effects, and management.

Implements Wizardry 6's 4 spell schools (Mage, Priest, Alchemist, Psionic)
with 7 power levels each, skill-threshold unlocking, and spell effects.
"""

from __future__ import annotations

import logging
import random

from bane.data.enums import (
    AttackMode,
    Condition,
    Profession,
    Skill,
    SpellSchool,
    SpellTarget,
    SPELL_LEVEL_THRESHOLDS,
)
from bane.data.models import CharacterData, MonsterDef, SpellDef
from bane.game.combat import MonsterInstance

logger = logging.getLogger(__name__)

# Map spell schools to their governing skill
SCHOOL_SKILL_MAP: dict[SpellSchool, Skill] = {
    SpellSchool.MAGE: Skill.THAUMATURGY,
    SpellSchool.PRIEST: Skill.THEOLOGY,
    SpellSchool.ALCHEMIST: Skill.ALCHEMY,
    SpellSchool.PSIONIC: Skill.THEOSOPHY,
}

# Classes that can use each spell school
SCHOOL_CLASS_MAP: dict[SpellSchool, set[Profession]] = {
    SpellSchool.MAGE: {
        Profession.MAGE, Profession.BISHOP, Profession.SAMURAI,
    },
    SpellSchool.PRIEST: {
        Profession.PRIEST, Profession.BISHOP, Profession.LORD, Profession.VALKYRIE,
    },
    SpellSchool.ALCHEMIST: {
        Profession.ALCHEMIST, Profession.BISHOP, Profession.NINJA, Profession.RANGER,
    },
    SpellSchool.PSIONIC: {
        Profession.PSIONIC, Profession.BISHOP, Profession.MONK, Profession.BARD,
    },
}


class MagicSystem:
    """Handles spell casting, effects, and spell management."""

    def __init__(self, spell_defs: dict[int, SpellDef] | None = None) -> None:
        self._spell_defs = spell_defs or {}

    def get_spell(self, spell_id: int) -> SpellDef | None:
        return self._spell_defs.get(spell_id)

    def can_cast(self, caster: CharacterData, spell: SpellDef) -> tuple[bool, str]:
        """Check if a character can cast a specific spell."""
        # Check class access to school
        allowed_classes = SCHOOL_CLASS_MAP.get(spell.school, set())
        if caster.profession not in allowed_classes:
            # Check if they learned it from a previous class (retained spells)
            school_spells = caster.spells_known.get(spell.school, [])
            if spell.id >= len(school_spells) or not school_spells[spell.id]:
                return False, f"{caster.profession.name} cannot cast {spell.school.name} spells"

        # Check skill level meets spell level threshold
        skill = SCHOOL_SKILL_MAP.get(spell.school)
        if skill:
            skill_level = caster.skills.get(skill, 0)
            required = SPELL_LEVEL_THRESHOLDS.get(spell.level, 0)
            if skill_level < required:
                return False, f"Need {skill.name} skill {required}, have {skill_level}"

        # Check SP
        if caster.sp_current < spell.sp_cost:
            return False, f"Not enough SP ({caster.sp_current}/{spell.sp_cost})"

        # Check silence (Alchemy is immune to silence)
        if (
            caster.conditions & Condition.SILENCED
            and spell.school != SpellSchool.ALCHEMIST
        ):
            return False, "Silenced!"

        return True, ""

    def cast_spell(
        self,
        caster: CharacterData,
        spell: SpellDef,
        targets: list[CharacterData | MonsterInstance],
    ) -> list[dict]:
        """Cast a spell and apply its effects. Returns list of result dicts."""
        # Deduct SP
        caster.sp_current -= spell.sp_cost
        results: list[dict] = []

        # Spell failure / backfire check (based on Oratory skill)
        if spell.school != SpellSchool.ALCHEMIST:
            oratory = caster.skills.get(Skill.ORATORY, 0)
            fail_chance = max(0, 30 - oratory)
            if random.randint(1, 100) <= fail_chance:
                results.append({
                    "type": "backfire",
                    "caster": caster.name,
                    "message": f"{caster.name}'s spell fizzles!",
                })
                return results

        # Calculate spell power (scales with skill level)
        skill = SCHOOL_SKILL_MAP.get(spell.school)
        skill_level = caster.skills.get(skill, 0) if skill else 0
        power_multiplier = 1.0 + skill_level / 100.0

        for target in targets:
            result = self._apply_spell_effect(spell, caster, target, power_multiplier)
            results.append(result)

        return results

    def _apply_spell_effect(
        self,
        spell: SpellDef,
        caster: CharacterData,
        target: CharacterData | MonsterInstance,
        power_mult: float,
    ) -> dict:
        """Apply a spell's effect to a single target."""
        target_name = target.name if isinstance(target, MonsterInstance) else target.name

        # Damage spells
        if spell.damage_max > 0:
            base_damage = random.randint(spell.damage_min, spell.damage_max)
            level_bonus = spell.damage_per_level * caster.level
            total_damage = int((base_damage + level_bonus) * power_mult)

            # Check resistance
            if spell.attack_mode is not None:
                if isinstance(target, MonsterInstance):
                    resist = target.definition.resistances.get(spell.attack_mode, 0)
                else:
                    resist = target.resistances.get(spell.attack_mode, 0)
                total_damage = int(total_damage * (100 - resist) / 100)

            total_damage = max(0, total_damage)

            if isinstance(target, MonsterInstance):
                target.hp -= total_damage
                killed = target.hp <= 0
                if killed:
                    target.conditions |= Condition.DEAD
            else:
                target.hp_current -= total_damage
                killed = target.hp_current <= 0
                if killed:
                    target.hp_current = 0
                    target.conditions |= Condition.DEAD

            return {
                "type": "damage",
                "caster": caster.name,
                "target": target_name,
                "damage": total_damage,
                "killed": killed,
                "message": (
                    f"{caster.name} casts {spell.name} on {target_name} "
                    f"for {total_damage} damage!"
                ),
            }

        # Healing spells (negative damage = healing)
        if spell.target_type in (SpellTarget.SELF, SpellTarget.SINGLE_ALLY, SpellTarget.ALL_ALLIES):
            if isinstance(target, CharacterData):
                heal_amount = random.randint(
                    max(1, spell.damage_min), max(1, spell.damage_max)
                )
                heal_amount = int(heal_amount * power_mult)
                target.hp_current = min(target.hp_max, target.hp_current + heal_amount)
                return {
                    "type": "heal",
                    "caster": caster.name,
                    "target": target_name,
                    "amount": heal_amount,
                    "message": f"{caster.name} casts {spell.name}, healing {target_name} for {heal_amount}!",
                }

        # Status effect spells
        if spell.status_effect != Condition.NONE:
            # Resistance check
            save_chance = 50
            if isinstance(target, MonsterInstance):
                save_chance += target.definition.level * 2
            else:
                save_chance += target.level * 2

            if random.randint(1, 100) > save_chance:
                if isinstance(target, MonsterInstance):
                    target.conditions |= spell.status_effect
                else:
                    target.conditions |= spell.status_effect
                return {
                    "type": "status",
                    "caster": caster.name,
                    "target": target_name,
                    "effect": spell.status_effect.name,
                    "message": f"{caster.name} casts {spell.name}! {target_name} is {spell.status_effect.name}!",
                }
            else:
                return {
                    "type": "resist",
                    "caster": caster.name,
                    "target": target_name,
                    "message": f"{caster.name} casts {spell.name} but {target_name} resists!",
                }

        return {
            "type": "misc",
            "caster": caster.name,
            "message": f"{caster.name} casts {spell.name}.",
        }

    def get_castable_spells(
        self, caster: CharacterData
    ) -> dict[SpellSchool, list[SpellDef]]:
        """Get all spells a character can currently cast, organized by school."""
        result: dict[SpellSchool, list[SpellDef]] = {}
        for school in SpellSchool:
            castable = []
            for spell in self._spell_defs.values():
                if spell.school == school:
                    can, _ = self.can_cast(caster, spell)
                    if can:
                        castable.append(spell)
            if castable:
                result[school] = sorted(castable, key=lambda s: (s.level, s.id))
        return result
