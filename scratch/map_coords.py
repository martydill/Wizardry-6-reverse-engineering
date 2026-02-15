
import sys

def map_offset_to_16x16(target_offset, base_offset, bytes_per_element):
    relative = target_offset - base_offset
    index = relative // bytes_per_element
    
    # Assume column-major 16x16
    col = index // 16
    row = index % 16
    
    return col, row

base = 0x7D22 # Start of features
target = 0x7E54
bpe = 1 # Assume 1 byte per cell for this new table?

print(f"If 1 byte per cell starting at {base:04X}:")
col, row = map_offset_to_16x16(target, base, 1)
print(f"  Target {target:04X} -> Cell index {target-base}, Position ({col}, {row})")

base2 = 0x7DA2 # Start of something after 128-byte feature table
print(f"If 1 byte per cell starting at {base2:04X}:")
col, row = map_offset_to_16x16(target, base2, 1)
print(f"  Target {target:04X} -> Cell index {target-base2}, Position ({col}, {row})")

base3 = 0x7E22 # Start of something after 256 bytes of tables
print(f"If 1 byte per cell starting at {base3:04X}:")
col, row = map_offset_to_16x16(target, base3, 1)
print(f"  Target {target:04X} -> Cell index {target-base3}, Position ({col}, {row})")
