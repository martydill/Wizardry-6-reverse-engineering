from __future__ import annotations

import argparse
from pathlib import Path

from .engine import GameEngine, PlayerState, load_game_data_bundle
from .renderer import render_ascii_with_player


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a lightweight Wizardry 6 ASCII game loop."
    )
    parser.add_argument("map_path", type=Path, help="Path to the map file.")
    parser.add_argument(
        "--map-format",
        choices=["w6mp", "raw"],
        default=None,
        help="Map format. Defaults to auto-detect.",
    )
    parser.add_argument("--map-width", type=int, help="Width for raw maps.")
    parser.add_argument("--map-height", type=int, help="Height for raw maps.")
    parser.add_argument("--tiles-path", type=Path, help="Path to the tiles file.")
    parser.add_argument(
        "--tiles-format",
        choices=["w6tl", "raw"],
        default=None,
        help="Tiles format. Defaults to auto-detect.",
    )
    parser.add_argument("--tile-width", type=int, help="Width for raw tiles.")
    parser.add_argument("--tile-height", type=int, help="Height for raw tiles.")
    parser.add_argument("--tile-count", type=int, help="Tile count for raw tiles.")
    parser.add_argument("--monsters-path", type=Path, help="Path to monster data.")
    parser.add_argument("--items-path", type=Path, help="Path to item data.")
    parser.add_argument("--npcs-path", type=Path, help="Path to NPC data.")
    parser.add_argument(
        "--conversations-path", type=Path, help="Path to conversations."
    )
    parser.add_argument("--game-data-path", type=Path, help="Path to game data blob.")
    parser.add_argument("--save-game-path", type=Path, help="Path to save game data.")
    parser.add_argument(
        "--save-game-expected-size",
        type=int,
        help="Expected size for save game payload validation.",
    )
    parser.add_argument("--portraits-path", type=Path, help="Path to portrait data.")
    parser.add_argument("--portrait-width", type=int, help="Portrait width.")
    parser.add_argument("--portrait-height", type=int, help="Portrait height.")
    parser.add_argument("--portrait-count", type=int, help="Portrait count.")
    parser.add_argument("--start-x", type=int, default=0, help="Starting X position.")
    parser.add_argument("--start-y", type=int, default=0, help="Starting Y position.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        data = load_game_data_bundle(
            map_path=args.map_path,
            map_format=args.map_format,
            map_width=args.map_width,
            map_height=args.map_height,
            tiles_path=args.tiles_path,
            tiles_format=args.tiles_format,
            tile_width=args.tile_width,
            tile_height=args.tile_height,
            tile_count=args.tile_count,
            monsters_path=args.monsters_path,
            items_path=args.items_path,
            npcs_path=args.npcs_path,
            conversations_path=args.conversations_path,
            game_data_path=args.game_data_path,
            save_game_path=args.save_game_path,
            save_game_expected_size=args.save_game_expected_size,
            portraits_path=args.portraits_path,
            portrait_width=args.portrait_width,
            portrait_height=args.portrait_height,
            portrait_count=args.portrait_count,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    engine = GameEngine(data, PlayerState(x=args.start_x, y=args.start_y))

    print("Wizardry 6 ASCII Game Loop")
    print("Commands: n, s, e, w, map, quit")
    while True:
        command = input("> ").strip().lower()
        if command in {"quit", "q", "exit"}:
            print("Exiting.")
            break
        if command in {"map", "m"}:
            print(render_ascii_with_player(engine.map_grid, engine.player))
            continue
        if command in {"n", "s", "e", "w"}:
            moved = engine.move(command)
            if not moved:
                print("Blocked.")
            else:
                print(render_ascii_with_player(engine.map_grid, engine.player))
            continue
        print("Unknown command. Use n/s/e/w, map, or quit.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
