with open('gamedata/NEWGAME.DBS', 'rb') as f_n, open('gamedata/newgameoriginal.DBS', 'rb') as f_o:
    d_n, d_o = f_n.read(), f_o.read()
    diffs = [i for i in range(len(d_n)) if d_n[i] != d_o[i]]

print(f"Diffs: {diffs}")
cells = [d // 8 for d in diffs]
print(f"Cells: {cells}")

# Look at intervals between cells
intervals = [cells[i] - cells[i-1] for i in range(1, len(cells))]
print(f"Intervals: {intervals}")
