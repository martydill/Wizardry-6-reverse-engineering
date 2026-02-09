"""Tests for character creation, leveling, and class changing."""

from bane.data.enums import Ability, Profession, Race, Sex, Skill, SpellSchool
from bane.game.character import CharacterSystem, CLASS_REQUIREMENTS, RACE_BASE_STATS


class TestCharacterCreation:
    def setup_method(self):
        self.system = CharacterSystem()

    def test_get_base_stats_human(self):
        stats = self.system.get_base_stats(Race.HUMAN)
        assert stats[Ability.STRENGTH] == 9
        assert len(stats) == 7

    def test_get_base_stats_all_races(self):
        for race in Race:
            stats = self.system.get_base_stats(race)
            assert len(stats) == 7
            for val in stats.values():
                assert 1 <= val <= 20

    def test_fighter_no_requirements(self):
        stats = {a: 8 for a in Ability}
        assert self.system.can_select_class(stats, Profession.FIGHTER)

    def test_mage_requires_intelligence(self):
        low_stats = {a: 8 for a in Ability}
        assert not self.system.can_select_class(low_stats, Profession.MAGE)

        high_stats = {a: 8 for a in Ability}
        high_stats[Ability.INTELLIGENCE] = 11
        assert self.system.can_select_class(high_stats, Profession.MAGE)

    def test_ninja_requires_many_stats(self):
        low_stats = {a: 8 for a in Ability}
        assert not self.system.can_select_class(low_stats, Profession.NINJA)

        reqs = CLASS_REQUIREMENTS[Profession.NINJA]
        high_stats = {a: 15 for a in Ability}
        assert self.system.can_select_class(high_stats, Profession.NINJA)

    def test_get_available_classes(self):
        # With all 8s, only Fighter should be available
        low_stats = {a: 8 for a in Ability}
        available = self.system.get_available_classes(low_stats)
        assert Profession.FIGHTER in available
        assert Profession.NINJA not in available

        # With all 18s, all classes should be available
        high_stats = {a: 18 for a in Ability}
        available = self.system.get_available_classes(high_stats)
        assert len(available) == 14

    def test_create_character(self):
        stats = {a: 12 for a in Ability}
        char = self.system.create_character(
            name="Testchar",
            race=Race.HUMAN,
            sex=Sex.MALE,
            profession=Profession.FIGHTER,
            stats=stats,
        )
        assert char.name == "Testchar"
        assert char.race == Race.HUMAN
        assert char.sex == Sex.MALE
        assert char.profession == Profession.FIGHTER
        assert char.level == 1
        assert char.hp_current == char.hp_max
        assert char.hp_max > 0
        assert char.experience == 0
        assert char.strength == 12
        assert len(char.skills) == len(Skill)

    def test_mana_recovery_rate(self):
        stats = {a: 15 for a in Ability}
        mage = self.system.create_character("Mage", Race.ELF, Sex.FEMALE, Profession.MAGE, stats)
        fighter = self.system.create_character("Fighter", Race.HUMAN, Sex.MALE, Profession.FIGHTER, stats)
        assert mage.mana_recovery_rate > fighter.mana_recovery_rate


class TestLevelUp:
    def setup_method(self):
        self.system = CharacterSystem()
        stats = {a: 12 for a in Ability}
        self.char = self.system.create_character("Hero", Race.HUMAN, Sex.MALE, Profession.FIGHTER, stats)

    def test_level_increases(self):
        old_level = self.char.level
        changes = self.system.level_up(self.char)
        assert self.char.level == old_level + 1
        assert changes["level"] == old_level + 1

    def test_hp_increases(self):
        old_hp = self.char.hp_max
        changes = self.system.level_up(self.char)
        assert self.char.hp_max > old_hp
        assert changes["hp"] > 0

    def test_skill_points_awarded(self):
        changes = self.system.level_up(self.char)
        assert changes["skill_points"] > 0


class TestClassChange:
    def setup_method(self):
        self.system = CharacterSystem()
        stats = {a: 15 for a in Ability}
        self.char = self.system.create_character("Multi", Race.HUMAN, Sex.MALE, Profession.FIGHTER, stats)
        # Level up a few times
        for _ in range(5):
            self.system.level_up(self.char)

    def test_class_change_resets_level(self):
        old_level = self.char.level
        assert old_level > 1
        self.system.change_class(self.char, Profession.MAGE)
        assert self.char.level == 1
        assert self.char.profession == Profession.MAGE

    def test_class_change_increments_rebirths(self):
        assert self.char.rebirths == 0
        self.system.change_class(self.char, Profession.MAGE)
        assert self.char.rebirths == 1
        self.system.change_class(self.char, Profession.PRIEST)
        assert self.char.rebirths == 2

    def test_class_change_halves_hp(self):
        old_hp = self.char.hp_max
        self.system.change_class(self.char, Profession.THIEF)
        assert self.char.hp_max < old_hp
        assert self.char.hp_max >= 1


class TestSpellAccess:
    def setup_method(self):
        self.system = CharacterSystem()

    def test_no_spells_at_zero_skill(self):
        stats = {a: 15 for a in Ability}
        char = self.system.create_character("Mage", Race.ELF, Sex.MALE, Profession.MAGE, stats)
        # Skill level 0 should give level 1 spells only
        available = self.system.get_available_spells(char, SpellSchool.MAGE)
        assert 1 in available
        assert 2 not in available

    def test_spells_unlock_at_thresholds(self):
        stats = {a: 15 for a in Ability}
        char = self.system.create_character("Mage", Race.ELF, Sex.MALE, Profession.MAGE, stats)
        char.skills[Skill.THAUMATURGY] = 36
        available = self.system.get_available_spells(char, SpellSchool.MAGE)
        assert 1 in available
        assert 2 in available
        assert 3 in available
        assert 4 not in available

    def test_all_spells_at_98(self):
        stats = {a: 15 for a in Ability}
        char = self.system.create_character("Mage", Race.ELF, Sex.MALE, Profession.MAGE, stats)
        char.skills[Skill.THAUMATURGY] = 98
        available = self.system.get_available_spells(char, SpellSchool.MAGE)
        assert available == [1, 2, 3, 4, 5, 6, 7]
