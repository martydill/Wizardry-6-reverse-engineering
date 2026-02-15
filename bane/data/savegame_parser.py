"""Parser for SAVEGAME.DBS — game state save data.

SAVEGAME.DBS stores the current game state:
- Party position (dungeon level, x, y, facing)
- Party composition (which characters are active)
- Quest flags and world state
- Opened chests, unlocked doors, met NPCs
- Game time counter
"""

from __future__ import annotations

import logging
from pathlib import Path

from bane.data.binary_reader import BinaryReader, BinaryReaderError, BinaryWriter
from bane.data.enums import Direction
from bane.data.models import SaveGameData

logger = logging.getLogger(__name__)


class SaveGameParseError(Exception):
    """Raised when SAVEGAME.DBS parsing fails."""


class SaveGameParser:
    """Parses SAVEGAME.DBS into SaveGameData.

    Usage:
        parser = SaveGameParser(Path("gamedata/SAVEGAME.DBS"))
        save = parser.parse()
        print(f"Party at level {save.current_level}, pos ({save.position_x}, {save.position_y})")
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def parse(self) -> SaveGameData:
        """Parse the save game file."""
        logger.info("Parsing SAVEGAME.DBS from %s", self.path)
        reader = BinaryReader.from_file(self.path)
        save = SaveGameData()

        try:
            # Party position
            save.current_level = reader.read_u16()
            save.position_x = reader.read_u16()
            save.position_y = reader.read_u16()
            save.facing = Direction(reader.read_u8() % 4)

            # Party members (6 slots, 0xFF = empty)
            for _ in range(6):
                member_id = reader.read_u8()
                if member_id != 0xFF:
                    save.party_member_ids.append(member_id)

            # Game time
            save.game_time = reader.read_u32()
            save.total_steps = reader.read_u32()

            # Quest flags (count + key-value pairs)
            num_flags = reader.read_u16()
            for _ in range(num_flags):
                flag_id = reader.read_u16()
                flag_val = reader.read_u16()
                save.quest_flags[flag_id] = flag_val

            # Opened chests
            num_chests = reader.read_u16()
            for _ in range(num_chests):
                save.chests_opened.add(reader.read_u16())

            # Opened doors
            num_doors = reader.read_u16()
            for _ in range(num_doors):
                save.doors_opened.add(reader.read_u16())

            # Met NPCs
            num_npcs = reader.read_u16()
            for _ in range(num_npcs):
                save.npcs_met.add(reader.read_u16())

        except BinaryReaderError as e:
            raise SaveGameParseError(f"Failed to parse SAVEGAME.DBS: {e}") from e

        logger.info(
            "Parsed save: Level %d, pos (%d, %d) facing %s, %d party members",
            save.current_level,
            save.position_x,
            save.position_y,
            save.facing.name,
            len(save.party_member_ids),
        )
        return save

    def dump(self) -> str:
        """Return a human-readable summary of the save game."""
        try:
            save = self.parse()
        except (SaveGameParseError, FileNotFoundError) as e:
            return f"Error: {e}"

        lines = [
            "SAVEGAME.DBS Summary",
            f"  Position: Level {save.current_level}, "
            f"({save.position_x}, {save.position_y}) facing {save.facing.name}",
            f"  Party members: {save.party_member_ids}",
            f"  Game time: {save.game_time}",
            f"  Total steps: {save.total_steps}",
            f"  Quest flags: {len(save.quest_flags)}",
            f"  Chests opened: {len(save.chests_opened)}",
            f"  Doors opened: {len(save.doors_opened)}",
            f"  NPCs met: {len(save.npcs_met)}",
        ]
        return "\n".join(lines)


class SaveGameWriter:
    """Writes save game data to SAVEGAME.DBS format (or JSON for new saves)."""

    def write_dbs(self, save: SaveGameData, path: Path | str) -> None:
        """Write save data in original DBS format."""
        writer = BinaryWriter()

        writer.write_u16(save.current_level)
        writer.write_u16(save.position_x)
        writer.write_u16(save.position_y)
        writer.write_u8(save.facing.value)

        # Party (pad to 6 with 0xFF)
        members = save.party_member_ids[:6]
        for mid in members:
            writer.write_u8(mid)
        for _ in range(6 - len(members)):
            writer.write_u8(0xFF)

        writer.write_u32(save.game_time)
        writer.write_u32(save.total_steps)

        # Quest flags
        writer.write_u16(len(save.quest_flags))
        for flag_id, flag_val in sorted(save.quest_flags.items()):
            writer.write_u16(flag_id)
            writer.write_u16(flag_val)

        # Chests
        writer.write_u16(len(save.chests_opened))
        for chest_id in sorted(save.chests_opened):
            writer.write_u16(chest_id)

        # Doors
        writer.write_u16(len(save.doors_opened))
        for door_id in sorted(save.doors_opened):
            writer.write_u16(door_id)

        # NPCs
        writer.write_u16(len(save.npcs_met))
        for npc_id in sorted(save.npcs_met):
            writer.write_u16(npc_id)

        writer.write_to_file(path)
        logger.info("Wrote save game to %s", path)

    def write_json(self, save: SaveGameData, path: Path | str) -> None:
        """Write save data in JSON format (engine-native saves)."""
        import json

        data = {
            "current_level": save.current_level,
            "position_x": save.position_x,
            "position_y": save.position_y,
            "facing": save.facing.name,
            "party_member_ids": save.party_member_ids,
            "game_time": save.game_time,
            "total_steps": save.total_steps,
            "quest_flags": save.quest_flags,
            "chests_opened": sorted(save.chests_opened),
            "doors_opened": sorted(save.doors_opened),
            "npcs_met": sorted(save.npcs_met),
        }
        Path(path).write_text(json.dumps(data, indent=2))
        logger.info("Wrote JSON save to %s", path)
