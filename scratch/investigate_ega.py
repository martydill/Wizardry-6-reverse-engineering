
import pygame
import os
from pathlib import Path

def save_gray(pixels, w, h, name):
    surf = pygame.Surface((w, h))
    for y in range(h):
        for x in range(w):
            v = pixels[y*w + x]
            c = v * 255
            surf.set_at((x, y), (c, c, c))
    pygame.image.save(surf, name)

def extract_planes_planar(data, w, h):
    # Standard Planar: Plane 0 (all), Plane 1 (all)...
    plane_size = (w * h) // 8
    planes = []
    for p in range(4):
        p_data = data[p*plane_size : (p+1)*plane_size]
        pixels = []
        for b in p_data:
            for i in range(8):
                pixels.append((b >> (7-i)) & 1)
        planes.append(pixels)
    return planes

def extract_planes_interleaved(data, w, h):
    # Row Interleaved: Row 0 (P0, P1, P2, P3), Row 1...
    bytes_per_row_plane = w // 8
    planes = [[], [], [], []]
    
    for y in range(h):
        row_start = y * bytes_per_row_plane * 4
        for p in range(4):
            p_start = row_start + p * bytes_per_row_plane
            p_data = data[p_start : p_start + bytes_per_row_plane]
            for b in p_data:
                for i in range(8):
                    planes[p].append((b >> (7-i)) & 1)
    return planes

def main():
    pygame.init()
    os.makedirs('debug_output', exist_ok=True)
    
    path = Path('gamedata/TITLEPAG.EGA')
    data = path.read_bytes()
    
    # Try offset 768 (assuming header/palette)
    payload = data[768:]
    w, h = 320, 200
    
    if len(payload) < 32000:
        print("Payload too small")
        return

    # 1. Standard Planar Planes
    print("Extracting Standard Planar Planes...")
    planes = extract_planes_planar(payload, w, h)
    for i, p in enumerate(planes):
        save_gray(p, w, h, f"debug_output/plane_std_{i}.png")

    # 2. Row Interleaved Planes
    print("Extracting Row Interleaved Planes...")
    planes = extract_planes_interleaved(payload, w, h)
    for i, p in enumerate(planes):
        save_gray(p, w, h, f"debug_output/plane_int_{i}.png")

    # 3. Packed Linear (to see if it looks like a grayscale image)
    print("Extracting Packed Linear...")
    pixels = []
    for b in payload:
        pixels.append((b >> 4) & 0xF)
        pixels.append(b & 0xF)
    
    # Map 0-15 to 0-255 for grayscale
    pixels_gray = [p * 17 for p in pixels]
    
    surf = pygame.Surface((w, h))
    for y in range(h):
        for x in range(w):
            c = pixels_gray[y*w + x]
            surf.set_at((x, y), (c, c, c))
    pygame.image.save(surf, "debug_output/packed.png")

    print("Done. Check debug_output/")

if __name__ == "__main__":
    main()
