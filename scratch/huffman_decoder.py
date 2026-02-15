#!/usr/bin/env python3
"""
Wizardry 6 Huffman decoder for MSG.DBS format.

MSG.HDR: Index file with message offsets
MSG.DBS: Huffman-encoded messages
MISC.HDR: Huffman tree (256 nodes, each 4 bytes: left/right as signed 16-bit ints)

Message format in MSG.DBS:
  Byte 0: Uncompressed length
  Byte 1: Compressed length
  Bytes 2+: Compressed data (Huffman encoded)
"""

import struct
from pathlib import Path


class HuffmanDecoder:
    """Huffman decoder using tree from MISC.HDR."""

    def __init__(self, tree_path):
        """Load Huffman tree from MISC.HDR.

        Tree format: 256 nodes × 4 bytes = 1024 bytes total
        Each node: [left: int16, right: int16]
          - Negative value: index to another node (use -value)
          - Non-negative value: decoded byte value (leaf node)
        """
        with open(tree_path, 'rb') as f:
            data = f.read()

        self.nodes = []
        # Read 256 nodes (1024 bytes)
        for i in range(0, 1024, 4):
            left, right = struct.unpack('<hh', data[i:i+4])
            self.nodes.append((left, right))

        print(f"Loaded Huffman tree: {len(self.nodes)} nodes")

    def decode(self, compressed_data, uncompressed_len, swap=False):
        """Decode Huffman-compressed data.

        Args:
            compressed_data: Compressed byte data
            uncompressed_len: Expected output length
            swap: If True, swap left/right interpretation (for testing)

        Returns:
            Decompressed bytes
        """
        out = []
        node_idx = 0  # Start at root node
        bit_ptr = 0

        while len(out) < uncompressed_len:
            if bit_ptr >= len(compressed_data) * 8:
                break

            # Read one bit (MSB first)
            byte_idx = bit_ptr // 8
            bit_idx = bit_ptr % 8
            bit = (compressed_data[byte_idx] >> (7 - bit_idx)) & 1
            bit_ptr += 1

            # Traverse tree
            left, right = self.nodes[node_idx]

            if swap:
                next_val = right if bit == 0 else left
            else:
                next_val = left if bit == 0 else right

            if next_val >= 0:
                # Leaf node - output decoded byte
                out.append(next_val)
                node_idx = 0  # Return to root
            else:
                # Internal node - continue traversal
                node_idx = -next_val

        return bytes(out)


def decode_all_messages(hdr_path, dbs_path, tree_path, max_messages=None):
    """Decode all messages from MSG.DBS using MSG.HDR index.

    Args:
        hdr_path: Path to MSG.HDR
        dbs_path: Path to MSG.DBS
        tree_path: Path to MISC.HDR (Huffman tree)
        max_messages: Maximum number of messages to decode (None = all)

    Returns:
        List of decoded message strings
    """
    # Load Huffman tree
    decoder = HuffmanDecoder(tree_path)

    # Load header (message offsets)
    with open(hdr_path, 'rb') as f:
        hdr_data = f.read()

    # Load message database
    with open(dbs_path, 'rb') as f:
        dbs_data = f.read()

    # Parse header as array of 16-bit words
    words = []
    for i in range(0, len(hdr_data), 2):
        word = struct.unpack('<H', hdr_data[i:i+2])[0]
        words.append(word)

    print(f"\nHeader: {len(words)} words")
    print(f"Database: {len(dbs_data)} bytes")

    # Decode messages
    messages = []
    num_to_decode = max_messages if max_messages else len(words) // 2

    for msg_idx in range(num_to_decode):
        i = msg_idx * 2
        if i + 1 >= len(words):
            break

        offset = words[i]
        value2 = words[i + 1]

        # Interpret value2 as end offset
        if value2 <= offset or offset >= len(dbs_data):
            print(f"Message {msg_idx}: Invalid offsets ({offset}, {value2})")
            continue

        length = value2 - offset
        if offset + length > len(dbs_data):
            print(f"Message {msg_idx}: Length exceeds database size")
            continue

        # Extract message chunk
        chunk = dbs_data[offset:offset + length]

        if len(chunk) < 2:
            print(f"Message {msg_idx}: Chunk too small ({len(chunk)} bytes)")
            continue

        # Parse message header
        ulen = chunk[0]  # Uncompressed length
        clen = chunk[1]  # Compressed length

        if 2 + clen > len(chunk):
            print(f"Message {msg_idx}: Compressed length mismatch "
                  f"(expected {clen}, have {len(chunk) - 2})")
            continue

        # Extract compressed data
        compressed = chunk[2:2 + clen]

        # Decode
        try:
            decoded = decoder.decode(compressed, ulen, swap=False)
            text = decoded.decode('ascii', errors='replace')
            messages.append(text)

            print(f"\nMessage {msg_idx} (offset={offset}, ulen={ulen}, clen={clen}):")
            print(f"  {text}")

        except Exception as e:
            print(f"Message {msg_idx}: Decode error: {e}")

    return messages


def test_simple():
    """Simple test of first few messages."""
    decoder = HuffmanDecoder('gamedata/MISC.HDR')

    with open('gamedata/MSG.DBS', 'rb') as f:
        data = f.read(1024)

    print("\n" + "=" * 80)
    print("SIMPLE TEST - First messages from MSG.DBS")
    print("=" * 80)

    for swap in [False, True]:
        print(f"\nTesting with swap={swap}:")
        i = 0

        for entries in range(5):
            if i + 2 > len(data):
                break

            ulen = data[i]
            clen = data[i + 1]

            if i + 2 + clen > len(data):
                print(f"  Entry {entries}: Not enough data")
                break

            msg_data = data[i + 2:i + 2 + clen]
            decoded = decoder.decode(msg_data, ulen, swap=swap)

            text = decoded.decode('ascii', errors='replace')
            print(f"  Entry {entries}: {text}")

            i += 2 + clen


def main():
    """Main function."""
    base_dir = Path("gamedata")

    # Test simple decoding first
    test_simple()

    # Then decode using header file
    print("\n" + "=" * 80)
    print("DECODING ALL MESSAGES USING MSG.HDR")
    print("=" * 80)

    messages = decode_all_messages(
        hdr_path=base_dir / "MSG.HDR",
        dbs_path=base_dir / "MSG.DBS",
        tree_path=base_dir / "MISC.HDR",
        max_messages=50  # Decode first 50 messages
    )

    print(f"\n\nSuccessfully decoded {len(messages)} messages")


if __name__ == "__main__":
    main()
