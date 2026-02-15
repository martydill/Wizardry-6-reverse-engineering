def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    # 10 maps of 20x20 (14 00 14 00) then 1 map of 16x16 (10 00 10 00)
    target = b'\x14\x00\x14\x00' * 10 + b'\x10\x00\x10\x00'
    pos = data.find(target)
    if pos != -1:
        print(f"Found 10x20x20 + 1x16x16 at 0x{pos:04X}")
    else:
        # Try just widths then heights
        target = b'\x14' * 10 + b'\x10'
        pos = data.find(target)
        if pos != -1:
            print(f"Found 10x20 + 1x16 (bytes) at 0x{pos:04X}")

if __name__ == "__main__":
    search()
