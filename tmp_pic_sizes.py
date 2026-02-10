import struct
from pathlib import Path
from bane.data.pic_decoder import _decode_rle

for path in sorted(Path('gamedata').glob('MON*.PIC')):
    d=_decode_rle(path.read_bytes())
    if len(d)<2:
        print(path.name,'too short')
        continue
    header=struct.unpack('<H', d[:2])[0]
    payload=len(d)-header
    print(path.name, 'comp', path.stat().st_size, 'decomp', len(d), 'header', header, 'payload', payload)
