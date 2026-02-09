from __future__ import annotations

import argparse
from pathlib import Path

from .pygame_viewer import RenderConfig, run_pygame_viewer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render Wizardry 6 data with a pygame viewer."
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
    parser.add_argument("--tile-scale", type=int, default=2, help="Tile scale factor.")
    parser.add_argument(
        "--portrait-scale", type=int, default=2, help="Portrait scale factor."
    )
    parser.add_argument(
        "--monster-width",
        type=int,
        default=16,
        help="Width of a monster record in pixels.",
    )
    parser.add_argument(
        "--monster-height",
        type=int,
        default=16,
        help="Height of a monster record in pixels.",
    )
    parser.add_argument(
        "--monster-scale",
        type=int,
        default=2,
        help="Scale factor for monster previews.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = RenderConfig(
        tile_scale=args.tile_scale,
        portrait_scale=args.portrait_scale,
        monster_width=args.monster_width,
        monster_height=args.monster_height,
        monster_scale=args.monster_scale,
    )

    return run_pygame_viewer(
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
        start_x=args.start_x,
        start_y=args.start_y,
        render_config=config,
    )


if __name__ == "__main__":
    raise SystemExit(main())
