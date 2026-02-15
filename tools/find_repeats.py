def search():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    counts = {}
    for i in range(0, len(data) - 8, 8):
        chunk = data[i:i+8]
        counts[chunk] = counts.get(chunk, 0) + 1
    
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    print("Most common 8-byte chunks:")
    for chunk, count in sorted_counts[:20]:
        print(f"{chunk.hex(' ')}: {count}")

if __name__ == "__main__":
    search()
