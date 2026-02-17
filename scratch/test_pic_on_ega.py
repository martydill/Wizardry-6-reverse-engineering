from bane.data.pic_decoder import decode_pic_frames
from pathlib import Path

path = Path("gamedata/TITLEPAG.EGA")
try:
    frames = decode_pic_frames(path.read_bytes())
    print(f"Number of PIC frames: {len(frames)}")
    if frames:
        for i, frame in enumerate(frames):
            print(f"  Frame {i}: {frame.width}x{frame.height}")
except Exception as e:
    print(f"PIC decoding failed: {e}")
