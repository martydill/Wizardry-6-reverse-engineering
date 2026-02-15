"""DBS file dumper — hex dump and structure analysis tool.

Dumps the contents of Wizardry 6 .DBS files for reverse engineering.

Usage:
    python -m tools.dbs_dumper gamedata/SCENARIO.DBS
    python -m tools.dbs_dumper gamedata/PCFILE.DBS --characters
    python -m tools.dbs_dumper gamedata/SAVEGAME.DBS --savegame
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bane.data.binary_reader import BinaryReader
from bane.data.character_parser import CharacterParser
from bane.data.savegame_parser import SaveGameParser
from bane.data.scenario_parser import ScenarioParser


def hex_dump_file(path: Path, offset: int = 0, length: int = 512) -> None:
    """Print hex dump of a file."""
    reader = BinaryReader.from_file(path)
    print(f"File: {path}")
    print(f"Size: {reader.size} bytes (0x{reader.size:X})")
    print(f"Dump offset 0x{offset:X}, length {length}:")
    print(reader.hex_dump(offset, length))


def dump_scenario(path: Path) -> None:
    """Analyze and dump SCENARIO.DBS structure."""
    print(f"=== SCENARIO.DBS Analysis: {path} ===\n")
    parser = ScenarioParser(path)

    # Hex dump header
    print("--- Header (first 512 bytes) ---")
    print(parser.dump_header(512))
    print()

    # Try to parse
    try:
        scenario = parser.parse()
        print(f"Monsters: {len(scenario.monsters)}")
        for mid, m in sorted(scenario.monsters.items())[:20]:
            print(f"  [{mid:3d}] {m.name:20s} L{m.level:2d} HP:{m.hp_min}-{m.hp_max} XP:{m.xp_reward}")
        if len(scenario.monsters) > 20:
            print(f"  ... and {len(scenario.monsters) - 20} more")

        print(f"\nItems: {len(scenario.items)}")
        for iid, item in sorted(scenario.items.items())[:20]:
            print(f"  [{iid:3d}] {item.name:20s} Type:{item.item_type.name} Val:{item.value}")
        if len(scenario.items) > 20:
            print(f"  ... and {len(scenario.items) - 20} more")

        print(f"\nSpells: {len(scenario.spells)}")
        print(f"Loot tables: {len(scenario.loot_tables)}")
        print(f"Dungeon levels: {len(scenario.dungeon_levels)}")
        print(f"Events: {len(scenario.events)}")
    except Exception as e:
        print(f"Parse error: {e}")
        print("(This is expected until the format is fully reverse-engineered)")


def dump_characters(path: Path) -> None:
    """Dump character data from PCFILE.DBS."""
    print(f"=== PCFILE.DBS Analysis: {path} ===\n")
    parser = CharacterParser(path)
    print(parser.dump_characters())


def dump_savegame(path: Path) -> None:
    """Dump save game data from SAVEGAME.DBS."""
    print(f"=== SAVEGAME.DBS Analysis: {path} ===\n")
    parser = SaveGameParser(path)
    print(parser.dump())


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-dump",
        description="Dump and analyze Wizardry 6 data files",
    )
    parser.add_argument("file", type=Path, help="Path to .DBS file")
    parser.add_argument(
        "--offset", type=lambda x: int(x, 0), default=0,
        help="Hex dump start offset (e.g., 0x100)",
    )
    parser.add_argument(
        "--length", type=int, default=512,
        help="Hex dump length in bytes",
    )
    parser.add_argument("--characters", action="store_true", help="Parse as PCFILE.DBS")
    parser.add_argument("--savegame", action="store_true", help="Parse as SAVEGAME.DBS")
    parser.add_argument("--scenario", action="store_true", help="Parse as SCENARIO.DBS")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    if args.characters:
        dump_characters(args.file)
    elif args.savegame:
        dump_savegame(args.file)
    elif args.scenario:
        dump_scenario(args.file)
    else:
        # Default: raw hex dump
        hex_dump_file(args.file, args.offset, args.length)


if __name__ == "__main__":
    main()
