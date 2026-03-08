from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from PIL import Image
import pygame

from bane.data.sprite_decoder import decode_mazedata_tiles, Sprite

logger = logging.getLogger(__name__)

class DisplayRecord(TypedDict):
    owner_id: int
    tile_ref: int
    x: int
    y: int
    aux: int

class MazedataAtlas:
    def __init__(self, path: Path):
        self.path = path
        self.sprites = decode_mazedata_tiles(path)
        self.records = self._parse_display_records(path)
        self.owner_to_records: dict[int, list[DisplayRecord]] = {}
        for r in self.records:
            self.owner_to_records.setdefault(r["owner_id"], []).append(r)
        
        # Build tile surfaces for pygame
        self.tile_surfs: list[pygame.Surface | None] = []
        for sp in self.sprites:
            rgba = sp.to_rgba_bytes(transparent_index=0)
            s = pygame.image.frombuffer(rgba, (sp.width, sp.height), "RGBA")
            self.tile_surfs.append(s.convert_alpha())

    def _parse_display_records(self, path: Path) -> list[DisplayRecord]:
        data = path.read_bytes()
        n = data[0] | (data[1] << 8)
        n2 = data[2] | (data[3] << 8)
        st = 4 + n * 5
        raw = data[st : st + n2 * 5]
        recs: list[DisplayRecord] = []
        for i in range(n2):
            b = raw[i * 5 : i * 5 + 5]
            if len(b) < 5:
                break
            recs.append({
                "owner_id": b[0],
                "tile_ref": b[1],
                "x": b[2],
                "y": b[3],
                "aux": b[4],
            })
        return recs

    def build_composite(self, owner_id: int, stream_tile: pygame.Surface | None = None) -> pygame.Surface:
        """Build a composite surface for an owner, optionally injecting a stream tile."""
        s = pygame.Surface((200, 140))
        s.fill((0, 0, 0))
        s.set_colorkey((0, 0, 0))
        
        recs = self.owner_to_records.get(owner_id, [])
        prev_surf: pygame.Surface | None = None
        
        for r in recs:
            t = r["tile_ref"]
            x, y = r["x"], r["y"]
            
            if t == 0:
                # Stream placeholder
                if stream_tile:
                    s.blit(stream_tile, (x, y))
                continue
                
            if t == 255:
                # Repeat previous
                if prev_surf:
                    s.blit(prev_surf, (x, y))
                continue
                
            idx = t - 1
            if 0 <= idx < len(self.tile_surfs):
                ts = self.tile_surfs[idx]
                if ts:
                    s.blit(ts, (x, y))
                    prev_surf = ts
                    
        return s

    def get_owner_stream_positions(self, owner_id: int) -> list[tuple[int, int]]:
        """Get all (x, y) positions where a stream tile should be blitted for this owner."""
        recs = self.owner_to_records.get(owner_id, [])
        return [(r["x"], r["y"]) for r in recs if r["tile_ref"] == 0]
