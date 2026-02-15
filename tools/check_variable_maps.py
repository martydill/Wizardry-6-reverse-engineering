import math

def get_entropy(data):
    if not data: return 0
    counts = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    entropy = 0
    for count in counts.values():
        p = count / len(data)
        entropy -= p * math.log2(p)
    return entropy

def check():
    with open('gamedata/NEWGAME.DBS', 'rb') as f:
        data = f.read()
    
    offsets = []
    curr = 0
    for i in range(16):
        offsets.append(curr)
        if i == 10:
            size = 16 * 16 * 8 # 2048
        else:
            size = 20 * 20 * 8 # 3200
        curr += size
        
    print(f"{'Map':<6} | {'Offset':<10} | {'Entropy':<8} | {'Zero %':<8}")
    for i, off in enumerate(offsets):
        if off + 2048 > len(data): break
        chunk = data[off:off+2048] # Just check first 2048 bytes
        ent = get_entropy(chunk)
        zeros = chunk.count(0) / len(chunk) * 100
        print(f"{i:<6} | 0x{off:04X} | {ent:8.2f} | {zeros:7.1f}%")

if __name__ == "__main__":
    check()
