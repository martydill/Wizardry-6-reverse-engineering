#!/usr/bin/env python3
"""
Analyze Wizardry 6 MSG.HDR and MSG.DBS files.
These files likely contain game text messages, possibly Huffman encoded.

MSG.HDR: Header/index file with pointers
MSG.DBS: Message database (possibly compressed)
"""

import struct
import os
from pathlib import Path


def analyze_msg_hdr(filepath):
    """Analyze the MSG.HDR file structure."""
    print("=" * 80)
    print("ANALYZING MSG.HDR")
    print("=" * 80)

    with open(filepath, 'rb') as f:
        data = f.read()

    file_size = len(data)
    print(f"File size: {file_size} bytes")

    # Try to parse as array of 16-bit words (little-endian)
    if file_size % 2 == 0:
        words = []
        for i in range(0, file_size, 2):
            word = struct.unpack('<H', data[i:i+2])[0]
            words.append(word)

        print(f"Number of 16-bit words: {len(words)}")
        print(f"\nFirst 32 words (as decimal):")
        for i in range(min(32, len(words))):
            if i % 8 == 0:
                print(f"  {i:4d}: ", end="")
            print(f"{words[i]:6d}", end=" ")
            if (i + 1) % 8 == 0:
                print()
        print()

        print(f"\nFirst 32 words (as hex):")
        for i in range(min(32, len(words))):
            if i % 8 == 0:
                print(f"  {i:4d}: ", end="")
            print(f"{words[i]:04X}", end=" ")
            if (i + 1) % 8 == 0:
                print()
        print()

        # Check if words form pairs (offset, length)
        if len(words) % 2 == 0:
            print(f"\nPossible message entries (offset, length pairs):")
            print(f"Number of possible entries: {len(words) // 2}")

            entries = []
            for i in range(0, min(40, len(words)), 2):
                offset = words[i]
                length_or_end = words[i + 1]
                entries.append((offset, length_or_end))
                print(f"  Entry {i//2:3d}: offset={offset:6d} (0x{offset:04X}), "
                      f"value2={length_or_end:6d} (0x{length_or_end:04X})")

            # Check if second value could be end offset
            print(f"\nChecking if pairs are (start_offset, end_offset):")
            for i in range(min(20, len(entries))):
                start, end = entries[i]
                if end >= start:
                    length = end - start
                    print(f"  Entry {i:3d}: offset={start:6d}, end={end:6d}, "
                          f"length={length:6d} bytes")
                else:
                    print(f"  Entry {i:3d}: offset={start:6d}, end={end:6d} "
                          f"(INVALID: end < start)")

        return words

    return None


def analyze_msg_dbs(filepath, max_bytes=1000):
    """Analyze the MSG.DBS file structure."""
    print("\n" + "=" * 80)
    print("ANALYZING MSG.DBS")
    print("=" * 80)

    with open(filepath, 'rb') as f:
        data = f.read()

    file_size = len(data)
    print(f"File size: {file_size} bytes")

    # Byte frequency analysis (for Huffman detection)
    byte_freq = {}
    for byte in data:
        byte_freq[byte] = byte_freq.get(byte, 0) + 1

    print(f"\nByte frequency analysis:")
    sorted_freq = sorted(byte_freq.items(), key=lambda x: x[1], reverse=True)
    print(f"  Unique bytes: {len(byte_freq)}/256")
    print(f"  Most common bytes:")
    for i, (byte, count) in enumerate(sorted_freq[:20]):
        pct = (count / file_size) * 100
        print(f"    0x{byte:02X} ({byte:3d}): {count:6d} times ({pct:5.2f}%)")

    # Look for patterns that might indicate Huffman tree or header
    print(f"\nFirst {min(max_bytes, file_size)} bytes (hex):")
    for i in range(0, min(max_bytes, file_size), 16):
        hex_str = ' '.join(f'{b:02X}' for b in data[i:i+16])
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"  {i:06X}: {hex_str:<48} {ascii_str}")

    # Check for potential text strings (might be uncompressed sections)
    print(f"\nSearching for ASCII text strings (length >= 10)...")
    in_string = False
    string_start = 0
    string_data = []

    for i, byte in enumerate(data):
        if 32 <= byte < 127 or byte in [9, 10, 13]:  # Printable + tab, LF, CR
            if not in_string:
                in_string = True
                string_start = i
            string_data.append(byte)
        else:
            if in_string and len(string_data) >= 10:
                text = bytes(string_data).decode('ascii', errors='ignore')
                print(f"  Offset {string_start:6d} (0x{string_start:04X}): {text[:60]}")
            in_string = False
            string_data = []

    return data


