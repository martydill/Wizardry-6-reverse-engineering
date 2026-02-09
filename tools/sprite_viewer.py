"""Sprite viewer — browse extracted EGA sprites in a window.

Usage:
    python -m tools.sprite_viewer gamedata/SCENARIO.DBS
    python -m tools.sprite_viewer --test  # display test patterns
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pygame

from bane.data.sprite_decoder import DEFAULT_16_PALETTE, EGADecoder, Sprite, SpriteAtlas


def create_test_sprites() -> SpriteAtlas:
    """Create test sprites to verify the rendering pipeline."""
    atlas = SpriteAtlas()
    decoder = EGADecoder()

    # Test pattern 1: All 16 colors in a grid
    pixels = []
    for y in range(16):
        for x in range(16):
            pixels.append((y * 16 + x) % 16)
    atlas.add_sprite(0, Sprite(width=16, height=16, pixels=pixels, palette=list(DEFAULT_16_PALETTE)))

    # Test pattern 2: Gradient bars
    pixels2 = []
    for y in range(32):
        for x in range(32):
            pixels2.append((x // 2) % 16)
    atlas.add_sprite(1, Sprite(width=32, height=32, pixels=pixels2, palette=list(DEFAULT_16_PALETTE)))

    # Test pattern 3: Checkerboard
    pixels3 = []
    for y in range(16):
        for x in range(16):
            pixels3.append(15 if (x + y) % 2 == 0 else 0)
    atlas.add_sprite(2, Sprite(width=16, height=16, pixels=pixels3, palette=list(DEFAULT_16_PALETTE)))

    # Test pattern 4: EGA planar decode test
    # Create 16x16 image data in planar format
    planar_data = bytearray(16 * 16 // 8 * 4)  # 4 planes, 2 bytes per row per plane
    # Fill with a pattern
    for plane in range(4):
        for row in range(16):
            offset = plane * (16 * 16 // 8) + row * 2
            if plane == 0:
                planar_data[offset] = 0xAA  # alternating bits
                planar_data[offset + 1] = 0x55
            elif plane == 1:
                planar_data[offset] = 0xCC
                planar_data[offset + 1] = 0x33
            elif plane == 2:
                planar_data[offset] = 0xF0
                planar_data[offset + 1] = 0x0F
            else:
                planar_data[offset] = 0xFF if row < 8 else 0x00
                planar_data[offset + 1] = 0xFF if row < 8 else 0x00

    sprite = decoder.decode_planar(bytes(planar_data), 16, 16)
    atlas.add_sprite(3, sprite)

    return atlas


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bane-sprites",
        description="View Wizardry 6 sprites",
    )
    parser.add_argument("file", type=Path, nargs="?", help="Path to SCENARIO.DBS")
    parser.add_argument("--test", action="store_true", help="Show test patterns")
    parser.add_argument("--scale", type=int, default=4, help="Display scale factor")
    args = parser.parse_args()

    if args.test:
        atlas = create_test_sprites()
    elif args.file:
        # TODO: Extract sprites from SCENARIO.DBS
        print("Sprite extraction from SCENARIO.DBS not yet implemented")
        print("Use --test to view test patterns")
        atlas = create_test_sprites()
    else:
        print("Specify a file or use --test")
        sys.exit(1)

    # Initialize pygame
    pygame.init()
    scale = args.scale
    win_w, win_h = 640, 480
    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption("Bane Engine — Sprite Viewer")
    font = pygame.font.Font(None, 20)

    sprite_ids = atlas.sprite_ids
    current_index = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_LEFT:
                    current_index = (current_index - 1) % len(sprite_ids)
                elif event.key == pygame.K_RIGHT:
                    current_index = (current_index + 1) % len(sprite_ids)

        screen.fill((30, 30, 40))

        if sprite_ids:
            sprite_id = sprite_ids[current_index]
            sprite = atlas.get_sprite(sprite_id)
            if sprite:
                # Scale sprite
                scaled = sprite.scale(scale)
                rgba = scaled.to_rgba_bytes()
                surf = pygame.image.frombuffer(
                    rgba, (scaled.width, scaled.height), "RGBA"
                )

                # Center on screen
                x = (win_w - scaled.width) // 2
                y = (win_h - scaled.height) // 2
                screen.blit(surf, (x, y))

                # Info text
                info = f"Sprite {sprite_id} ({sprite.width}x{sprite.height}) [{current_index + 1}/{len(sprite_ids)}]"
                text_surf = font.render(info, True, (200, 200, 200))
                screen.blit(text_surf, (10, 10))

        controls = font.render("Left/Right: Navigate | ESC: Quit", True, (120, 120, 120))
        screen.blit(controls, (10, win_h - 30))

        # Draw palette at bottom
        palette_y = win_h - 60
        for i, color in enumerate(DEFAULT_16_PALETTE):
            px = 10 + i * 20
            pygame.draw.rect(screen, color, (px, palette_y, 18, 18))
            pygame.draw.rect(screen, (100, 100, 100), (px, palette_y, 18, 18), 1)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
