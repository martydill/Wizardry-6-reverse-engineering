import pygame
from pathlib import Path
from bane.data.sprite_decoder import EGADecoder, DEFAULT_16_PALETTE, TITLEPAG_PALETTE, Sprite

def test():
    path = Path('gamedata/TITLEPAG.EGA')
    if not path.exists():
        print("File not found")
        return
    data = path.read_bytes()
    
    pygame.display.init()
    
    # 1. Sequential Planar, Extracted Palette (Current)
    palette_ext = []
    for i in range(16):
        r = min(255, data[i * 3] * 4)
        g = min(255, data[i * 3 + 1] * 4)
        b = min(255, data[i * 3 + 2] * 4)
        palette_ext.append((r, g, b))
    
    decoder_ext = EGADecoder(palette=palette_ext)
    s1 = decoder_ext.decode_planar(data[768:768+32000], 320, 200)
    pygame.image.save(pygame.image.frombuffer(s1.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_seq_ext.png")

    # 2. Sequential Planar, TITLEPAG_PALETTE
    decoder_title = EGADecoder(palette=TITLEPAG_PALETTE)
    s2 = decoder_title.decode_planar(data[768:768+32000], 320, 200)
    pygame.image.save(pygame.image.frombuffer(s2.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_seq_titlepal.png")

    # 3. Tiled Planar, Default Palette (What it might have been doing before, sort of)
    decoder_def = EGADecoder(palette=DEFAULT_16_PALETTE)
    # Note: decode_pic_bytes was using offset from header, but if header was junk...
    # Let's try offset 0 and 768
    try:
        s3 = decoder_def.decode_tiled_planar(data[:32000], 320, 200)
        pygame.image.save(pygame.image.frombuffer(s3.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_tiled_0.png")
        s4 = decoder_def.decode_tiled_planar(data[768:768+32000], 320, 200)
        pygame.image.save(pygame.image.frombuffer(s4.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_tiled_768.png")
    except:
        pass

    # 5. Sequential Planar, TITLEPAG_PALETTE, Plane Order [3, 0, 2, 1]
    s6 = decoder_title.decode_planar(data[768:768+32000], 320, 200, plane_order=[3, 0, 2, 1])
    pygame.image.save(pygame.image.frombuffer(s6.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_seq_titlepal_3021.png")

    # 6. Sequential Planar, Extracted Palette (8-bit check), Plane Order [3, 0, 2, 1]
    is_vga = all(b <= 63 for b in data[:768])
    mult = 4 if is_vga else 1
    pal8 = []
    for i in range(16):
        pal8.append((min(255, data[i*3]*mult), min(255, data[i*3+1]*mult), min(255, data[i*3+2]*mult)))
    decoder8 = EGADecoder(palette=pal8)
    s7 = decoder8.decode_planar(data[768:768+32000], 320, 200, plane_order=[3, 0, 2, 1])
    pygame.image.save(pygame.image.frombuffer(s7.to_rgba_bytes(), (320, 200), "RGBA"), "scratch/title_seq_ext8_3021.png")

    pygame.quit()

test()
