from bane.data.message_parser import MessageParser
from pathlib import Path

def dump():
    p = MessageParser('gamedata/MISC.HDR')
    msgs = p.load('gamedata/MSG.DBS', 'gamedata/MSG.HDR')
    
    ids = sorted(msgs.keys())
    print(f"Total IDs: {len(ids)}")
    for mid in ids[:20]:
        print(f"ID {mid}: {msgs[mid]}")

if __name__ == "__main__":
    dump()
