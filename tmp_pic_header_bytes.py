import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

path = Path('gamedata/MON00.PIC')
d=_decode_rle(path.read_bytes())
header=struct.unpack('<H', d[:2])[0]
header_bytes = d[:header]
print('header size', header)
print('first 96 bytes')
print(' '.join(f'{b:02X}' for b in header_bytes[:96]))
