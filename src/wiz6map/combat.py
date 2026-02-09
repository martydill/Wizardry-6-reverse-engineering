from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Combatant:
    name: str
    hp: int
    attack: int
    defense: int

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def apply_damage(self, amount: int) -> int:
        damage = max(0, amount)
        self.hp = max(0, self.hp - damage)
        return damage


@dataclass
class PartyMember(Combatant):
    pass


@dataclass
class Monster(Combatant):
    sprite_index: int = 0


@dataclass
class CombatState:
    party: list[PartyMember]
    monsters: list[Monster]
    turn_index: int = 0

    @property
    def over(self) -> bool:
        return not any(member.alive for member in self.party) or not any(
            monster.alive for monster in self.monsters
        )

    @property
    def victors(self) -> str | None:
        if not any(member.alive for member in self.party):
            return "monsters"
        if not any(monster.alive for monster in self.monsters):
            return "party"
        return None

    def current_actor(self) -> Combatant | None:
        order = self._turn_order()
        if not order:
            return None
        return order[self.turn_index % len(order)]

    def advance_turn(self) -> None:
        if self.over:
            return
        self.turn_index = (self.turn_index + 1) % max(1, len(self._turn_order()))

    def perform_attack(self) -> tuple[Combatant, Combatant, int] | None:
        if self.over:
            return None
        actor = self.current_actor()
        if actor is None:
            return None

        if isinstance(actor, PartyMember):
            target = next((m for m in self.monsters if m.alive), None)
        else:
            target = next((p for p in self.party if p.alive), None)
        if target is None:
            return None

        base = max(1, actor.attack - target.defense)
        damage = target.apply_damage(base)
        self.advance_turn()
        return actor, target, damage

    def _turn_order(self) -> list[Combatant]:
        return [*self.party, *self.monsters]
