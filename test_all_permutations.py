
import pygame
import os
import itertools
from pathlib import Path
from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def decode_8k_perm(data, w, h, palette, perm):
    pixels = [0] * (w * h)
    bytes_per_row = w // 8
    for i, plane in enumerate(perm):
        # i is the bit position (0-3), plane is the bank index (0-3)
        plane_base = plane * 8192
        for y in range(h):
            row_base = plane_base + y * bytes_per_row
            for bx in range(bytes_per_row):
                byte_val = data[row_base + bx]
                for bit in range(8):
                    x = bx * 8 + (7 - bit)
                    if byte_val & (1 << bit):
                        pixels[y * w + x] |= (1 << i)
    return Sprite(w, h, pixels, palette)

def main():
    pygame.init()
    os.makedirs('perms', exist_ok=True)
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    w, h = 320, 200
    
    for perm in itertools.permutations(range(4)):
        sprite = decode_8k_perm(data, w, h, DEFAULT_16_PALETTE, perm)
        name = "".join(map(str, perm))
        pygame.image.save(pygame.image.frombuffer(sprite.to_rgba_bytes(), (w, h), "RGBA"), f"perms/perm_{name}.png")
        print(f"Saved perms/perm_{name}.png")

if __name__ == "__main__":
    main()
