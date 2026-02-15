
import pygame
from pathlib import Path
from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def score_vertical(pixels, w, h):
    s = 0
    for x in range(w):
        for y in range(1, h):
            if pixels[y*w + x] == pixels[(y-1)*w + x]:
                s += 1
    return s

def main():
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    w, h = 320, 200
    
    best_score = -1
    best_offset = -1
    
    # Try offsets 0 to 256
    for offset in range(0, 257, 1):
        pixels = [0] * (w * h)
        bytes_per_row = w // 8
        for plane in range(4):
            plane_base = plane * 8192
            for y in range(h):
                row_base = plane_base + offset + y * bytes_per_row
                if row_base + bytes_per_row > (plane + 1) * 8192:
                    continue
                for bx in range(bytes_per_row):
                    byte_val = data[row_base + bx]
                    for bit in range(8):
                        x = bx * 8 + (7 - bit)
                        if byte_val & (1 << bit):
                            pixels[y * w + x] |= (1 << plane)
        
        s = score_vertical(pixels, w, h)
        if s > best_score:
            best_score = s
            best_offset = offset
        
        if offset % 8 == 0 or offset == 192:
            print(f"Offset {offset}: Score {s}")

    print(f"Best offset: {best_offset} with score {best_score}")

if __name__ == "__main__":
    main()
