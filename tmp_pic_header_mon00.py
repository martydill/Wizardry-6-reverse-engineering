import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

path=Path('gamedata/MON00.PIC')
d=_decode_rle(path.read_bytes())
header=struct.unpack('<H', d[:2])[0]
print('header', header)
for i in range(25):
    rec = d[i*24:(i+1)*24]
    words = struct.unpack('<12H', rec)
    if words[0]==0 and words[1]==0:
        break
    print(i, words[:4])
