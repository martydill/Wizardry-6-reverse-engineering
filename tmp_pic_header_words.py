import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

def dump(path, count=12):
    d=_decode_rle(Path(path).read_bytes())
    header=struct.unpack('<H', d[:2])[0]
    header_bytes = d[:header]
    print(path, 'header', header)
    for i in range(count):
        rec = header_bytes[i*24:(i+1)*24]
        if len(rec) < 24:
            break
        words = struct.unpack('<12H', rec)
        print(i, words)

for name in ['MON01.PIC','MON02.PIC','MON03.PIC']:
    dump('gamedata/'+name, count=10)
