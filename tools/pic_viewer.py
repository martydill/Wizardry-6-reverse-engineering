"""Monster .PIC viewer — render Wizardry 6 monster images.

Usage:
    python -m tools.pic_viewer gamedata/MON00.PIC
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pygame

from bane.data.pic_decoder import PIC_HEIGHT, PIC_WIDTH, decode_pic_file, decode_pic_frames
from bane.data.sprite_decoder import DEFAULT_16_PALETTE


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-pic",
        description="View Wizardry 6 monster .PIC files",
    )
    parser.add_argument("file", type=Path, help="Path to .PIC file")
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
        help="Interpret tile bits MSB-first (default)",
    )
    parser.add_argument(
        "--lsb-first",
        action="store_true",
        help="Interpret tile bits LSB-first",
    )
    parser.add_argument(
        "--transparent",
        type=int,
        default=-1,
        help="Palette index to treat as transparent (default: none)",
    )
    args = parser.parse_args()
    plane_order = [int(ch) for ch in args.plane_order.strip()]

    if args.lsb_first and args.msb_first:
        raise SystemExit("Choose only one of --msb-first or --lsb-first")
    msb_first = not args.lsb_first

    frames = decode_pic_frames(
        data=args.file.read_bytes(),
        header_skip=args.header_skip,
        msb_first=msb_first,
    )
    if frames:
        frame_index = max(0, min(args.frame, len(frames) - 1))
        sprite = frames[frame_index]
    else:
        frame_index = 0
        frames = []
        sprite = decode_pic_file(
            str(args.file),
            width=args.width,
            height=args.height,
            layout=args.layout,
            header_skip=args.header_skip,
            plane_order=plane_order,
        )

    pygame.init()
    scale = max(1, args.scale)
    win_w = max(640, sprite.width * scale + 40)
    win_h = max(480, sprite.height * scale + 80)
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"Bane Engine — {args.file.name}")
    font = pygame.font.Font(None, 20)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif frames and event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                    frame_index = (frame_index + 1) % len(frames)
                    sprite = frames[frame_index]
                elif frames and event.key == pygame.K_LEFT:
                    frame_index = (frame_index - 1) % len(frames)
                    sprite = frames[frame_index]

        screen.fill((20, 20, 30))

        scaled = sprite.scale(scale)
        rgba = scaled.to_rgba_bytes(transparent_index=args.transparent)
        surf = pygame.image.frombuffer(rgba, (scaled.width, scaled.height), "RGBA")

        x = (win_w - scaled.width) // 2
        y = (win_h - scaled.height) // 2
        screen.blit(surf, (x, y))

        if frames:
            info = (
                f"{args.file.name} frame {frame_index + 1}/{len(frames)} "
                f"({sprite.width}x{sprite.height}) skip={args.header_skip}"
            )
        else:
            info = (
                f"{args.file.name} ({sprite.width}x{sprite.height}) "
                f"[{args.layout} order={args.plane_order} skip={args.header_skip}]"
            )
        text_surf = font.render(info, True, (200, 200, 200))
        screen.blit(text_surf, (10, 10))

        controls_text = "ESC: Quit"
        if frames:
            controls_text += "  Left/Right/Space: Frame"
        controls = font.render(controls_text, True, (120, 120, 120))
        screen.blit(controls, (10, win_h - 30))

        palette_y = win_h - 60
        for i, color in enumerate(DEFAULT_16_PALETTE):
            px = 10 + i * 20
            pygame.draw.rect(screen, color, (px, palette_y, 18, 18))
            pygame.draw.rect(screen, (100, 100, 100), (px, palette_y, 18, 18), 1)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
