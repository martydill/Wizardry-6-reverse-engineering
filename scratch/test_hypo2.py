
import pygame
import os
from pathlib import Path
from bane.data.sprite_decoder import Sprite

def main():
    pygame.init()
    os.makedirs('output_shift', exist_ok=True)
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    
    # Hypothesis 2: [768 Palette][8000 P0][8000 P1][8000 P2][8000 P3]
    # Total = 768 + 32000 = 32768. EXACT MATCH.
    
    pal_data = data[:768]
    palette = []
    for i in range(16):
        r, g, b = pal_data[i*3 : i*3+3]
        palette.append((r, g, b))
    
    image_data = data[768:]
    w, h = 320, 200
    
    for msb in [True, False]:
        pixels = [0] * (w * h)
        bytes_per_row = w // 8
        for plane in range(4):
            plane_base = plane * 8000
            for y in range(h):
                row_base = plane_base + y * bytes_per_row
                for bx in range(bytes_per_row):
                    byte_val = image_data[row_base + bx]
                    for bit in range(8):
                        if msb:
                            x = bx * 8 + (7 - bit)
                        else:
                            x = bx * 8 + bit
                        if byte_val & (1 << bit):
                            pixels[y * w + x] |= (1 << plane)
        
        sprite = Sprite(w, h, pixels, palette)
        name = "msb" if msb else "lsb"
        pygame.image.save(pygame.image.frombuffer(sprite.to_rgba_bytes(), (w, h), "RGBA"), f"output_shift/hypo2_{name}.png")
        print(f"Saved output_shift/hypo2_{name}.png")

if __name__ == "__main__":
    main()
