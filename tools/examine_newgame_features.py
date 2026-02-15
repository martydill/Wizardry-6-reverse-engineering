#!/usr/bin/env python3
"""
Examine all fountains and sconces in NEWGAME.DBS to find map 10 features.
"""

from pathlib import Path

filepath = Path("gamedata/NEWGAME.DBS")

with open(filepath, 'rb') as f:
    data = f.read()

cells = []
for i in range(len(data) // 20):
    offset = i * 20
    if offset + 20 <= len(data):
        cells.append(data[offset:offset+20])

print('='*80)
print('ALL FEATURES IN NEWGAME.DBS')
print('='*80)
print()

# Find all fountains
print('FOUNTAINS (byte 18 = 0xA0):')
print('-'*80)

fountain_cells = []
for idx, cell in enumerate(cells):
    if cell[18] == 0xA0:
        fountain_cells.append(idx)

for idx in fountain_cells:
    cell = cells[idx]
    print(f'Cell {idx:4d}:')
    print(f'  Even bytes: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')
    print(f'  Odd bytes:  {" ".join(f"{cell[i]:02X}" for i in range(1, 20, 2))}')

    # Check if it also has other markers
    if cell[0] != 0:
        print(f'  >>> Also has byte 0 = 0x{cell[0]:02X}')
    print()

print('='*80)
print('SCONCES (byte 0 = 0xA0):')
print('-'*80)

sconce_cells = []
for idx, cell in enumerate(cells):
    if cell[0] == 0xA0:
        sconce_cells.append(idx)

for idx in sconce_cells:
    cell = cells[idx]
    print(f'Cell {idx:4d}:')
    print(f'  Even bytes: {" ".join(f"{cell[i]:02X}" for i in range(0, 20, 2))}')
    print(f'  Odd bytes:  {" ".join(f"{cell[i]:02X}" for i in range(1, 20, 2))}')

    # Check if it also has fountain marker
    if cell[18] != 0:
        print(f'  >>> Also has byte 18 = 0x{cell[18]:02X}')
    print()

print('='*80)
print('CELLS WITH BOTH MARKERS:')
print('-'*80)

both = []
for idx, cell in enumerate(cells):
    if cell[0] == 0xA0 and cell[18] == 0xA0:
        both.append(idx)
        print(f'Cell {idx:4d} has BOTH byte 0=0xA0 AND byte 18=0xA0!')

if not both:
    print('(none found)')

print()
print('='*80)
print('SUMMARY:')
print(f'  Fountains: {len(fountain_cells)} cells')
print(f'  Sconces: {len(sconce_cells)} cells')
print(f'  Both: {len(both)} cells')
print('='*80)
print()
print('Expected for map 10: 4 fountains, 3 sconces, 1 secret button')
print('Secret button should have been a sconce but was changed.')
