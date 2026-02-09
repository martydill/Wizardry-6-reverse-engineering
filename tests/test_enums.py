"""Tests for game enumerations."""

from bane.data.enums import Direction, Race, Profession, WallType, Ability


class TestDirection:
    def test_turn_left(self):
        assert Direction.NORTH.turn_left() == Direction.WEST
        assert Direction.WEST.turn_left() == Direction.SOUTH
        assert Direction.SOUTH.turn_left() == Direction.EAST
        assert Direction.EAST.turn_left() == Direction.NORTH

    def test_turn_right(self):
        assert Direction.NORTH.turn_right() == Direction.EAST
        assert Direction.EAST.turn_right() == Direction.SOUTH
        assert Direction.SOUTH.turn_right() == Direction.WEST
        assert Direction.WEST.turn_right() == Direction.NORTH

    def test_reverse(self):
        assert Direction.NORTH.reverse() == Direction.SOUTH
        assert Direction.EAST.reverse() == Direction.WEST

    def test_dx_dy(self):
        assert Direction.NORTH.dx == 0 and Direction.NORTH.dy == -1
        assert Direction.SOUTH.dx == 0 and Direction.SOUTH.dy == 1
        assert Direction.EAST.dx == 1 and Direction.EAST.dy == 0
        assert Direction.WEST.dx == -1 and Direction.WEST.dy == 0

    def test_full_rotation(self):
        d = Direction.NORTH
        for _ in range(4):
            d = d.turn_right()
        assert d == Direction.NORTH


class TestRaces:
    def test_all_11_races(self):
        assert len(Race) == 11
        assert Race.HUMAN.value == 0
        assert Race.MOOK.value == 10

    def test_race_names(self):
        assert Race.DRACON.name == "DRACON"
        assert Race.FELPURR.name == "FELPURR"


class TestProfessions:
    def test_all_14_classes(self):
        assert len(Profession) == 14
        assert Profession.FIGHTER.value == 0
        assert Profession.NINJA.value == 13

    def test_base_classes(self):
        base = [Profession.FIGHTER, Profession.MAGE, Profession.PRIEST, Profession.THIEF]
        for p in base:
            assert p.value < 8

    def test_elite_classes(self):
        elite = [
            Profession.VALKYRIE, Profession.BISHOP,
            Profession.LORD, Profession.SAMURAI,
            Profession.MONK, Profession.NINJA,
        ]
        for p in elite:
            assert p.value >= 8
