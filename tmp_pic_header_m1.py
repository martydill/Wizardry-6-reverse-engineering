import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

path = Path('gamedata/MON01.PIC')
d=_decode_rle(path.read_bytes())
header=struct.unpack('<H', d[:2])[0]
header_bytes = d[:header]
print('header size', header)
# dump first 5 records of 24 bytes
for i in range(5):
    rec = header_bytes[i*24:(i+1)*24]
    print(i, ' '.join(f'{b:02X}' for b in rec))
