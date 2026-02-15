
import pygame
import os
from pathlib import Path
from bane.data.sprite_decoder import Sprite, DEFAULT_16_PALETTE

def decode_sequential_planar(data, w, h, palette):
    pixels = [0] * (w * h)
    bytes_per_row = w // 8
    plane_size = bytes_per_row * h # 8000
    for plane in range(4):
        plane_base = plane * plane_size
        for y in range(h):
            row_base = plane_base + y * bytes_per_row
            for bx in range(bytes_per_row):
                byte_val = data[row_base + bx]
                for bit in range(8):
                    # Try MSB first
                    x = bx * 8 + (7 - bit)
                    if byte_val & (1 << bit):
                        pixels[y * w + x] |= (1 << plane)
    return Sprite(w, h, pixels, palette)

def main():
    pygame.init()
    os.makedirs('output_new', exist_ok=True)
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    
    # Layout: [8000 P0][8000 P1][8000 P2][8000 P3][768 Palette]
    image_data = data[:32000]
    pal_data = data[32000:]
    
    # Try different palette extractions
    # 1. First 16 colors from the end palette
    palette = []
    for i in range(16):
        r, g, b = pal_data[i*3 : i*3+3]
        palette.append((r, g, b))
        
    sprite = decode_sequential_planar(image_data, 320, 200, palette)
    pygame.image.save(pygame.image.frombuffer(sprite.to_rgba_bytes(), (320, 200), "RGBA"), "output_new/sequential_end_pal.png")

    # Try 8k spacing but with header AT THE START of each plane
    # [192 Header][8000 Plane 0][192 Header][8000 Plane 1] ...
    def decode_8k_header_start(data, w, h):
        pixels = [0] * (w * h)
        bytes_per_row = w // 8
        header_data = bytearray()
        for plane in range(4):
            plane_base = plane * 8192
            header_data.extend(data[plane_base : plane_base + 192])
            for y in range(h):
                row_base = plane_base + 192 + y * bytes_per_row
                for bx in range(bytes_per_row):
                    byte_val = data[row_base + bx]
                    for bit in range(8):
                        x = bx * 8 + (7 - bit)
                        if byte_val & (1 << bit):
                            pixels[y * w + x] |= (1 << plane)
        
        # Extract palette from the combined 768-byte header
        palette = []
        for i in range(16):
            r, g, b = header_data[i*3 : i*3+3]
            palette.append((r, g, b))
        return Sprite(w, h, pixels, palette)

    sprite = decode_8k_header_start(data, 320, 200)
    pygame.image.save(pygame.image.frombuffer(sprite.to_rgba_bytes(), (320, 200), "RGBA"), "output_new/8k_header_start.png")

    # What if the palette is at the START?
    pal_data_start = data[:768]
    image_data_start = data[768:]
    palette_start = []
    for i in range(16):
        r, g, b = pal_data_start[i*3 : i*3+3]
        palette_start.append((r, g, b))
    
    # If planar sequential at 768 offset
    sprite = decode_sequential_planar(image_data_start, 320, 200, palette_start)
    pygame.image.save(pygame.image.frombuffer(sprite.to_rgba_bytes(), (320, 200), "RGBA"), "output_new/sequential_start_pal.png")

if __name__ == "__main__":
    main()
