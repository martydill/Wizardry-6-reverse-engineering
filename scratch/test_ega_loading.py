from bane.data.sprite_decoder import decode_ega_frames
from pathlib import Path

path = Path("gamedata/TITLEPAG.EGA")
frames = decode_ega_frames(path)
print(f"Number of frames: {len(frames)}")
if frames:
    sprite = frames[0]
    print(f"Sprite dimensions: {sprite.width}x{sprite.height}")
    print(f"First 16 colors of palette:")
    for i in range(16):
        print(f"  {i}: {sprite.palette[i]}")
