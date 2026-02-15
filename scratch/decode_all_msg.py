import struct
from huffman_decoder import HuffmanDecoder

def decode_all():
    decoder = HuffmanDecoder('gamedata/MISC.HDR')
    with open('gamedata/MSG.DBS', 'rb') as f:
        data = f.read()
    
    with open('decoded_msg.txt', 'w', encoding='utf-8') as out:
        i = 0
        entries = 0
        while i < len(data) - 1:
            ulen = data[i]
            clen = data[i+1]
            if i + 2 + clen > len(data):
                break
            msg_data = data[i+2 : i+2+clen]
            decoded = decoder.decode(msg_data, ulen)
            
            text = ""
            for b in decoded:
                if 32 <= b <= 126:
                    text += chr(b)
                else:
                    text += f"\\x{b:02x}"
            out.write(f"Entry {entries:4d} (Off {i:5d}): {text}\n")
            
            i += 2 + clen
            entries += 1

if __name__ == "__main__":
    decode_all()