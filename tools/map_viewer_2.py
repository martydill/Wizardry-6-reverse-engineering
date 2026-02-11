import struct
import os
import sys

class BinaryStream:
    """Helper class to handle little-endian binary reading."""
    def __init__(self, filename):
        self.filename = filename
        self.f = open(filename, "rb")

    def seek(self, offset):
        self.f.seek(offset)

    def tell(self):
        return self.f.tell()

    def read_byte(self):
        return struct.unpack("<B", self.f.read(1))[0]

    def read_uint16(self):
        return struct.unpack("<H", self.f.read(2))[0]

    def read_uint32(self):
        return struct.unpack("<I", self.f.read(4))[0]
    
    def read_bytes(self, count):
        return self.f.read(count)

    def close(self):
        self.f.close()

class Wizardry6ScenarioParser:
    """Parses SCENARIO.DBS: The world database containing maps and scripts."""
    
    # Wall Bitmasks for Wiz6
    WALL_NORTH = 0x01
    WALL_EAST  = 0x02
    WALL_SOUTH = 0x04
    WALL_WEST  = 0x08
    
    def __init__(self, filepath):
        self.stream = BinaryStream(filepath)
        self.levels = []

    def parse(self):
        print(f"[*] Parsing {self.stream.filename}...")
        
        # 1. Parse the Master Header
        # The file starts with a count of levels (uint16), followed by offsets (uint32).
        self.stream.seek(0)
        num_levels = self.stream.read_uint16()
        print(f"[*] Found {num_levels} dungeon levels in header.")

        level_offsets = []
        for i in range(num_levels):
            offset = self.stream.read_uint32()
            level_offsets.append(offset)

        # 2. Parse Each Level Block
        for idx, offset in enumerate(level_offsets):
            # Validation: Offset must be within file bounds
            if offset == 0 or offset >= os.path.getsize(self.stream.filename):
                continue

            self.stream.seek(offset)
            
            # Local Level Header Structure (Reconstructed)
            # 0x00: Map Width  (2 bytes)
            # 0x02: Map Height (2 bytes)
            # 0x04: Ptr to Wall/Floor Data
            # 0x08: Ptr to Object Data
            # 0x0C: Ptr to Monster Data
            # 0x10: Ptr to Event/Incident Data
            
            map_w = self.stream.read_uint16()
            map_h = self.stream.read_uint16()
            
            ptr_walls = self.stream.read_uint32()
            ptr_objects = self.stream.read_uint32()
            ptr_monsters = self.stream.read_uint32()
            ptr_events = self.stream.read_uint32()

            level_data = {
                "id": idx + 1,
                "dims": (map_w, map_h),
                "offsets": {
                    "walls": ptr_walls,
                    "events": ptr_events
                },
                "grid": []
            }
            
            # 3. Extract Map Geometry
            # The pointers are usually relative to the file start, but sometimes logic varies.
            # We assume absolute file offsets based on standard Sir-Tech format.
            if ptr_walls > 0:
                self.stream.seek(ptr_walls)
                
                # Reading the grid
                # Data is stored row by row. Each cell structure varies, 
                # but usually starts with a byte defining walls.
                grid = []
                for y in range(map_h):
                    row = []
                    for x in range(map_w):
                        # Read cell data. In Wiz6, cells are multi-byte structures.
                        # We read the first byte for walls.
                        # Note: We skip bytes to advance to the next cell.
                        # Assuming a standard cell size of 4 bytes for this extraction.
                        # (Adjust CELL_SIZE if alignment is off for your version)
                        CELL_SIZE = 4 
                        
                        cell_raw = self.stream.read_bytes(CELL_SIZE)
                        if len(cell_raw) < CELL_SIZE:
                            break
                        wall_byte = cell_raw[0] # First byte usually holds wall bitmask
                        
                        # Extract Incident ID if present (often in 2nd or 3rd byte)
                        event_id = cell_raw[1] 
                        
                        cell_info = {
                            "walls": self._decode_walls(wall_byte),
                            "event": event_id if event_id!= 0 else None
                        }
                        row.append(cell_info)
                    grid.append(row)
                level_data["grid"] = grid

            self.levels.append(level_data)
            print(f"    - Level {idx+1}: {map_w}x{map_h} loaded.")

        return self.levels

    def _decode_walls(self, byte_val):
        walls = []
        if byte_val & self.WALL_NORTH: walls.append("N")
        if byte_val & self.WALL_SOUTH: walls.append("S")
        if byte_val & self.WALL_EAST:  walls.append("E")
        if byte_val & self.WALL_WEST:  walls.append("W")
        return walls

    def close(self):
        self.stream.close()

