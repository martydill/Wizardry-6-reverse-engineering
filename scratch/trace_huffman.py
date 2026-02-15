import struct

class HuffmanTree:
    def __init__(self, tree_path):
        with open(tree_path, 'rb') as f:
            data = f.read()
        self.nodes = []
        for i in range(0, 1024, 4):
            left, right = struct.unpack('<hh', data[i:i+4])
            self.nodes.append((left, right))

    def get_path(self, target_val, node_idx=0, current_path=""):
        if node_idx < 0:
            node_idx = -node_idx
        if node_idx >= len(self.nodes):
            return None
        left, right = self.nodes[node_idx]
        if left == target_val: return current_path + "0"
        elif left < 0:
            res = self.get_path(target_val, left, current_path + "0")
            if res: return res
        if right == target_val: return current_path + "1"
        elif right < 0:
            res = self.get_path(target_val, right, current_path + "1")
            if res: return res
        return None

def test():
    tree = HuffmanTree('gamedata/MISC.HDR')
    print("Paths for HUMAN:")
    for char in "HUMAN":
        print(f"'{char}': {tree.get_path(ord(char))}")
        
    print("\nPaths for other races:")
    for race in ["ELF", "DWARF", "GNOME", "HOBBIT", "FAERIE"]:
        print(f"{race}: {' '.join([tree.get_path(ord(c)) or '?' for c in race])}")

if __name__ == "__main__":
    test()