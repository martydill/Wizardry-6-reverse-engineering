
import pygame
from pathlib import Path
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, Sprite
import os

def main():
    path = Path('gamedata/titlepag.ega')
    data = path.read_bytes()
    print(f"File size: {len(data)}")

    # Create output directory
    os.makedirs('output', exist_ok=True)

    decoder = EGADecoder()
    
    def decode_8k_planes(data, w, h, msb_first):
        pixels = [0] * (w * h)
        bytes_per_row = w // 8
        for plane in range(4):
            plane_base = plane * 8192
            for y in range(h):
                row_base = plane_base + y * bytes_per_row
                for bx in range(bytes_per_row):
                    byte_val = data[row_base + bx]
                    for bit in range(8):
                        if msb_first:
                            x = bx * 8 + (7 - bit)
                        else:
                            x = bx * 8 + bit
                        if byte_val & (1 << bit):
                            pixels[y * w + x] |= (1 << plane)
        return Sprite(w, h, pixels, DEFAULT_16_PALETTE)

    # Try extracting palette from first 768 bytes
    pal_data = data[:768]
    extracted_palette = []
    for i in range(16):
        r = pal_data[i*3]
        g = pal_data[i*3+1]
        b = pal_data[i*3+2]
        extracted_palette.append((r, g, b))
    
    decoder_custom = EGADecoder(palette=extracted_palette)

    configs = [
        ("row_interleaved_custom_pal_768", 768, decoder_custom.decode_planar_row_interleaved, True),
        ("row_interleaved_default_pal_768", 768, decoder.decode_planar_row_interleaved, True),
    ]

    pygame.display.init()
    
    for name, offset, func, msb in configs:
        try:
            print(f"Trying {name}...")
            if "160" in name:
                w, h = 160, 200
            elif "100" in name:
                w, h = 320, 100
            else:
                w, h = 320, 200
            sprite = func(data[offset:], w, h, msb)
            
            # Calculate score
            pixels = sprite.pixels
            width = sprite.width
            height = sprite.height
            s = 0
            for y in range(height):
                row = pixels[y*width:(y+1)*width]
                for x in range(1, width):
                    if row[x] == row[x-1]:
                        s += 1
            for x in range(width):
                prev = pixels[x]
                for y in range(1, height):
                    v = pixels[y*width + x]
                    if v == prev:
                        s += 1
                    prev = v
            
            print(f"  Score: {s}")
            
            rgba = sprite.to_rgba_bytes()
            surf = pygame.image.frombuffer(rgba, (320, 200), "RGBA")
            pygame.image.save(surf, f"output/{name}.png")
            print(f"  Saved output/{name}.png")
        except Exception as e:
            print(f"Error decoding {name}: {e}")

    pygame.quit()

if __name__ == "__main__":
    main()
