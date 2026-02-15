
with open('gamedata/newgame0.dbs', 'rb') as f1, open('gamedata/newgame.dbs', 'rb') as f2:
    d1 = f1.read()
    d2 = f2.read()

diffs = []
for i in range(min(len(d1), len(d2))):
    if d1[i] != d2[i]:
        diffs.append((i, d1[i], d2[i]))

for offset, old, new in diffs:
    print(f"0x{offset:04X}: 0x{old:02X} -> 0x{new:02X}")