class Wiz6BinParser:
    """Parses WIZ6.BIN: Static game data (Items, Races, Classes)."""
    
    # Heuristic offset for Item Table (Version 3.x)
    # If output looks garbage, this offset needs adjustment.
    ITEM_TABLE_OFFSET = 14780 
    RECORD_SIZE = 40 # Standard item record size
    
    def __init__(self, filepath):
        self.stream = BinaryStream(filepath)

    def extract_items(self, limit=50):
        print(f"\n[*] Parsing {self.stream.filename} (Item Table)...")
        self.stream.seek(self.ITEM_TABLE_OFFSET)
        
        items = []
        for i in range(limit):
            # Item Record Structure (Partial)
            # 0x00: Name Offset (uint16) - Ptr to string table
            # 0x02: Type (byte)
            # 0x03: Unknown
            # 0x04: Equip Bitmask (uint16)
            #...
            
            try:
                rec_start = self.stream.tell()
                name_ptr = self.stream.read_uint16()
                item_type = self.stream.read_byte()
                self.stream.read_byte() # skip
                equip_flags = self.stream.read_uint16()
                
                # Jump to next record
                self.stream.seek(rec_start + self.RECORD_SIZE)
                
                items.append({
                    "id": i,
                    "name_offset": name_ptr,
                    "type_id": item_type,
                    "equip_flags": f"{equip_flags:016b}"
                })
            except:
                break
                
        return items

def render_ascii_map(level_data):
    """Renders a visual representation of the map grid."""
    print(f"\n--- MAP RENDER: Level {level_data['id']} ---")
    grid = level_data["grid"]
    if not grid:
        print("(No grid data extracted)")
        return

    # Top Border
    if grid and grid[0]:
        print(" " + " _" * len(grid[0]))

    for row in grid:
        line_str = "|"
        for cell in row:
            # Floor logic: if 'S' (South) wall is present, draw underscore
            if "S" in cell["walls"]:
                char = "_"
            else:
                char = " "
            
            # Event logic: If there is an event, mark it
            if cell["event"]:
                char = "E"
            
            # East wall logic
            right_border = "|" if "E" in cell["walls"] else " "
            line_str += char + right_border
        print(line_str)

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    dbs_path = "SCENARIO.DBS"
    bin_path = "WIZ6.BIN"

    # 1. Extract Maps
    if os.path.exists(dbs_path):
        parser = Wizardry6ScenarioParser(dbs_path)
        levels = parser.parse()
        
        # Render the first map as a test
        if levels and levels[0]['grid']:
            render_ascii_map(levels[0])
            
            # Print analysis of the first map's events
            print(f"\n[!] Event Analysis for Level 1:")
            event_count = 0
            for row in levels[0]['grid']:
                for cell in row:
                    if cell['event']:
                        event_count += 1
            print(f"    Found {event_count} tiles with interaction scripts (Incidents).")
        elif levels:
             print("\n[!] No grid data found in the first level.")
            
        parser.close()
    else:
        print(f"[!] {dbs_path} not found.")

    # 2. Extract Items
    if os.path.exists(bin_path):
        bin_parser = Wiz6BinParser(bin_path)
        items = bin_parser.extract_items(10)
        print("\n[*] First 10 Detected Item Records (Raw Data):")
        for it in items:
            print(it)
        print("[*] Note: 'name_offset' points to MSG6.DBS string table.")
    else:
        print(f"[!] {bin_path} not found.")