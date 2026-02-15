
import struct
from pathlib import Path
import pygame
from bane.data.sprite_decoder import EGADecoder, TITLEPAG_PALETTE, DEFAULT_16_PALETTE

def get_titlepag_palette():
    data = Path("gamedata/TITLEPAG.EGA").read_bytes()
    palette = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette.append((r, g, b))
    return palette

def save_image(pixels, width, height, palette, filename):
    rgba = bytearray(width * height * 4)
    for i, p in enumerate(pixels):
        c = palette[p % 16]
        rgba[i*4] = c[0]
        rgba[i*4+1] = c[1]
        rgba[i*4+2] = c[2]
        rgba[i*4+3] = 255
    
    pygame.init()
    surf = pygame.image.frombuffer(bytes(rgba), (width, height), "RGBA")
    pygame.image.save(surf, filename)

def main():
    palette = TITLEPAG_PALETTE
    
    path = Path("gamedata/WPORT1.EGA")
    data = path.read_bytes()
    portrait_data = data[:288]
    
    decoder = EGADecoder(palette=palette)
    
    # Try different plane orders with the title screen palette
    for order in [[0,1,2,3], [3,0,2,1], [3,2,1,0]]:
        sprite = decoder.decode_tiled_planar(portrait_data, 24, 24, plane_order=order)
        save_image(sprite.pixels, 24, 24, palette, f"output/wport_tp_pal_{''.join(map(str, order))}.png")

    # Also try default palette with 3021
    sprite = EGADecoder(palette=DEFAULT_16_PALETTE).decode_tiled_planar(portrait_data, 24, 24, plane_order=[3,0,2,1])
    save_image(sprite.pixels, 24, 24, DEFAULT_16_PALETTE, "output/wport_def_pal_3021.png")

if __name__ == "__main__":
    main()
