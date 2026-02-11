#!/usr/bin/env python3
"""
Complete MSG.DBS decoder for Wizardry 6.

Format discovered:
1. MSG.DBS contains sequentially-stored Huffman-compressed messages
2. Decode ALL messages into one large uncompressed buffer
3. MSG.HDR contains triplets: (message_id, offset, length)
   - offset: position in uncompressed buffer
   - length: number of bytes to read
"""

import struct
import sys
from huffman_decoder import HuffmanDecoder


def decode_complete_buffer():
    """Decode all MSG.DBS messages into banks.

    MSG.DBS contains multiple message banks separated by zero-length entries.
    Each bank's messages are decoded and concatenated.

    Returns:
        tuple: (all_banks_concatenated, list_of_individual_banks)
    """
    decoder = HuffmanDecoder('gamedata/MISC.HDR')

    with open('gamedata/MSG.DBS', 'rb') as f:
        data = f.read()

    print(f"Decoding MSG.DBS ({len(data)} bytes)...")

    banks = []
    current_bank = bytearray()
    i = 0
    msg_count = 0
    bank_num = 0
    total_messages = 0

    while i < len(data) - 1:
        ulen = data[i]
        clen = data[i+1]

        # Zero ulen indicates bank separator
        if ulen == 0:
            if len(current_bank) > 0:
                banks.append(bytes(current_bank))
                print(f"  Bank {bank_num}: {len(current_bank)} bytes from {msg_count} messages")
                current_bank = bytearray()
                bank_num += 1
                total_messages += msg_count
                msg_count = 0
            i += 1
            continue

        if clen == 0:
            i += 1
            continue

        if i + 2 + clen > len(data):
            break

        msg_data = data[i+2:i+2+clen]

        try:
            decoded = decoder.decode(msg_data, ulen)
            current_bank.extend(decoded)
            msg_count += 1
            i += 2 + clen
        except Exception as e:
            # Try to continue past errors
            i += 1

    # Add final bank
    if len(current_bank) > 0:
        banks.append(bytes(current_bank))
        print(f"  Bank {bank_num}: {len(current_bank)} bytes from {msg_count} messages")
        total_messages += msg_count

    print(f"\nDecoded {len(banks)} banks, {total_messages} total messages")

    # Concatenate all banks into one buffer
    complete_buffer = b''.join(banks)
    print(f"Total uncompressed size: {len(complete_buffer)} bytes")

    return complete_buffer, banks


def parse_msg_header():
    """Parse MSG.HDR into (message_id, offset, length) triplets.

    Format:
        Word[0]: Total uncompressed buffer size
        Word[1..]: Triplets of (message_id, offset, length)
    """
    with open('gamedata/MSG.HDR', 'rb') as f:
        hdr_data = f.read()

    # Parse as 16-bit little-endian words
    words = []
    for i in range(0, len(hdr_data), 2):
        word = struct.unpack('<H', hdr_data[i:i+2])[0]
        words.append(word)

    print(f"\nParsing MSG.HDR ({len(words)} words)...")

    # First word is total buffer size
    buffer_size = words[0]
    print(f"Expected uncompressed buffer size: {buffer_size} bytes")

    # Parse triplets starting at word[1]
    entries = []
    i = 1

    while i + 2 < len(words):
        msg_id = words[i]
        offset = words[i + 1]
        length = words[i + 2]

        # Stop if we hit padding (zeros)
        if msg_id == 0 and offset == 0 and length == 0:
            break

        entries.append((msg_id, offset, length))
        i += 3

    print(f"Parsed {len(entries)} message entries")

    return entries, buffer_size


def extract_all_messages(buffer, entries):
    """Extract all messages from buffer using header entries."""
    messages = {}

    for msg_id, offset, length in entries:
        if offset + length <= len(buffer):
            raw_bytes = buffer[offset:offset + length]
            try:
                text = raw_bytes.decode('ascii', errors='replace')
                messages[msg_id] = text
            except:
                messages[msg_id] = raw_bytes

    return messages


def main():
    """Main decoder function."""
    print("=" * 80)
    print("WIZARDRY 6 MSG.DBS / MSG.HDR DECODER")
    print("=" * 80)

    # Step 1: Decode complete uncompressed buffer (all banks)
    buffer, banks = decode_complete_buffer()

    # Step 2: Parse header
    entries, expected_buffer_size = parse_msg_header()

    # Note: expected_buffer_size (718) is just the first bank size
    print(f"Note: Header word[0] = {expected_buffer_size} (first bank size)")
    print(f"      Actual total buffer = {len(buffer)} bytes")

    # Step 3: Extract messages
    print(f"\nExtracting messages from complete buffer...")
    messages = extract_all_messages(buffer, entries)

    print(f"Successfully extracted {len(messages)} messages")

    # Show sample messages
    print(f"\n" + "=" * 80)
    print(f"SAMPLE MESSAGES:")
    print(f"=" * 80)

    for msg_id in sorted(messages.keys())[:50]:
        text = messages[msg_id]
        if isinstance(text, str):
            display = text[:70].replace('\n', '\\n').replace('\r', '')
            print(f"ID {msg_id:4d}: {display}")
        else:
            print(f"ID {msg_id:4d}: [binary data, {len(text)} bytes]")

    # Save all messages
    with open('all_messages.txt', 'w', encoding='utf-8') as f:
        for msg_id in sorted(messages.keys()):
            text = messages[msg_id]
            f.write(f"=== Message ID {msg_id} ===\n")
            if isinstance(text, str):
                f.write(text)
            else:
                f.write(f"[Binary data: {text.hex()}]")
            f.write('\n\n')

    print(f"\n\nSaved all messages to all_messages.txt")

    # Interactive mode
    if len(sys.argv) > 1:
        try:
            msg_id = int(sys.argv[1])
            if msg_id in messages:
                print(f"\n\nMessage ID {msg_id}:")
                print(f"-" * 80)
                print(messages[msg_id])
            else:
                print(f"\nMessage ID {msg_id} not found")
        except ValueError:
            print(f"Invalid message ID: {sys.argv[1]}")


if __name__ == "__main__":
    main()
