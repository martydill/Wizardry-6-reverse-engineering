import sys

def analyze(file1, file2):
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        d1 = f1.read()
        d2 = f2.read()
    
    diffs = []
    for i in range(min(len(d1), len(d2))):
        if d1[i] != d2[i]:
            diffs.append((i, d1[i], d2[i]))
    
    print(f"Found {len(diffs)} differences")
    
    # Try different offsets for map start
    for start_offset in [0, 0x1FA, 0x200, 0x250, 0x300]:
        print(f"\nAssuming map starts at 0x{start_offset:X}:")
        for size in [20, 32]:
            print(f"  Size {size}x{size}:")
            for offset, b1, b2 in diffs:
                rel = offset - start_offset
                if rel < 0: continue
                
                # Row-major
                y = rel // size
                x = rel % size
                if y < size:
                    print(f"    Offset 0x{offset:X} (rel {rel:3d}): Row-major ({x:2d}, {y:2d}) | {b1:02X} -> {b2:02X}")
                
                # Column-major
                x2 = rel // size
                y2 = rel % size
                if x2 < size:
                    print(f"    Offset 0x{offset:X} (rel {rel:3d}): Col-major ({x2:2d}, {y2:2d}) | {b1:02X} -> {b2:02X}")

if __name__ == '__main__':
    analyze('gamedata/NEWGAME.DBS', 'gamedata/newgameoriginal.DBS')
