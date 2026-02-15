def compare():
    with open('gamedata/NEWGAME.DBS', 'rb') as fn, open('gamedata/newgameoriginal.DBS', 'rb') as fo:
        dn, do = fn.read(), fo.read()
    
    diffs = [i for i in range(len(dn)) if dn[i] != do[i]]
    if not diffs: return

    # Group differences by cell
    cells = {}
    for d in diffs:
        c = d // 8
        if c not in cells: cells[c] = []
        cells[c].append(d % 8)

    print(f"Total cells changed: {len(cells)}")
    
    # Check if they follow a pattern of Width W, Column C
    for w in range(1, 41):
        cols = set(c % w for c in cells.keys())
        if len(cols) == 1:
            print(f"Width {w} -> All changes in Column {list(cols)[0]}")
        elif len(cols) <= 2:
            # print(f"Width {w} -> Changes in Columns {cols}")
            pass

    # Print first few changed cells
    sorted_cells = sorted(cells.keys())
    for c in sorted_cells:
        print(f"Cell {c}: Row={c//20} Col={c%20} (W=20) | Row={c//32} Col={c%32} (W=32)")

if __name__ == "__main__":
    compare()
