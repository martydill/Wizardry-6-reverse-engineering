import pygame
import json
import sys
from pathlib import Path
from bane.data.pic_decoder import decode_pic_frames
from bane.data.sprite_decoder import TITLEPAG_PALETTE
from credits_animation import extract_credits_data

# Configuration
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 200
SCALE = 1
FPS = 30  # Standard animation speed

def render_credits(pic_path: str, winit_path: str):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH * SCALE, SCREEN_HEIGHT * SCALE))
    pygame.display.set_caption("Wizardry 6 Credits")
    clock = pygame.time.Clock()

    # Load and decode frames
    print(f"Loading {pic_path}...")
    with open(pic_path, "rb") as f:
        pic_data = f.read()
    frames = decode_pic_frames(pic_data)
    
    # Pre-render frames to surfaces
    frame_surfs = []
    for sprite in frames:
        surf = pygame.Surface((sprite.width, sprite.height))
        for i, color_idx in enumerate(sprite.pixels):
            px, py = i % sprite.width, i // sprite.width
            # Use TITLEPAG_PALETTE for correct colors (index 5 = Yellow)
            color = TITLEPAG_PALETTE[color_idx]
            surf.set_at((px, py), color)
        surf.set_colorkey(TITLEPAG_PALETTE[15])
        frame_surfs.append(surf)

    # Load animation data directly from WINIT.OVR
    print(f"Extracting animation from {winit_path}...")
    animation = extract_credits_data(winit_path)

    # Correct hard-coded splash offsets
    # Frame 11 (Sir-Tech) is at 84, 84
    animation["intro_splash"][1] = {"frame_idx": 11, "x_coord": 84, "y_coord": 84}
    # Frame 9 (Bane of the Cosmic Forge) is at 84, 82
    animation["credits_splash"][1] = {"frame_idx": 9, "x_coord": 84, "y_coord": 82}

    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    def update_display():
        pygame.transform.scale(canvas, (SCREEN_WIDTH * SCALE, SCREEN_HEIGHT * SCALE), screen)
        pygame.display.flip()

    def wait_or_quit(ms):
        start = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start < ms:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                    pygame.quit()
                    sys.exit()
            clock.tick(60)

    # --- Phase 1: Intro Splash (Logo) ---
    canvas.fill((0, 0, 0))
    for s in animation["intro_splash"]:
        canvas.blit(frame_surfs[s["frame_idx"]], (s["x_coord"], s["y_coord"]))
        update_display()
        wait_or_quit(1000)
    wait_or_quit(1000)

    # --- Phase 2: Credits Header ---
    canvas.fill((0, 0, 0))
    for s in animation["credits_splash"]:
        # Frame 13 is empty/clear command in some versions, skip if out of range
        idx = s["frame_idx"]
        if idx < len(frame_surfs):
            canvas.blit(frame_surfs[idx], (s["x_coord"], s["y_coord"]))
    update_display()
    wait_or_quit(1500)

    # --- Phase 3: Scrolling Credits ---
    # The scroll_pos acts as the global timer/offset
    # Logic from WINIT.OVR: 
    #   Relative_Offset = scroll_pos - Trigger_Y
    #   Current_Y = Base_Y - Relative_Offset
    
    for scroll_pos in range(0, 350):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                pygame.quit()
                sys.exit()

        canvas.fill((0, 0, 0))
        
        # Keep the header (Frame 9 and 12) visible or let them scroll?
        # In the game, they usually stay or scroll with the first block.
        # We follow the table precisely:
        for step in animation["main_scroll"]:
            trigger_y = step["y_coord"]
            base_y = step["flag"]
            
            if scroll_pos >= trigger_y:
                offset = scroll_pos - trigger_y
                draw_y = base_y - offset
                
                # Draw if frame is within vertical screen bounds
                if -64 < draw_y < SCREEN_HEIGHT:
                    canvas.blit(frame_surfs[step["frame_idx"]], (step["x_coord"], draw_y))
        
        update_display()
        clock.tick(FPS)

    print("Animation complete.")
    wait_or_quit(2000)
    pygame.quit()

if __name__ == "__main__":
    pic = "gamedata/CREDITS.PIC"
    winit = "gamedata/WINIT.OVR"
    render_credits(pic, winit)
