def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    valid = {16, 20, 24, 28, 32}
    
    print("Searching for dimension pairs...")
    for i in range(len(data) - 32):
        chunk = data[i:i+32]
        # Check if it looks like a list of (W, H) pairs
        is_dims = True
        for j in range(0, 32, 2):
            if chunk[j] not in valid or chunk[j+1] not in valid:
                is_dims = False
                break
        if is_dims:
            print(f"Possible dim list at 0x{i:04X}: {chunk.hex(' ')}")

if __name__ == "__main__":
    search()
