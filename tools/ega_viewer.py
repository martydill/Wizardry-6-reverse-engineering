
"""EGA viewer — render Wizardry 6 full-screen .EGA images.

Usage:
    python -m tools.ega_viewer gamedata/TITLEPAG.EGA
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pygame

from bane.data.sprite_decoder import decode_ega_file, decode_ega_frames


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-ega",
        description="View Wizardry 6 EGA files (full-screen or collections)",
    )
    parser.add_argument("file", type=Path, help="Path to .EGA file")
    parser.add_argument("--scale", type=int, default=2, help="Display scale factor")
    parser.add_argument("--frame", type=int, default=0, help="Initial frame index")
    args = parser.parse_args()

    pygame.init()
    
    try:
        frames = decode_ega_frames(args.file)
        if not frames:
            print(f"No frames found in {args.file}")
            return
        frame_index = max(0, min(args.frame, len(frames) - 1))
        sprite = frames[frame_index]
    except Exception as e:
        print(f"Error loading {args.file}: {e}")
        import traceback
        traceback.print_exc()
        return

    scale = max(1, args.scale)
    win_w = max(640, sprite.width * scale)
    win_h = max(480, sprite.height * scale + 40)
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"Bane Engine — {args.file.name}")
    font = pygame.font.Font(None, 24)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif len(frames) > 1 and event.key in (pygame.K_RIGHT, pygame.K_SPACE):
                    frame_index = (frame_index + 1) % len(frames)
                    sprite = frames[frame_index]
                elif len(frames) > 1 and event.key == pygame.K_LEFT:
                    frame_index = (frame_index - 1) % len(frames)
                    sprite = frames[frame_index]

        screen.fill((20, 20, 30))

        scaled = sprite.scale(scale)
        rgba = scaled.to_rgba_bytes()
        surf = pygame.image.frombuffer(rgba, (scaled.width, scaled.height), "RGBA")

        x = (win_w - scaled.width) // 2
        y = (win_h - scaled.height) // 2
        screen.blit(surf, (x, y))

        if len(frames) > 1:
            info = f"{args.file.name} frame {frame_index + 1}/{len(frames)} ({sprite.width}x{sprite.height}) - ESC: Quit, Left/Right: Frame"
        else:
            info = f"{args.file.name} ({sprite.width}x{sprite.height}) - ESC: Quit"
        
        text_surf = font.render(info, True, (200, 200, 200))
        screen.blit(text_surf, (10, win_h - 30))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
