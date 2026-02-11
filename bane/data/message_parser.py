from __future__ import annotations
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from bane.data.huffman import HuffmanDecoder
from bane.data.binary_reader import BinaryReader

@dataclass
class MessageEntry:
    id: int
    offset: int
    length: int
    text: str = ""

class MessageParser:
    """Parses Wizardry 6 message databases (MSG.DBS / MSG.HDR)."""

    def __init__(self, tree_path: Path | str):
        self.decoder = HuffmanDecoder.from_file(tree_path)
        self.messages: Dict[int, MessageEntry] = {}
        self._buffer: bytes = b""

    def load(self, dbs_path: Path | str, hdr_path: Path | str) -> Dict[int, str]:
        """Load and decompress all messages from the database.
        
        Args:
            dbs_path: Path to the compressed data file (MSG.DBS).
            hdr_path: Path to the message index file (MSG.HDR).
            
        Returns:
            A dictionary mapping message IDs to their decoded strings.
        """
        self._decompress_dbs(Path(dbs_path))
        self._parse_hdr(Path(hdr_path))
        
        result = {}
        for msg_id, entry in self.messages.items():
            if entry.offset + entry.length <= len(self._buffer):
                raw_text = self._buffer[entry.offset : entry.offset + entry.length]
                # Clean up leading control characters or common artifacts
                text = raw_text.decode('ascii', errors='replace')
                if text.startswith('\x05'):
                    text = text[1:]
                entry.text = text
                result[msg_id] = entry.text
                
        return result

    def _decompress_dbs(self, path: Path):
        """Decompress the entire DBS file into a single uncompressed buffer."""
        data = path.read_bytes()
        out = bytearray()
        
        i = 0
        while i < len(data) - 1:
            ulen = data[i]
            clen = data[i+1]
            if i + 2 + clen > len(data):
                break
                
            block_data = data[i+2 : i+2+clen]
            decoded = self.decoder.decode(block_data, ulen)
            out.extend(decoded)
            
            i += 2 + clen
            
        self._buffer = bytes(out)

    def _parse_hdr(self, path: Path):
        """Parse the HDR index file to locate messages within the buffer."""
        reader = BinaryReader.from_file(path)
        count = reader.read_u16()
        
        for _ in range(count):
            msg_id = reader.read_u16()
            offset = reader.read_u16()
            length = reader.read_u16()
            
            self.messages[msg_id] = MessageEntry(id=msg_id, offset=offset, length=length)

def load_messages(
    gamedata_dir: str | Path, 
    prefix: str = "MSG", 
    tree_file: str = "MISC.HDR"
) -> Dict[int, str]:
    """Helper to load a message set from the gamedata directory."""
    base_path = Path(gamedata_dir)
    parser = MessageParser(base_path / tree_file)
    return parser.load(
        base_path / f"{prefix}.DBS",
        base_path / f"{prefix}.HDR"
    )
