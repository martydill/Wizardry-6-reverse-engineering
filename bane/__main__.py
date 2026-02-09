"""Entry point for the Bane Engine."""

import argparse
import sys
from pathlib import Path

from bane.engine.engine import Engine
from bane.engine.config import EngineConfig


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane",
        description="Bane Engine — Wizardry VI: Bane of the Cosmic Forge",
    )
    parser.add_argument(
        "--gamedata",
        type=Path,
        default=Path("gamedata"),
        help="Path to directory containing original Wizardry 6 data files",
    )
    parser.add_argument(
        "--width", type=int, default=960, help="Window width (default: 960)"
    )
    parser.add_argument(
        "--height", type=int, default=600, help="Window height (default: 600)"
    )
    parser.add_argument(
        "--fullscreen", action="store_true", help="Start in fullscreen mode"
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="Integer scale factor for pixel-perfect rendering (default: 3)",
    )
    args = parser.parse_args()

    config = EngineConfig(
        gamedata_path=args.gamedata,
        window_width=args.width,
        window_height=args.height,
        fullscreen=args.fullscreen,
        scale_factor=args.scale,
    )

    engine = Engine(config)
    try:
        engine.run()
    except KeyboardInterrupt:
        pass
    finally:
        engine.shutdown()

    sys.exit(0)


if __name__ == "__main__":
    main()
