from __future__ import annotations

import logging
from pathlib import Path

import pygame
from PIL import Image

from bane.world.maze import Wiz6Maze
from bane.engine import render_pipeline

logger = logging.getLogger(__name__)

VIEW_W, VIEW_H = 176, 112

class Renderer3D:
    """
    Proper Stage-Based Renderer
    Implements the explicit, data-driven pipeline defined in docs/render_pipeline_stage_map.md
    1. scene_state
    2. helper_pass_replay
    3. deferred_queue_replay
    4. driver_shadow_present
    """
    def __init__(self, gamedata_path: Path):
        self.gamedata_path = gamedata_path
        self.scratch_dir = gamedata_path.parent / "scratch"
        self.db_path = gamedata_path / "NEWGAME.DBS"
        self.maze = Wiz6Maze(self.db_path)
        self.prior_temporal_state = None

    def render_view(self, map_id: int, wx: int, wy: int, facing: str) -> pygame.Surface:
        # 1. Execute the full disassembly-faithful stage pipeline
        try:
            outputs = render_pipeline.build_stage_reference(
                gamedata=self.gamedata_path,
                scratch_dir=self.scratch_dir,
                map_id=map_id,
                wx=wx,
                wy=wy,
                facing=facing,
                prior_present_temporal_state=self.prior_temporal_state
            )
            
            # Save temporal state for next frame's 36A0 masking
            if outputs.stage5_shadow_buffer_replay.shadow_state:
                self.prior_temporal_state = outputs.stage5_shadow_buffer_replay.shadow_state.get("present_36a0_temporal_state")
                
            # 2. Render the final shadow image using the actual EGA Driver 36AC/3670 emulation
            pil_img = render_pipeline.render_stage5_shadow_image(
                target=outputs.stage5_shadow_buffer_target,
                replay=outputs.stage5_shadow_buffer_replay,
                gamedata=self.gamedata_path
            )
            
            # 3. Convert to Pygame Surface
            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            surf = pygame.image.frombuffer(data, size, mode)
            
            # 4. Scale to standard viewport if needed (the crop is already 176x112 from the pipeline)
            if size != (VIEW_W, VIEW_H):
                surf = pygame.transform.scale(surf, (VIEW_W, VIEW_H))
                
            return surf
            
        except Exception as e:
            logger.error(f"Render pipeline failed: {e}")
            # Fallback to empty EGA background
            surf = pygame.Surface((VIEW_W, VIEW_H))
            surf.fill((6, 8, 14))
            return surf