def check_huffman_encoding(data):
    """Check if data appears to be Huffman encoded."""
    print("\n" + "=" * 80)
    print("HUFFMAN ENCODING DETECTION")
    print("=" * 80)

    # Huffman encoded data typically has:
    # 1. A header with the tree structure
    # 2. High entropy (relatively uniform bit distribution)

    # Check first few bytes for potential Huffman tree header
    print(f"First 64 bytes (potential Huffman header):")
    for i in range(min(64, len(data))):
        if i % 16 == 0:
            print(f"  {i:04X}: ", end="")
        print(f"{data[i]:02X} ", end="")
        if (i + 1) % 16 == 0:
            print()
    print()

    # Try to identify tree structure
    # Common formats:
    # - Canonical Huffman: code lengths array
    # - Explicit tree: nodes with left/right pointers
    # - Frequency table: byte frequencies followed by encoded data

    print("\nTrying to detect Huffman tree format...")

    # Check if starts with a count/size field
    if len(data) >= 4:
        size_le16 = struct.unpack('<H', data[0:2])[0]
        size_be16 = struct.unpack('>H', data[0:2])[0]
        size_le32 = struct.unpack('<I', data[0:4])[0]
        size_be32 = struct.unpack('>I', data[0:4])[0]

        print(f"  Potential size fields:")
        print(f"    LE16 at offset 0: {size_le16} (0x{size_le16:04X})")
        print(f"    BE16 at offset 0: {size_be16} (0x{size_be16:04X})")
        print(f"    LE32 at offset 0: {size_le32} (0x{size_le32:08X})")
        print(f"    BE32 at offset 0: {size_be32} (0x{size_be32:08X})")


def correlate_hdr_and_dbs(hdr_words, dbs_data):
    """Try to correlate header entries with database content."""
    print("\n" + "=" * 80)
    print("CORRELATING MSG.HDR AND MSG.DBS")
    print("=" * 80)

    if not hdr_words or len(hdr_words) < 2:
        print("Not enough header data to correlate")
        return

    # Assume pairs of (offset, end_offset) or (offset, length)
    print("\nAttempting to extract messages using header offsets...")

    for i in range(0, min(20, len(hdr_words)), 2):
        offset = hdr_words[i]
        value2 = hdr_words[i + 1]

        # Try both interpretations
        # Option 1: value2 is end offset
        if value2 > offset and value2 <= len(dbs_data):
            length = value2 - offset
            print(f"\nEntry {i//2} (offset={offset}, end={value2}, length={length}):")

            if offset + length <= len(dbs_data):
                chunk = dbs_data[offset:offset + length]

                # Show hex
                hex_preview = ' '.join(f'{b:02X}' for b in chunk[:32])
                print(f"  Hex: {hex_preview}{'...' if len(chunk) > 32 else ''}")

                # Try to decode as ASCII
                ascii_text = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk[:64])
                print(f"  ASCII: {ascii_text}")

                # Check if looks like compressed data
                unique_bytes = len(set(chunk))
                print(f"  Stats: {len(chunk)} bytes, {unique_bytes} unique values")


def main():
    """Main analysis function."""
    base_dir = Path("C:/Users/marty/Documents/code/bane/gamedata")

    hdr_path = base_dir / "MSG.HDR"
    dbs_path = base_dir / "MSG.DBS"

    if not hdr_path.exists():
        print(f"Error: {hdr_path} not found")
        return

    if not dbs_path.exists():
        print(f"Error: {dbs_path} not found")
        return

    # Analyze header file
    hdr_words = analyze_msg_hdr(hdr_path)

    # Analyze database file
    dbs_data = analyze_msg_dbs(dbs_path, max_bytes=256)

    # Check for Huffman encoding
    check_huffman_encoding(dbs_data)

    # Try to correlate the two files
    if hdr_words:
        correlate_hdr_and_dbs(hdr_words, dbs_data)


if __name__ == '__main__':
    main()
