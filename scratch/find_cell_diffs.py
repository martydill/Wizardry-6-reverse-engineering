
with open('gamedata/newgame0.dbs', 'rb') as f1, open('gamedata/newgame.dbs', 'rb') as f2:
    d1 = f1.read()
    d2 = f2.read()

diffs = []
for i in range(min(len(d1), len(d2))):
    if d1[i] != d2[i]:
        diffs.append(i)

if not diffs:
    print("No differences found.")
else:
    print(f"Total differences: {len(diffs)}")
    # Group by potential cell (20 bytes)
    cell_changes = set(i // 20 for i in diffs)
    for cell_idx in sorted(cell_changes):
        offset = cell_idx * 20
        print(f"Cell {cell_idx} (Offset 0x{offset:04X}) changed:")
        for i in range(offset, offset + 20):
            if i < len(d1) and d1[i] != d2[i]:
                print(f"  Byte {i-offset:2d}: 0x{d1[i]:02X} -> 0x{d2[i]:02X}")
