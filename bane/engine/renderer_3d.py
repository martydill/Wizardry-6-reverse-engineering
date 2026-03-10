from __future__ import annotations

import logging
from pathlib import Path

import pygame
from PIL import Image

from bane.engine import render_pipeline
from bane.engine import wmaze_compositor
from bane.world.maze import Wiz6Maze

logger = logging.getLogger(__name__)

VIEW_W, VIEW_H = 176, 112


class Renderer3D:
    """
    Stage-backed live renderer.

    The live app now uses the same stage reference and stage-5 replay path that the
    reverse-engineering work targets, instead of the old primitive-only fallback.
    """

    def __init__(self, gamedata_path: Path):
        self.gamedata_path = gamedata_path
        self.scratch_dir = gamedata_path.parent / "scratch"
        self.db_path = gamedata_path / "NEWGAME.DBS"
        self.maze = Wiz6Maze(self.db_path)
        self.prior_temporal_state: dict | None = None
        self._last_scene_key: tuple[int, int, int, str] | None = None
        self._last_surface: pygame.Surface | None = None
        self._primitive_img: dict[int, Image.Image] | None = None
        self._pass_param_doc: dict | None = None
        self._handler_offsets_doc: dict | None = None
        self._helper_draw_mode_doc: dict | None = None

    def _ensure_helper_pass_resources(self) -> None:
        if self._primitive_img is None:
            mpath = self.gamedata_path / "MAZEDATA.EGA"
            sprites = wmaze_compositor.decode_mazedata_tiles(mpath)
            sprite_trans, sprite_opaque = wmaze_compositor.build_sprite_layers(sprites)
            all_records = wmaze_compositor.parse_display_records(mpath)
            primitive_img: dict[int, Image.Image] = {}
            for idx, rec in enumerate(all_records):
                primitive_img[idx] = wmaze_compositor.render_owner_blitmode(
                    [rec],
                    sprite_trans,
                    sprite_opaque,
                    blit_mode="heuristic",
                )
            self._primitive_img = primitive_img
        if self._pass_param_doc is None:
            self._pass_param_doc = wmaze_compositor.load_json_if_exists(
                self.scratch_dir / "wmaze_render_pass_param_map.json"
            )
        if self._handler_offsets_doc is None:
            self._handler_offsets_doc = wmaze_compositor.load_json_if_exists(
                self.scratch_dir / "wmaze_draw_handler_record_offsets.json"
            )
        if self._helper_draw_mode_doc is None:
            self._helper_draw_mode_doc = wmaze_compositor.load_json_if_exists(
                self.scratch_dir / "wmaze_helper_draw_mode_map.json"
            )

    def _render_helper_primitive_base(
        self,
        *,
        outputs: render_pipeline.StageOutputs,
        wx: int,
        wy: int,
        facing: str,
    ) -> Image.Image | None:
        self._ensure_helper_pass_resources()
        if not self._primitive_img or not self._pass_param_doc or not self._handler_offsets_doc:
            return None
        canvas = Image.new("RGBA", (200, 140), (10, 10, 14, 255))
        facing_idx = wmaze_compositor.facing_to_index(facing)
        dx, dy = wmaze_compositor.dir_vec(facing)
        lx, ly = -dy, dx
        rx, ry = dy, -dx
        depth_limit = render_pipeline.scene_render_depth_limit(outputs.scene)
        visible: list[tuple[str, int, int]] = []
        visible_details: list[dict] = []
        for vs in outputs.scene.visible_slots:
            if int(vs.depth) > int(depth_limit):
                continue
            visible.append((vs.orient, vs.depth, vs.wall_value))
            bx = int(wx) + int(dx) * (int(vs.depth) - 1)
            by = int(wy) + int(dy) * (int(vs.depth) - 1)
            if str(vs.orient) == "left":
                bx += int(lx)
                by += int(ly)
            elif str(vs.orient) == "right":
                bx += int(rx)
                by += int(ry)
            visible_details.append(
                {
                    "orient": str(vs.orient),
                    "depth": int(vs.depth),
                    "channel4_1f8": vs.channel4,
                    "channel2_378": vs.channel2,
                    "cell_ref": {
                        "block": vs.block,
                        "row": vs.row,
                        "col": vs.col,
                    },
                    "base_cell": {
                        "wx": int(bx),
                        "wy": int(by),
                    },
                }
            )
        drawidx_overrides: dict[tuple[int, str, str], int] = {}
        for row in outputs.stage1_pass_state.pass_rows:
            depth = row.depth
            slot = row.slot_hint
            helper = row.draw_target
            draw_idx = row.predicted_draw_index
            if depth is None or slot is None or helper is None or draw_idx is None:
                continue
            drawidx_overrides[(int(depth), str(helper), str(slot))] = int(draw_idx)
        wmaze_compositor.render_wmaze_pass_experimental(
            map_id=outputs.scene.map_id,
            origins=outputs.scene.origins,
            facing_idx=facing_idx,
            canvas=canvas,
            visible=visible,
            visible_details=visible_details,
            primitive_img=self._primitive_img,
            pass_param_doc=self._pass_param_doc,
            handler_offsets_doc=self._handler_offsets_doc,
            helper_draw_mode_doc=self._helper_draw_mode_doc or {},
            fallback_seed_map={1: 5, 2: 0, 3: 10},
            drawidx_overrides=drawidx_overrides,
            respect_helper_draw_modes=True,
            suppress_direct_36ac_primitive_fallback=True,
        )
        return canvas.crop((12, 14, 188, 126))

    @staticmethod
    def _transparentize_background(
        img: Image.Image,
        *,
        bg: tuple[int, int, int] = (6, 8, 14),
    ) -> Image.Image:
        rgba = img.convert("RGBA")
        px = rgba.load()
        for y in range(rgba.height):
            for x in range(rgba.width):
                r, g, b, a = px[x, y]
                if a and (r, g, b) == bg:
                    px[x, y] = (r, g, b, 0)
        return rgba

    def render_view(self, map_id: int, wx: int, wy: int, facing: str) -> pygame.Surface:
        scene_key = (int(map_id), int(wx), int(wy), str(facing))
        if self._last_scene_key == scene_key and self._last_surface is not None:
            return self._last_surface.copy()

        try:
            outputs = render_pipeline.build_stage_reference(
                gamedata=self.gamedata_path,
                scratch_dir=self.scratch_dir,
                map_id=map_id,
                wx=wx,
                wy=wy,
                facing=facing,
                prior_present_temporal_state=self.prior_temporal_state,
            )
            if outputs.stage5_shadow_buffer_replay.shadow_state:
                self.prior_temporal_state = outputs.stage5_shadow_buffer_replay.shadow_state.get(
                    "present_36a0_temporal_state"
                )

            pil_img = render_pipeline.render_stage5_shadow_image(
                target=outputs.stage5_shadow_buffer_target,
                replay=outputs.stage5_shadow_buffer_replay,
                gamedata=self.gamedata_path,
                include_deferred_3670=False,
                include_present_36a0=False,
            )
            helper_base = self._render_helper_primitive_base(
                outputs=outputs,
                wx=wx,
                wy=wy,
                facing=facing,
            )
            if helper_base is not None:
                pil_img = Image.alpha_composite(
                    helper_base.convert("RGBA"),
                    self._transparentize_background(pil_img),
                )

            mode = pil_img.mode
            size = pil_img.size
            data = pil_img.tobytes()
            surf = pygame.image.frombuffer(data, size, mode)
            if size != (VIEW_W, VIEW_H):
                surf = pygame.transform.scale(surf, (VIEW_W, VIEW_H))

            self._last_scene_key = scene_key
            self._last_surface = surf.copy()
            return surf
        except Exception as exc:
            logger.error("Render pipeline failed: %s", exc)
            surf = pygame.Surface((VIEW_W, VIEW_H))
            surf.fill((6, 8, 14))
            self._last_scene_key = scene_key
            self._last_surface = surf.copy()
            return surf
