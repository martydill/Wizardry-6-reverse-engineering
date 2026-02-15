
def compare_files(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        data1 = f1.read()
        data2 = f2.read()
    
    if len(data1) != len(data2):
        print(f"Files have different sizes: {len(data1)} vs {len(data2)}")
    
    diffs = []
    for i in range(min(len(data1), len(data2))):
        if data1[i] != data2[i]:
            diffs.append((i, data1[i], data2[i]))
    
    return diffs

diffs = compare_files('gamedata/newgame0.dbs', 'gamedata/newgame.dbs')
print(f"Total differences: {len(diffs)}")
for offset, old, new in diffs[:100]:
    print(f"Offset: 0x{offset:04X} ({offset}), Old: 0x{old:02X}, New: 0x{new:02X}")

if len(diffs) > 100:
    print("...")
