import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

def dump(path, n=32):
    d=_decode_rle(Path(path).read_bytes())
    header=struct.unpack('<H', d[:2])[0]
    words=struct.unpack('<'+'H'*(min(header, n*2)//2), d[:min(header, n*2)])
    print(path, 'header', header)
    print(words)

for name in ['MON00.PIC','MON01.PIC','MON02.PIC']:
    dump('gamedata/'+name, n=48)
