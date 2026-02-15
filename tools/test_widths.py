def test():
    with open('gamedata/NEWGAME.DBS', 'rb') as fn, open('gamedata/newgameoriginal.DBS', 'rb') as fo:
        dn, do = fn.read(), fo.read()
    
    diffs = [i for i in range(len(dn)) if dn[i] != do[i]]
    if not diffs: return

    for bpc in [8]:
        for w in range(1, 100):
            cols = set((d // bpc) % w for d in diffs)
            if len(cols) == 1:
                print(f"BPC {bpc}, Width {w} -> Column {list(cols)[0]}")

test()
