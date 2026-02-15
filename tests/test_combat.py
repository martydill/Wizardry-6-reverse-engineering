"""Tests for the combat system."""

import random

from bane.data.enums import AttackMode, CombatAction, Condition, Profession, Race, Sex, Skill
from bane.data.models import CharacterData, MonsterDef
from bane.game.character import CharacterSystem
from bane.game.combat import CombatActionData, CombatEngine, MonsterGroup


def make_test_character(name: str = "Hero", level: int = 5) -> CharacterData:
    system = CharacterSystem()
    stats = {a: 12 for a in range(7)}
    from bane.data.enums import Ability
    stats_typed = {Ability(k): v for k, v in stats.items()}
    char = system.create_character(name, Race.HUMAN, Sex.MALE, Profession.FIGHTER, stats_typed)
    for _ in range(level - 1):
        system.level_up(char)
    char.skills[Skill.SWORD] = 30
    return char


def make_test_monster(name: str = "Goblin", hp: int = 10) -> MonsterDef:
    return MonsterDef(
        id=1,
        name=name,
        level=2,
        hp_min=hp,
        hp_max=hp,
        ac={mode: 0 for mode in AttackMode},
        xp_reward=50,
        gold_min=5,
        gold_max=10,
        num_attacks=1,
        damage_min=1,
        damage_max=4,
        attack_mode=AttackMode.PHYSICAL,
        resistances={mode: 0 for mode in AttackMode},
    )


class TestCombatSetup:
    def test_create_combat(self):
        party = [make_test_character("Hero")]
        groups = [MonsterGroup(make_test_monster(), count=2, group_id=0)]
        combat = CombatEngine(party, groups)
        assert not combat.is_over
        assert combat.round_number == 0
        assert len(combat.get_all_alive_monsters()) == 2

    def test_monster_group(self):
        monster_def = make_test_monster("Rat", hp=5)
        group = MonsterGroup(monster_def, count=3, group_id=0)
        assert group.alive_count == 3
        assert not group.is_defeated
        assert group.name == "Rat"


class TestCombatExecution:
    def test_attack_round(self):
        random.seed(42)
        party = [make_test_character("Hero", level=10)]
        groups = [MonsterGroup(make_test_monster("Rat", hp=5), count=1, group_id=0)]
        combat = CombatEngine(party, groups)

        actions = [CombatActionData(action=CombatAction.ATTACK, actor_index=0)]
        results = combat.execute_round(actions)
        assert combat.round_number == 1
        assert len(results) > 0

    def test_combat_ends_when_monsters_die(self):
        random.seed(42)
        party = [make_test_character("Hero", level=20)]
        party[0].strength = 50  # Overpowered for testing
        groups = [MonsterGroup(make_test_monster("Rat", hp=1), count=1, group_id=0)]
        combat = CombatEngine(party, groups)

        # Run rounds until combat ends
        for _ in range(10):
            if combat.is_over:
                break
            actions = [CombatActionData(action=CombatAction.ATTACK, actor_index=0)]
            combat.execute_round(actions)

        assert combat.is_over

    def test_flee(self):
        random.seed(42)
        party = [make_test_character("Coward")]
        party[0].speed = 100  # Very fast = high flee chance
        groups = [MonsterGroup(make_test_monster(), count=1, group_id=0)]
        combat = CombatEngine(party, groups)

        # Try fleeing multiple times
        for _ in range(10):
            if combat.is_over:
                break
            actions = [CombatActionData(action=CombatAction.FLEE, actor_index=0)]
            combat.execute_round(actions)

        assert combat.fled

    def test_defend_action(self):
        party = [make_test_character()]
        groups = [MonsterGroup(make_test_monster(), count=1, group_id=0)]
        combat = CombatEngine(party, groups)
        actions = [CombatActionData(action=CombatAction.PARRY, actor_index=0)]
        results = combat.execute_round(actions)
        # Should have at least the defend result
        assert any("defends" in r.message for r in results)


class TestCombatRewards:
    def test_calculate_rewards(self):
        party = [make_test_character()]
        monster_def = make_test_monster()
        monster_def.xp_reward = 100
        monster_def.gold_min = 10
        monster_def.gold_max = 20
        groups = [MonsterGroup(monster_def, count=2, group_id=0)]
        combat = CombatEngine(party, groups)

        # Kill all monsters
        for m in combat.get_all_alive_monsters():
            m.hp = 0
            m.conditions |= Condition.DEAD

        xp, gold = combat.calculate_rewards()
        assert xp == 200  # 2 monsters × 100 XP
        assert 20 <= gold <= 40  # 2 monsters × 10-20 gold
