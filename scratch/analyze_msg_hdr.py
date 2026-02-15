import struct

def analyze_hdr(path):
    with open(path, 'rb') as f:
        count_bytes = f.read(2)
        count = struct.unpack('<H', count_bytes)[0]
        print(f"Entry count: {count}")
        
        max_off = 0
        max_len = 0
        entries = []
        for i in range(count):
            id_val, off, length = struct.unpack('<HHH', f.read(6))
            entries.append((id_val, off, length))
            max_off = max(max_off, off)
            max_len = max(max_len, length)
            
        print(f"Max offset: {max_off}")
        print(f"Max length: {max_len}")
        
        # Print first 20 entries
        for i in range(min(20, len(entries))):
            print(f"ID {entries[i][0]:4d}: Off {entries[i][1]:5d}, Len {entries[i][2]:5d}")

if __name__ == "__main__":
    analyze_hdr('gamedata/MSG.HDR')
