"""Monster .PIC viewer — render Wizardry 6 monster images.

Usage:
    python -m loaders.pic_viewer gamedata/MON00.PIC
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pygame

from bane.data.pic_decoder import (
    PIC_HEIGHT,
    PIC_WIDTH,
    decode_pic_file,
    decode_pic_frames,
)
from bane.data.sprite_decoder import (
    DEFAULT_16_PALETTE,
    decode_ega_file,
    decode_ega_frames,
)


def _load_file(path: Path, args) -> tuple[list, int]:
    """Load frames from a .PIC or .EGA file. Returns (frames, frame_index)."""
    plane_order = [int(ch) for ch in args.plane_order.strip()]
    msb_first = not args.lsb_first

    if path.suffix.lower() == ".ega":
        frames = decode_ega_frames(path)
        if not frames:
            frames = [decode_ega_file(path)]
    else:
        frames = decode_pic_frames(data=path.read_bytes(), header_skip=args.header_skip, msb_first=msb_first)
        if not frames:
            frames = [decode_pic_file(
                str(path),
                width=args.width,
                height=args.height,
                layout=args.layout,
                header_skip=args.header_skip,
                plane_order=plane_order,
            )]

    frame_index = max(0, min(args.frame, len(frames) - 1))
    return frames, frame_index


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-pic",
        description="View Wizardry 6 monster .PIC and .EGA files",
    )
    parser.add_argument("file", type=Path, help="Path to .PIC or .EGA file")
    parser.add_argument("--scale", type=int, default=2, help="Display scale factor")
    parser.add_argument("--width", type=int, default=PIC_WIDTH, help="Override width")
    parser.add_argument("--height", type=int, default=PIC_HEIGHT, help="Override height")
    parser.add_argument(
        "--layout",
        type=str,
        default="planar-row",
        help="Layout: planar, planar-lsb, planar-row, planar-row-lsb",
    )
    parser.add_argument(
        "--header-skip",
        type=int,
        default=None,
        help="Override embedded header length in decompressed stream",
    )
    parser.add_argument(
        "--plane-order",
        type=str,
        default="0123",
        help="Plane order as digits, e.g. 0123 or 3210",
    )
    parser.add_argument(
        "--frame",
        type=int,
        default=0,
        help="Initial frame index",
    )
    parser.add_argument(
        "--msb-first",
        action="store_true",
        help="Interpret bits MSB-first (default)",
    )
    parser.add_argument(
        "--lsb-first",
        action="store_true",
        help="Interpret bits LSB-first",
    )
    parser.add_argument(
        "--transparent",
        type=int,
        default=None,
        help="Palette index to treat as transparent (default: 15 for .PIC, none for .EGA)",
    )
    args = parser.parse_args()

    if args.lsb_first and args.msb_first:
        raise SystemExit("Choose only one of --msb-first or --lsb-first")

    # Build sorted list of sibling files with the same extension for Up/Down navigation
    current_file = args.file.resolve()
    sibling_files = sorted(
        current_file.parent.glob(f"*{current_file.suffix}"),
        key=lambda p: p.name.lower(),
    )
    file_index = next((i for i, p in enumerate(sibling_files) if p == current_file), 0)

    frames, frame_index = _load_file(current_file, args)
    sprite = frames[frame_index]

    pygame.init()
    scale = max(1, args.scale)
    win_w, win_h = 640, 480
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"Bane Engine — {current_file.name}")
    font = pygame.font.Font(None, 20)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_SPACE) and len(frames) > 1:
                    frame_index = (frame_index + 1) % len(frames)
                    sprite = frames[frame_index]
                elif event.key == pygame.K_LEFT and len(frames) > 1:
                    frame_index = (frame_index - 1) % len(frames)
                    sprite = frames[frame_index]
                elif event.key == pygame.K_UP and len(sibling_files) > 1:
                    file_index = (file_index - 1) % len(sibling_files)
                    current_file = sibling_files[file_index]
                    frames, frame_index = _load_file(current_file, args)
                    sprite = frames[frame_index]
                    pygame.display.set_caption(f"Bane Engine — {current_file.name}")
                elif event.key == pygame.K_DOWN and len(sibling_files) > 1:
                    file_index = (file_index + 1) % len(sibling_files)
                    current_file = sibling_files[file_index]
                    frames, frame_index = _load_file(current_file, args)
                    sprite = frames[frame_index]
                    pygame.display.set_caption(f"Bane Engine — {current_file.name}")

        screen.fill((20, 20, 30))

        scaled = sprite.scale(scale)
        transparent_index = args.transparent
        if transparent_index is None:
            transparent_index = 15 if current_file.suffix.lower() == ".pic" else -1
        rgba = scaled.to_rgba_bytes(transparent_index=transparent_index)
        surf = pygame.image.frombuffer(rgba, (scaled.width, scaled.height), "RGBA")

        x = (win_w - scaled.width) // 2
        y = (win_h - scaled.height) // 2
        screen.blit(surf, (x, y))

        file_info = f"{current_file.name} ({file_index + 1}/{len(sibling_files)})"
        if len(frames) > 1:
            frame_info = f"frame {frame_index + 1}/{len(frames)} ({sprite.width}x{sprite.height})"
        else:
            frame_info = f"{sprite.width}x{sprite.height}"
        text_surf = font.render(f"{file_info}  {frame_info}", True, (200, 200, 200))
        screen.blit(text_surf, (10, 10))

        controls_text = "ESC: Quit  Up/Down: File"
        if len(frames) > 1:
            controls_text += "  Left/Right/Space: Frame"
        controls = font.render(controls_text, True, (120, 120, 120))
        screen.blit(controls, (10, win_h - 30))

        palette = DEFAULT_16_PALETTE
        palette_y = win_h - 60
        for i, color in enumerate(palette):
            px = 10 + i * 20
            pygame.draw.rect(screen, color, (px, palette_y, 18, 18))
            pygame.draw.rect(screen, (100, 100, 100), (px, palette_y, 18, 18), 1)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
