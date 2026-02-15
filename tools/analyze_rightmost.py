def analyze():
    with open('gamedata/NEWGAME.DBS', 'rb') as fn, open('gamedata/newgameoriginal.DBS', 'rb') as fo:
        dn, do = fn.read(), fo.read()
    
    diffs = [i for i in range(len(dn)) if dn[i] != do[i]]
    if not diffs: return

    # Group by cell (assuming 8 bytes per cell)
    cell_changes = {}
    for d in diffs:
        cell_idx = d // 8
        byte_in_cell = d % 8
        if cell_idx not in cell_changes:
            cell_changes[cell_idx] = []
        cell_changes[cell_idx].append((byte_in_cell, do[d], dn[d]))

    print(f"{'Cell':<6} {'Row (W=64)':<10} {'Col (W=64)':<10} {'Changes'}")
    for cell_idx in sorted(cell_changes.keys()):
        row = cell_idx // 64
        col = cell_idx % 64
        changes = ", ".join([f"B{b}: {old:02X}->{new:02X}" for b, old, new in cell_changes[cell_idx]])
        print(f"{cell_idx:<6} {row:<10} {col:<10} {changes}")

if __name__ == "__main__":
    analyze()
