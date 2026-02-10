import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

path = Path('gamedata/MON13.PIC')
d=_decode_rle(path.read_bytes())
header=struct.unpack('<H', d[:2])[0]
print('header', header)
for i in range(12):
    rec = d[i*24:(i+1)*24]
    words = struct.unpack('<12H', rec)
    print(i, words)
