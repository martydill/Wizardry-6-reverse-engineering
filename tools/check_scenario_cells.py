with open('gamedata/SCENARIO.DBS', 'rb') as f:
    f.seek(0xA000)
    for i in range(5):
        cell = f.read(20)
        print(f"Cell {i}: {cell.hex(' ')}")
