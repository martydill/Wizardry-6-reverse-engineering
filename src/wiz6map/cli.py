from __future__ import annotations

import argparse
from pathlib import Path

from .loader import MapLoadError, load_map, load_raw_map
from .renderer import render_ascii


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render Wizardry 6 maps as ASCII art.")
    parser.add_argument("path", type=Path, help="Path to the map file.")
    parser.add_argument(
        "--format",
        choices=["w6mp", "raw"],
        default=None,
        help="Map format. Defaults to auto-detect.",
    )
    parser.add_argument("--width", type=int, help="Width for raw maps.")
    parser.add_argument("--height", type=int, help="Height for raw maps.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.format == "raw":
            if args.width is None or args.height is None:
                raise MapLoadError("Raw format requires --width and --height")
            grid = load_raw_map(args.path, width=args.width, height=args.height)
        else:
            grid = load_map(args.path, fmt=args.format)
    except MapLoadError as exc:
        parser.error(str(exc))
        return 2

    print(render_ascii(grid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
