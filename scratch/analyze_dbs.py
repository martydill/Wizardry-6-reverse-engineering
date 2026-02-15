import struct
from collections import Counter

class HuffmanAnalyzer:
    def __init__(self, tree_path):
        with open(tree_path, 'rb') as f:
            data = f.read(1024)
        self.nodes = []
        for i in range(0, 1024, 4):
            left, right = struct.unpack('<hh', data[i:i+4])
            self.nodes.append((left, right))

    def analyze_block(self, compressed_data, uncompressed_len):
        counts = []
        node_idx = 0
        bit_ptr = 0
        while len(counts) < uncompressed_len:
            byte_idx = bit_ptr // 8
            if byte_idx >= len(compressed_data): break
            bit_idx = bit_ptr % 8
            bit = (compressed_data[byte_idx] >> (7 - bit_idx)) & 1
            bit_ptr += 1
            
            left, right = self.nodes[node_idx]
            next_val = left if bit == 0 else right
            if next_val >= 0:
                counts.append(next_val)
                node_idx = 0
            else:
                node_idx = -next_val
        return counts

def main():
    analyzer = HuffmanAnalyzer('gamedata/MISC.HDR')
    with open('gamedata/MSG.DBS', 'rb') as f:
        data = f.read()
    
    all_vals = []
    i = 0
    while i < len(data) - 1:
        ulen = data[i]
        clen = data[i+1]
        if i + 2 + clen > len(data): break
        vals = analyzer.analyze_block(data[i+2:i+2+clen], ulen)
        all_vals.extend(vals)
        i += 2 + clen
    
    c = Counter(all_vals)
    print("Top 10 most frequent decoded values:")
    for val, count in c.most_common(10):
        print(f"Value {val} ({chr(val) if 32 <= val <= 126 else '?' }): {count}")

if __name__ == "__main__":
    main()
