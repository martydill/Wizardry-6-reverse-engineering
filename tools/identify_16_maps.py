import math

def calculate_entropy(data):
    if not data:
        return 0
    counts = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    entropy = 0
    for count in counts.values():
        p = count / len(data)
        entropy -= p * math.log2(p)
    return entropy

def analyze_maps(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print(f"Total cells (if 8 bytes/cell): {len(data) // 8}")
    
    map_size = 3200 # 20x20x8
    
    print(f"\nScanning for up to 16 maps of size 20x20...")
    header = "{:<8} | {:<10} | {:<10} | {:<10} | {:<10}".format("Map #", "Offset", "Entropy", "Zero %", "Status")
    print(header)
    print("-" * 60)
    
    for i in range(16):
        start = i * map_size
        end = start + map_size
        chunk = data[start:end]
        
        if not chunk:
            break
            
        entropy = calculate_entropy(chunk)
        zeros = chunk.count(0) / len(chunk) * 100
        
        status = "Map?" if entropy < 4.5 and zeros > 20 else "Other"
        if len(chunk) < map_size:
            status = "Partial"
            
        print("{:<8} | 0x{:04X}   | {:10.2f} | {:9.1f}% | {:<10}".format(i, start, entropy, zeros, status))

if __name__ == "__main__":
    analyze_maps('gamedata/NEWGAME.DBS')
