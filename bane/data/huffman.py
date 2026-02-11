import struct
from pathlib import Path

class HuffmanDecoder:
    """Huffman decoder using the tree format found in Wizardry 6 HDR files.
    
    The tree is composed of 4-byte nodes. Each node has two 16-bit signed words:
    [Left Child, Right Child].
    - Negative values: Pointer to another node (e.g., -1 -> Node 1).
    - Non-negative values: Literal leaf value (usually ASCII character code).
    """

    def __init__(self, tree_data: bytes):
        self.nodes = []
        # The tree usually fits in 1024 bytes (256 nodes)
        for i in range(0, len(tree_data), 4):
            if i + 4 > len(tree_data):
                break
            left, right = struct.unpack("<hh", tree_data[i:i+4])
            self.nodes.append((left, right))

    @classmethod
    def from_file(cls, path: str | Path) -> "HuffmanDecoder":
        """Load the Huffman tree from a file (e.g., MISC.HDR)."""
        return cls(Path(path).read_bytes())

    def decode(self, compressed_data: bytes, uncompressed_len: int, bit_offset: int = 0) -> bytes:
        """Decode Huffman-compressed data.
        
        Args:
            compressed_data: The raw compressed bytes.
            uncompressed_len: Number of values to decode.
            bit_offset: Starting bit position within the data.
            
        Returns:
            The decoded bytes.
        """
        out = bytearray()
        node_idx = 0
        bit_ptr = bit_offset
        
        while len(out) < uncompressed_len:
            byte_idx = bit_ptr // 8
            if byte_idx >= len(compressed_data):
                break
                
            bit_idx = bit_ptr % 8
            # Wizardry 6 uses MSB-first for Huffman bits
            bit = (compressed_data[byte_idx] >> (7 - bit_idx)) & 1
            bit_ptr += 1
            
            if node_idx >= len(self.nodes):
                break
                
            left, right = self.nodes[node_idx]
            next_val = left if bit == 0 else right
            
            if next_val >= 0:
                # Leaf node: output value and reset to root
                out.append(next_val & 0xFF)
                node_idx = 0
            else:
                # Internal node: follow the branch
                node_idx = -next_val
                
        return bytes(out)
