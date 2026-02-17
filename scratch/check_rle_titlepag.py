from bane.data.pic_decoder import _decode_rle
from pathlib import Path

path = Path("gamedata/TITLEPAG.EGA")
data = path.read_bytes()
decompressed = _decode_rle(data)
print(f"Original size: {len(data)}")
print(f"Decompressed size: {len(decompressed)}")
