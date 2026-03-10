"""render_font.py — Pygame font renderer for Wizardry 6 WFONT files.

Usage:
    python -m loaders.render_font "Hello World"
    python -m loaders.render_font --font 0 "ABCDEF"
    python -m loaders.render_font --font 1 --chars 0,1,2,3,4,5,6,7,8,9,10
    python -m loaders.render_font --scale 4 "Test string"
    python -m loaders.render_font --all          # show all glyphs from font 0
    python -m loaders.render_font --all --font 1 # show all glyphs from font 1

WFONT0.EGA : 1bpp monochrome, 128 chars, frame N = ASCII char N.
             Use with plain ASCII text strings.
WFONT1-4.EGA: 4-plane EGA colour, 128 chars, frame N = game UI char code N.
              Use --chars to specify raw game char codes (0-127).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pygame

from bane.data.sprite_decoder import (
    DEFAULT_16_PALETTE,
    decode_ega_frames,
)

GAMEDATA = Path("gamedata")
FONT_PATHS = [
    GAMEDATA / "WFONT0.EGA",
    GAMEDATA / "WFONT1.EGA",
    GAMEDATA / "WFONT2.EGA",
    GAMEDATA / "WFONT3.EGA",
    GAMEDATA / "WFONT4.EGA",
]

# EGA colour index 0 in the DEFAULT_16_PALETTE is black (background/transparent for WFONT0).
# EGA colour index 15 is white (foreground for 1bpp WFONT0).
TRANSPARENT_INDEX = 0   # background colour — treated as transparent when blitting


def sprite_to_surface(sprite, *, transparent: bool = False) -> pygame.Surface:
    """Convert a Sprite to a pygame Surface.

    When transparent=True the palette index 0 pixels are made transparent,
    which lets glyphs be blitted onto any background colour.
    """
    surf = pygame.Surface((sprite.width, sprite.height), pygame.SRCALPHA)
    for y in range(sprite.height):
        for x in range(sprite.width):
            idx = sprite.get_pixel(x, y)
            if transparent and idx == TRANSPARENT_INDEX:
                surf.set_at((x, y), (0, 0, 0, 0))
            else:
                r, g, b = sprite.palette[idx] if idx < len(sprite.palette) else (0, 0, 0)
                surf.set_at((x, y), (r, g, b, 255))
    return surf


def load_font_glyphs(font_index: int) -> list[pygame.Surface]:
    """Load all 128 glyph surfaces for the given WFONT index (0-4)."""
    path = FONT_PATHS[font_index]
    if not path.exists():
        print(f"Font file not found: {path}")
        sys.exit(1)
    sprites = decode_ega_frames(path)
    return [sprite_to_surface(s, transparent=True) for s in sprites]


def _wrap_words(text: str, max_chars: int) -> list[str]:
    """Word-wrap text to a maximum number of characters per line."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        line = ""
        for word in words:
            # A single word longer than max_chars gets its own line(s)
            while len(word) > max_chars:
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:max_chars])
                word = word[max_chars:]
            if not word:
                continue
            candidate = f"{line} {word}" if line else word
            if len(candidate) > max_chars:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def render_string(
    glyphs: list[pygame.Surface],
    text: str,
    *,
    scale: int = 1,
    fg: tuple[int, int, int] = (200, 200, 200),
    bg: tuple[int, int, int] = (20, 20, 30),
    char_width: int = 8,
    char_height: int = 8,
    max_width: int = 0,
) -> pygame.Surface:
    """Render a string of ASCII text onto a Surface using WFONT0 glyphs.

    Each character occupies char_width × char_height pixels (pre-scale).
    fg/bg only affect the 1bpp WFONT0 font (white foreground → fg, black → bg).
    For WFONT1-4 the EGA palette colours are used as-is.
    max_width: maximum surface width in pixels (pre-scale); 0 = no limit.
    """
    text = text.upper()
    max_chars = (max_width // char_width) if max_width > 0 else 0
    lines = _wrap_words(text, max_chars) if max_chars > 0 else [text]

    w = max((max_chars or max(len(l) for l in lines)) * char_width, 1) * scale
    h = char_height * len(lines) * scale
    surf = pygame.Surface((w, h))
    surf.fill(bg)

    for row, line in enumerate(lines):
        y = row * char_height * scale
        for i, ch in enumerate(line):
            code = ord(ch)
            if code >= len(glyphs):
                continue
            glyph = glyphs[code]
            if scale > 1:
                glyph = pygame.transform.scale(glyph, (char_width * scale, char_height * scale))
            surf.blit(glyph, (i * char_width * scale, y))

    # WFONT0 renders with palette idx 15 (white) as foreground.
    # Tint white pixels to fg colour using a colour multiply trick via PixelArray.
    if fg != (255, 255, 255):
        pa = pygame.PixelArray(surf)
        white = surf.map_rgb(255, 255, 255)
        fg_mapped = surf.map_rgb(*fg)
        pa.replace(white, fg_mapped)
        del pa

    return surf


def render_codes(
    glyphs: list[pygame.Surface],
    codes: list[int],
    *,
    scale: int = 1,
    bg: tuple[int, int, int] = (20, 20, 30),
    char_width: int = 8,
    char_height: int = 8,
) -> pygame.Surface:
    """Render a sequence of raw glyph codes (for WFONT1-4 UI fonts)."""
    n = len(codes)
    w = max(n * char_width, 1) * scale
    h = char_height * scale
    surf = pygame.Surface((w, h))
    surf.fill(bg)

    for i, code in enumerate(codes):
        if code >= len(glyphs):
            continue
        glyph = glyphs[code]
        if scale > 1:
            glyph = pygame.transform.scale(glyph, (char_width * scale, char_height * scale))
        surf.blit(glyph, (i * char_width * scale, 0))

    return surf


def show_all_glyphs(
    glyphs: list[pygame.Surface],
    *,
    scale: int = 2,
    cols: int = 16,
    bg: tuple[int, int, int] = (20, 20, 30),
    char_width: int = 8,
    char_height: int = 8,
    font_index: int = 0,
) -> None:
    """Open a window showing all 128 glyphs in a grid."""
    pygame.init()
    rows = (len(glyphs) + cols - 1) // cols
    cell_w = char_width * scale + 2
    cell_h = char_height * scale + 2
    win_w = cols * cell_w + 4
    win_h = rows * cell_h + 4 + 20  # extra space for title bar info

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(f"WFONT{font_index}.EGA — all {len(glyphs)} glyphs")
    screen.fill(bg)

    sys_font = pygame.font.SysFont("monospace", 9)

    for idx, glyph in enumerate(glyphs):
        col = idx % cols
        row = idx // cols
        x = 2 + col * cell_w
        y = 2 + row * cell_h
        scaled = pygame.transform.scale(glyph, (char_width * scale, char_height * scale))
        screen.blit(scaled, (x, y))

    # Status bar at the bottom
    label = sys_font.render(
        f"WFONT{font_index}.EGA  |  {len(glyphs)} glyphs  |  8x8 px  |  scale={scale}x  |  hover=N/A  |  ESC=quit",
        True, (140, 140, 160),
    )
    screen.blit(label, (4, win_h - 16))

    pygame.display.flip()

    running = True
    hovered = -1
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
            elif ev.type == pygame.MOUSEMOTION:
                mx, my = ev.pos
                col = (mx - 2) // cell_w
                row_ = (my - 2) // cell_h
                new_hovered = row_ * cols + col
                if new_hovered != hovered and 0 <= new_hovered < len(glyphs):
                    hovered = new_hovered
                    # Redraw status bar with glyph info
                    screen.fill(bg, (0, win_h - 20, win_w, 20))
                    ch = chr(hovered) if font_index == 0 and 32 <= hovered < 127 else "?"
                    info = f"glyph={hovered}  char={ch!r}  code=0x{hovered:02X}"
                    lbl = sys_font.render(info, True, (200, 200, 120))
                    screen.blit(lbl, (4, win_h - 16))
                    pygame.display.flip()

    pygame.quit()


def main() -> None:
    ap = argparse.ArgumentParser(description="Wizardry 6 WFONT renderer")
    ap.add_argument("text", nargs="?", default="", help="ASCII text to render (WFONT0)")
    ap.add_argument("--font", type=int, default=0, choices=[0, 1, 2, 3, 4],
                    help="Font index (0=text, 1-4=UI EGA colour fonts)")
    ap.add_argument("--chars", default="", help="Comma-separated raw char codes for WFONT1-4, e.g. 1,2,3,4")
    ap.add_argument("--scale", type=int, default=3, help="Pixel scale factor (default 3)")
    ap.add_argument("--all", action="store_true", help="Show all glyphs in a grid viewer")
    ap.add_argument("--cols", type=int, default=16, help="Columns in --all grid (default 16)")
    ap.add_argument("--max-width", type=int, default=0,
                    help="Maximum surface width in pixels (pre-scale); enables word wrap (default off)")
    ap.add_argument("--fg", default="200,200,200",
                    help="Foreground RGB for WFONT0, e.g. 255,255,0 (default 200,200,200)")
    ap.add_argument("--bg", default="20,20,30",
                    help="Background RGB, e.g. 0,0,0 (default 20,20,30)")
    args = ap.parse_args()

    fg = tuple(int(x) for x in args.fg.split(","))
    bg = tuple(int(x) for x in args.bg.split(","))

    glyphs = load_font_glyphs(args.font)

    if args.all:
        show_all_glyphs(glyphs, scale=args.scale, cols=args.cols,
                        bg=bg, font_index=args.font)
        return

    pygame.init()

    if args.chars:
        codes = [int(c.strip()) for c in args.chars.split(",")]
        surf = render_codes(glyphs, codes, scale=args.scale, bg=bg)
        title = f"WFONT{args.font}  codes={args.chars}"
    elif args.text:
        surf = render_string(glyphs, args.text, scale=args.scale, fg=fg, bg=bg, max_width=args.max_width)
        title = f"WFONT{args.font}  '{args.text}'"
    else:
        # Default demo: render printable ASCII using WFONT0
        demo = "ABCDEFGHIJKLMNOPQRSTUVWXYZ  0123456789  THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"
        surf = render_string(glyphs, demo, scale=args.scale, fg=fg, bg=bg, max_width=args.max_width)
        title = f"WFONT{args.font}  demo"

    # Add a margin
    margin = 8
    win_w = surf.get_width() + margin * 2
    win_h = surf.get_height() + margin * 2

    screen = pygame.display.set_mode((win_w, win_h))
    pygame.display.set_caption(title)
    screen.fill(bg)
    screen.blit(surf, (margin, margin))
    pygame.display.flip()

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False

    pygame.quit()


if __name__ == "__main__":
    main()
