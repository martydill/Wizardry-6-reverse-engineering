import sys
import math

def calculate_entropy(data):
    if not data:
        return 0
    entropy = 0
    for i in range(256):
        p_i = data.count(i) / len(data)
        if p_i > 0:
            entropy -= p_i * math.log2(p_i)
    return entropy

def scan_for_maps(filename):
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Check every 8 bytes
    results = []
    window_size = 2048 # Minimum map size (16x16x8)
    
    for offset in range(14, len(data) - window_size, 8):
        window = data[offset : offset + window_size]
        
        # Count cells with wall bits
        wall_cells = 0
        for i in range(0, window_size, 8):
            b3 = window[i+3]
            b5 = window[i+5]
            if (b3 & 0xC0) or (b5 & 0xA0): # North/South or West/East
                wall_cells += 1
        
        wall_pct = wall_cells / (window_size / 8)
        zeros = window.count(0) / window_size
        entropy = calculate_entropy(window)
        
        if 0.05 < wall_pct < 0.6 and zeros > 0.4 and entropy > 1.0:
            results.append((offset, wall_pct, zeros, entropy))
    
    # Print only local maxima or changes in map-likeness
    print(f"{'Offset':<10} | {'Wall %':<8} | {'Zeros %':<8} | {'Entropy':<8}")
    print("-" * 50)
    
    last_offset = -10000
    for res in results:
        if res[0] > last_offset + window_size:
            print(f"0x{res[0]:04X} ({res[0]:5d}) | {res[1]:7.1%} | {res[2]:7.1%} | {res[3]:7.2f}")
            last_offset = res[0]

scan_for_maps('gamedata/NEWGAME.DBS')
