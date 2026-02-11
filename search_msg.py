from bane.data.message_parser import MessageParser
from pathlib import Path

def search_gate():
    p = MessageParser('gamedata/MISC.HDR')
    p._decompress_dbs(Path('gamedata/MSG.DBS'))
    p._parse_hdr(Path('gamedata/MSG.HDR'))
    
    # Iterate through all messages
    for msg_id, entry in sorted(p.messages.items()):
        raw = p._buffer[entry.offset:entry.offset+entry.length].decode('ascii', errors='replace')
        cleaned = raw.replace('E', ' ')
        if "gate" in cleaned.lower():
            print(f"ID {msg_id}: {raw}")

if __name__ == "__main__":
    search_gate()
