def check_boundary(offset, w, h):
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    print("Checking {}x{} boundary at 0x{:04X}".format(w, h, offset))
    
    # North walls of top row
    n_walls = []
    for c in range(w):
        idx = offset + (0 * w + c) * 8
        if idx + 3 >= len(data): break
        b3 = data[idx + 3]
        n_walls.append(1 if b3 & 0x80 else 0)
    print("Top row North bits: {}".format(n_walls))

    # West walls of left column
    w_walls = []
    for r in range(h):
        idx = offset + (r * w + 0) * 8
        if idx + 5 >= len(data): break
        b5 = data[idx + 5]
        w_walls.append(1 if b5 & 0x80 else 0)
    print("Left col West bits: {}".format(w_walls))

if __name__ == "__main__":
    check_boundary(0x7D00, 16, 16)
    print("\n--- Try 20x20 ---")
    check_boundary(0x7D00, 20, 20)
