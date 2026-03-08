from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

logger = logging.getLogger(__name__)

MAP_HEADER_SIZE = 0x019E
MAP_RECORD_SIZE = 0x0C0E
MAP_STREAM_WINDOW = 0x01B0

@dataclass
class MazeCell:
    block: int
    row: int
    col: int
    wx: int
    wy: int
    wall_a: int  # North/South walls
    wall_b: int  # East/West walls
    ch4: int     # Channel 4 (classifier)
    ch2: int     # Channel 2 (classifier)

class Wiz6Maze:
    def __init__(self, dbs_path: Path):
        self.data = dbs_path.read_bytes()
        self.origins: list[tuple[int, int]] = []
        self.maps: dict[int, dict[tuple[int, int], MazeCell]] = {}

    def load_map(self, map_id: int):
        base = MAP_HEADER_SIZE + map_id * MAP_RECORD_SIZE
        
        # Decode origins (12 blocks)
        xs = list(self.data[base + 0x1E0 : base + 0x1E0 + 12])
        ys = list(self.data[base + 0x1EC : base + 0x1EC + 12])
        origins = list(zip(xs, ys))
        self.origins = origins

        # Decode wall planes
        a_start = base + 0x60
        b_start = base + 0x120
        c4_start = base + 0x1F8
        c2_start = base + 0x378

        def get_2bit(start: int, idx: int) -> int:
            b = self.data[start + (idx // 4)]
            shift = (idx % 4) * 2
            return (b >> shift) & 0x03

        def get_4bit(start: int, idx: int) -> int:
            b = self.data[start + (idx // 2)]
            if idx & 1:
                return (b >> 4) & 0x0F
            return b & 0x0F

        a_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
        b_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
        c4_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]
        c2_vals = [[[0] * 8 for _ in range(8)] for _ in range(12)]

        cells = {}
        for b, (ox, oy) in enumerate(origins):
            if ox == 0 and oy == 0:
                continue
            for r in range(8):
                for c in range(8):
                    idx = (b << 6) + (r << 3) + c
                    a_v = get_2bit(a_start, idx)
                    b_v = get_2bit(b_start, idx)
                    c4_v = get_4bit(c4_start, idx)
                    c2_v = get_2bit(c2_start, idx)
                    
                    a_vals[b][r][c] = a_v
                    b_vals[b][r][c] = b_v
                    c4_vals[b][r][c] = c4_v
                    c2_vals[b][r][c] = c2_v
                    
                    wx, wy = ox + c, oy + r
                    cells[(wx, wy)] = MazeCell(
                        block=b, row=r, col=c, wx=wx, wy=wy,
                        wall_a=a_v, wall_b=b_v, ch4=c4_v, ch2=c2_v
                    )
        
        self.edges = self._collect_world_edge_values(a_vals, b_vals, origins, map_id)
        self.maps[map_id] = cells
        return cells

    def _collect_world_edge_values(self, a_vals, b_vals, origins, map_id):
        out = {}
        for b, (ox, oy) in enumerate(origins):
            if ox == 0 and oy == 0:
                continue
            for y in range(9):
                for x in range(8):
                    if y == 0:
                        val = self._wall_mode_value(a_vals, b_vals, origins, map_id, b, 0, x, 2)
                    else:
                        val = self._wall_mode_value(a_vals, b_vals, origins, map_id, b, y - 1, x, 0)
                    if val:
                        out[("h", ox + x, oy + y)] = val
            for y in range(8):
                for x in range(9):
                    if x == 0:
                        val = self._wall_mode_value(a_vals, b_vals, origins, map_id, b, y, 0, 3)
                    else:
                        val = self._wall_mode_value(a_vals, b_vals, origins, map_id, b, y, x - 1, 1)
                    if val:
                        out[("v", ox + x, oy + y)] = val
        return out

    def _wall_mode_value(self, a_vals, b_vals, origins, map_id, block, row, col, mode):
        if mode == 0:
            return a_vals[block][row][col]
        if mode == 1:
            return b_vals[block][row][col]
        ox, oy = origins[block]
        wx = ox + col
        wy = oy + row
        if mode == 2:
            res = self._resolve_block(origins, wx, wy - 1, prefer_block=block)
        else:
            res = self._resolve_block(origins, wx - 1, wy, prefer_block=block)
        if res is None:
            return 0 if map_id in (0x0A, 0x0C) else 2
        rb, rr, rc = res
        return a_vals[rb][rr][rc] if mode == 2 else b_vals[rb][rr][rc]

    def _resolve_block(self, origins, wx, wy, prefer_block=None):
        if prefer_block is not None:
            ox, oy = origins[prefer_block]
            if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
                return prefer_block, wy - oy, wx - ox
        for b, (ox, oy) in enumerate(origins):
            if ox <= wx <= ox + 7 and oy <= wy <= oy + 7:
                return b, wy - oy, wx - ox
        return None

    def get_cell(self, map_id: int, wx: int, wy: int) -> MazeCell | None:
        m = self.maps.get(map_id)
        if m:
            return m.get((wx, wy))
        return None

    def get_wall(self, map_id: int, wx: int, wy: int, dx: int, dy: int) -> int:
        """Get the wall value between (wx, wy) and (wx+dx, wy+dy)."""
        if dx == 0 and dy == -1:
            return self.edges.get(("h", wx, wy), 0)
        if dx == 0 and dy == 1:
            return self.edges.get(("h", wx, wy + 1), 0)
        if dx == -1 and dy == 0:
            return self.edges.get(("v", wx, wy), 0)
        if dx == 1 and dy == 0:
            return self.edges.get(("v", wx + 1, wy), 0)
        return 0
