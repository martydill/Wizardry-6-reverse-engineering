#!/usr/bin/env python3
"""
Parse MSG.HDR to understand the index structure and decode all messages.
"""

import struct
import sys
from pathlib import Path
from huffman_decoder import HuffmanDecoder


def parse_msg_sequential(dbs_path, count=20):
    """Parse messages sequentially from MSG.DBS."""
    with open(dbs_path, 'rb') as f:
        data = f.read()

    i = 0
    entries = 0
    while i < len(data) - 1 and entries < count:
        ulen = data[i]
        clen = data[i+1]
        if i + 2 + clen > len(data):
            break
        print(f"Offset {i:5d}: Uncomp={ulen:3d}, Comp={clen:3d}, "
              f"Data={data[i+2:i+2+clen].hex()[:60]}")
        i += 2 + clen
        entries += 1


def analyze_header_structure():
    """Analyze MSG.HDR structure to find the correct interpretation."""
    with open('gamedata/MSG.HDR', 'rb') as f:
        hdr_data = f.read()

    with open('gamedata/MSG.DBS', 'rb') as f:
        dbs_data = f.read()

    # Parse as 16-bit words
    words = []
    for i in range(0, len(hdr_data), 2):
        word = struct.unpack('<H', hdr_data[i:i+2])[0]
        words.append(word)

    print(f"=" * 80)
    print(f"MSG.HDR STRUCTURE ANALYSIS")
    print(f"=" * 80)
    print(f"Header size: {len(hdr_data)} bytes")
    print(f"Number of words: {len(words)}")
    print(f"Database size: {len(dbs_data)} bytes")

    # Load decoder
    decoder = HuffmanDecoder('gamedata/MISC.HDR')

    # Read all messages sequentially
    print(f"\n\nReading messages sequentially from MSG.DBS:")
    print(f"-" * 80)

    offset = 0
    msg_num = 0
    sequential_offsets = []

    while offset < len(dbs_data) and msg_num < 1000:
        if offset + 2 > len(dbs_data):
            break

        ulen = dbs_data[offset]
        clen = dbs_data[offset + 1]

        # Sanity check
        if ulen == 0 or clen == 0 or clen > 255 or offset + 2 + clen > len(dbs_data):
            break

        sequential_offsets.append(offset)

        # Decode
        compressed = dbs_data[offset + 2:offset + 2 + clen]
        try:
            decoded = decoder.decode(compressed, ulen, swap=False)
            text = decoded.decode('ascii', errors='replace')

            # Clean up for display
            display_text = text[:60].replace('\n', '\\n').replace('\r', '')

            if msg_num < 50:  # Show first 50
                print(f"  {msg_num:4d} @ {offset:5d}: ulen={ulen:3d}, "
                      f"clen={clen:3d} -> \"{display_text}\"")

            # Move to next message
            offset += 2 + clen
            msg_num += 1

        except Exception as e:
            print(f"  {msg_num} at offset {offset}: Decode error: {e}")
            break

    print(f"\nTotal messages decoded: {msg_num}")

    # Now compare with header entries
    print(f"\n\n" + "=" * 80)
    print(f"COMPARING SEQUENTIAL OFFSETS WITH MSG.HDR ENTRIES:")
    print(f"=" * 80)

    hdr_matches = []

    for word_idx, word_val in enumerate(words):
        if word_val in sequential_offsets:
            seq_idx = sequential_offsets.index(word_val)
            hdr_matches.append((word_idx, word_val, seq_idx))

    print(f"Found {len(hdr_matches)} offset matches in header:")
    for word_idx, offset, seq_idx in hdr_matches[:50]:
        print(f"  Header word[{word_idx:4d}] = {offset:5d} = Sequential msg {seq_idx:4d}")

    # Check if there's a pattern
    if len(hdr_matches) > 1:
        print(f"\n\nPattern analysis:")
        intervals = []
        for i in range(1, min(20, len(hdr_matches))):
            word_diff = hdr_matches[i][0] - hdr_matches[i-1][0]
            seq_diff = hdr_matches[i][2] - hdr_matches[i-1][2]
            intervals.append((word_diff, seq_diff))
            print(f"  Match {i}: word_delta={word_diff}, seq_delta={seq_diff}")


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == 'sequential':
        parse_msg_sequential('gamedata/MSG.DBS', count=50)
    else:
        analyze_header_structure()


if __name__ == "__main__":
    main()
