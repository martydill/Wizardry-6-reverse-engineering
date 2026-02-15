import sys

def find_width(file_new, file_old):
    with open(file_new, 'rb') as f: d_new = f.read()
    with open(file_old, 'rb') as f: d_old = f.read()
    
    diffs = [i for i in range(len(d_new)) if d_new[i] != d_old[i]]
    if not diffs: return

    for bpc in [8]:
        # A cell at (r, c) is at offset: (r * width + c) * bpc + byte_in_cell
        # So (offset // bpc) % width should be the same for all diffs if they are in one column.
        
        for width in range(16, 65):
            cols = sorted(list(set((d // bpc) % width for d in diffs)))
            if len(cols) <= 2: # Allow a bit of noise or 2 adjacent columns
                print(f"Width {width}, BPC {bpc}: Columns {cols}")
                # Print rows too
                rows = sorted(list(set((d // bpc) // width for d in diffs)))
                # print(f"  Rows: {rows}")

if __name__ == "__main__":
    find_width('gamedata/NEWGAME.DBS', 'gamedata/newgameoriginal.DBS')
