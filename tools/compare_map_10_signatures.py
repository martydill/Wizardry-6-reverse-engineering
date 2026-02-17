import sys

def dump_range(filename, offset, length):
    with open(filename, 'rb') as f:
        f.seek(offset)
        data = f.read(length)
        return ' '.join(f'{b:02x}' for b in data)

print(f"SCENARIO.DBS at 0xA000: {dump_range('gamedata/SCENARIO.DBS', 0xA000, 32)}")
print(f"NEWGAME.DBS at 6958:   {dump_range('gamedata/NEWGAME.DBS', 6958, 32)}")
