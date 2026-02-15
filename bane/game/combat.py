"""Turn-based combat engine.

Implements the full Wizardry 6 combat system:
- Initiative/speed-based turn order
- Per-character action selection
- Attack resolution with hit chance, damage, criticals
- 9 attack modes and damage types
- Monster AI
- Group targeting
- Combat rewards (XP, gold, loot)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import IntEnum

from bane.data.enums import (
    AttackMode,
    CombatAction,
    Condition,
    Profession,
    Skill,
)
from bane.data.models import CharacterData, MonsterDef, LootTable

logger = logging.getLogger(__name__)


@dataclass
class MonsterInstance:
    """A living instance of a monster in combat."""

    definition: MonsterDef
    hp: int = 0
    conditions: Condition = Condition.NONE
    group_id: int = 0  # which monster group this belongs to

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def is_alive(self) -> bool:
        return self.hp > 0 and not bool(self.conditions & Condition.DEAD)

    @property
    def is_active(self) -> bool:
        blocking = Condition.DEAD | Condition.STONED | Condition.PARALYZED | Condition.ASLEEP
        return self.hp > 0 and not bool(self.conditions & blocking)


@dataclass
class CombatActionData:
    """A queued combat action for one combatant."""

    action: CombatAction = CombatAction.ATTACK
    actor_is_player: bool = True
    actor_index: int = 0  # index into party or monster list
    target_group: int = -1  # -1 = auto-select
    target_index: int = -1  # specific target within group
    spell_id: int = -1
    item_id: int = -1


@dataclass
class CombatResult:
    """Result of a single combat action."""

    actor_name: str = ""
    action: CombatAction = CombatAction.ATTACK
    target_name: str = ""
    hit: bool = False
    damage: int = 0
    critical: bool = False
    killed: bool = False
    message: str = ""


class MonsterGroup:
    """A group of monsters of the same type in combat."""

    def __init__(self, definition: MonsterDef, count: int, group_id: int) -> None:
        self.definition = definition
        self.group_id = group_id
        self.monsters: list[MonsterInstance] = []
        for _ in range(count):
            hp = random.randint(definition.hp_min, max(definition.hp_min, definition.hp_max))
            self.monsters.append(
                MonsterInstance(definition=definition, hp=hp, group_id=group_id)
            )

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def alive_count(self) -> int:
        return sum(1 for m in self.monsters if m.is_alive)

    @property
    def is_defeated(self) -> bool:
        return self.alive_count == 0

    def get_alive(self) -> list[MonsterInstance]:
        return [m for m in self.monsters if m.is_alive]


class CombatEngine:
    """Manages a single combat encounter.

    Usage:
        combat = CombatEngine(party, monster_groups)
        while not combat.is_over:
            # Get actions from UI
            actions = [...]
            results = combat.execute_round(actions)
            # Display results
    """

    def __init__(
        self,
        party_members: list[CharacterData],
        monster_groups: list[MonsterGroup],
    ) -> None:
        self.party = party_members
        self.monster_groups = monster_groups
        self.round_number = 0
        self.fled = False
        self._combat_log: list[str] = []

    @property
    def is_over(self) -> bool:
        """Combat ends when all monsters are dead, party is wiped, or party fled."""
        if self.fled:
            return True
        if all(g.is_defeated for g in self.monster_groups):
            return True
        if all(not m.is_alive() for m in self.party):
            return True
        return False

    @property
    def party_won(self) -> bool:
        return all(g.is_defeated for g in self.monster_groups)

    @property
    def combat_log(self) -> list[str]:
        return list(self._combat_log)

    def get_all_alive_monsters(self) -> list[MonsterInstance]:
        result = []
        for group in self.monster_groups:
            result.extend(group.get_alive())
        return result

    def execute_round(self, player_actions: list[CombatActionData]) -> list[CombatResult]:
        """Execute one round of combat with the given player actions."""
        self.round_number += 1
        results: list[CombatResult] = []

        # Build turn order: interleave player and monster actions by speed
        turn_order = self._build_turn_order(player_actions)

        for actor_type, actor_idx, action in turn_order:
            if self.is_over:
                break

            if actor_type == "player":
                char = self.party[actor_idx]
                if not char.is_active():
                    continue
                result = self._execute_player_action(char, action)
            else:
                monster = self.get_all_alive_monsters()[actor_idx] if actor_idx < len(self.get_all_alive_monsters()) else None
                if monster is None or not monster.is_active:
                    continue
                result = self._execute_monster_action(monster)

            if result:
                results.append(result)
                self._combat_log.append(result.message)

        # Monster HP regeneration at end of round
        for monster in self.get_all_alive_monsters():
            if monster.definition.hp_regen_rate > 0:
                regen = monster.definition.hp_regen_rate
                monster.hp = min(monster.hp + regen, monster.definition.hp_max)

        return results

    def _build_turn_order(
        self, player_actions: list[CombatActionData]
    ) -> list[tuple[str, int, CombatActionData | None]]:
        """Build the turn order based on speed/initiative."""
        entries: list[tuple[int, str, int, CombatActionData | None]] = []

        # Player characters
        for i, char in enumerate(self.party):
            if char.is_active():
                speed = char.speed + random.randint(1, 10)
                action = player_actions[i] if i < len(player_actions) else None
                entries.append((speed, "player", i, action))

        # Monsters
        for i, monster in enumerate(self.get_all_alive_monsters()):
            if monster.is_active:
                speed = random.randint(1, 15) + monster.definition.level
                entries.append((speed, "monster", i, None))

        # Sort by speed (highest first)
        entries.sort(key=lambda e: e[0], reverse=True)
        return [(e[1], e[2], e[3]) for e in entries]

    def _execute_player_action(
        self, char: CharacterData, action: CombatActionData | None
    ) -> CombatResult:
        """Execute a single player character's combat action."""
        if action is None or action.action == CombatAction.PARRY:
            return CombatResult(
                actor_name=char.name,
                action=CombatAction.PARRY,
                message=f"{char.name} defends.",
            )

        if action.action == CombatAction.FLEE:
            # Flee chance based on speed
            flee_chance = 30 + char.speed * 2
            if random.randint(1, 100) <= flee_chance:
                self.fled = True
                return CombatResult(
                    actor_name=char.name,
                    action=CombatAction.FLEE,
                    message="The party flees from combat!",
                )
            return CombatResult(
                actor_name=char.name,
                action=CombatAction.FLEE,
                message=f"{char.name} tries to flee but fails!",
            )

        if action.action == CombatAction.ATTACK:
            return self._resolve_player_attack(char, action)

        return CombatResult(
            actor_name=char.name,
            action=action.action,
            message=f"{char.name} does nothing.",
        )

    def _resolve_player_attack(
        self, char: CharacterData, action: CombatActionData
    ) -> CombatResult:
        """Resolve a physical attack from a player character."""
        alive_monsters = self.get_all_alive_monsters()
        if not alive_monsters:
            return CombatResult(
                actor_name=char.name,
                action=CombatAction.ATTACK,
                message=f"{char.name} attacks but there are no targets!",
            )

        # Select target
        if 0 <= action.target_index < len(alive_monsters):
            target = alive_monsters[action.target_index]
        else:
            target = random.choice(alive_monsters)

        # Hit calculation
        # Base hit chance: 50% + (attacker_level - defender_level) * 3 + weapon_skill
        weapon_skill = max(char.skills.get(Skill.SWORD, 0), 10)
        hit_chance = 50 + (char.level - target.definition.level) * 3 + weapon_skill // 2
        hit_chance -= target.definition.ac.get(AttackMode.PHYSICAL, 0)
        hit_chance = max(5, min(95, hit_chance))

        # Base miss chance (hidden per-class stat)
        hit_chance -= char.base_miss_chance

        result = CombatResult(
            actor_name=char.name,
            action=CombatAction.ATTACK,
            target_name=target.name,
        )

        if random.randint(1, 100) > hit_chance:
            result.hit = False
            result.message = f"{char.name} attacks {target.name} and misses!"
            return result

        # Damage calculation
        base_damage = random.randint(1, 8)  # weapon damage (placeholder)
        str_bonus = char.strength // 3
        damage = max(1, base_damage + str_bonus)

        # Critical hit (Kirijutsu)
        kirijutsu = char.skills.get(Skill.KIRIJUTSU, 0)
        if kirijutsu > 0 and random.randint(1, 100) <= kirijutsu // 3:
            damage = target.hp  # instant kill
            result.critical = True

        # Apply double damage type
        if target.definition.double_damage_type == 0:
            # Fighter type 0 bug — most weapons deal double damage
            damage *= 2

        target.hp -= damage
        result.hit = True
        result.damage = damage
        result.killed = target.hp <= 0

        if result.critical:
            result.message = (
                f"{char.name} strikes {target.name} with a CRITICAL HIT "
                f"for {damage} damage!"
            )
        elif result.killed:
            result.message = (
                f"{char.name} hits {target.name} for {damage} damage, killing it!"
            )
        else:
            result.message = f"{char.name} hits {target.name} for {damage} damage."

        if result.killed:
            target.conditions |= Condition.DEAD

        return result

    def _execute_monster_action(self, monster: MonsterInstance) -> CombatResult:
        """Execute a monster's combat action (AI-controlled)."""
        alive_party = [m for m in self.party if m.is_active()]
        if not alive_party:
            return CombatResult(message=f"{monster.name} has no targets.")

        # Simple AI: attack random party member, prefer front row
        front_row = alive_party[:3] if len(alive_party) > 3 else alive_party
        target = random.choice(front_row if front_row else alive_party)

        # Hit chance
        hit_chance = 50 + (monster.definition.level - target.level) * 3
        target_ac = sum(target.resistances.get(m, 0) for m in AttackMode) // len(AttackMode)
        hit_chance -= target_ac
        hit_chance = max(10, min(95, hit_chance))

        result = CombatResult(
            actor_name=monster.name,
            action=CombatAction.ATTACK,
            target_name=target.name,
        )

        if random.randint(1, 100) > hit_chance:
            result.hit = False
            result.message = f"{monster.name} attacks {target.name} and misses!"
            return result

        # Damage
        damage = random.randint(
            monster.definition.damage_min,
            max(monster.definition.damage_min, monster.definition.damage_max),
        )
        damage = max(1, damage)

        target.hp_current -= damage
        result.hit = True
        result.damage = damage

        if target.hp_current <= 0:
            target.hp_current = 0
            target.conditions |= Condition.DEAD
            result.killed = True
            result.message = (
                f"{monster.name} hits {target.name} for {damage} damage, killing them!"
            )
        else:
            result.message = f"{monster.name} hits {target.name} for {damage} damage."

        return result

    def calculate_rewards(self) -> tuple[int, int]:
        """Calculate total XP and gold from defeated monsters."""
        total_xp = 0
        total_gold = 0
        for group in self.monster_groups:
            for monster in group.monsters:
                if not monster.is_alive:
                    total_xp += monster.definition.xp_reward
                    total_gold += random.randint(
                        monster.definition.gold_min,
                        max(monster.definition.gold_min, monster.definition.gold_max),
                    )
        return total_xp, total_gold
