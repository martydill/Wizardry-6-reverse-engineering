"""Engine configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# Original Wizardry 6 resolution
ORIGINAL_WIDTH = 320
ORIGINAL_HEIGHT = 200


@dataclass
class EngineConfig:
    """Configuration for the Bane Engine."""

    # Path to the directory containing original Wizardry 6 data files
    gamedata_path: Path = field(default_factory=lambda: Path("gamedata"))

    # Window settings
    window_width: int = 960
    window_height: int = 600
    fullscreen: bool = False
    scale_factor: int = 3  # integer scale for pixel-perfect rendering
    vsync: bool = True

    # Audio
    master_volume: float = 1.0
    sfx_volume: float = 1.0
    music_volume: float = 0.7

    # Gameplay
    movement_speed: str = "normal"  # "instant", "fast", "normal", "slow"
    combat_speed: str = "normal"  # "fast", "normal", "slow"
    text_speed: str = "normal"  # "instant", "fast", "normal", "slow"
    show_automap: bool = True
    show_minimap: bool = True

    # Debug
    debug_overlay: bool = False
    log_level: str = "INFO"

    # Mods
    mod_path: Path = field(default_factory=lambda: Path("mods"))

    @property
    def scenario_dbs_path(self) -> Path:
        return self.gamedata_path / "SCENARIO.DBS"

    @property
    def scenario_hdr_path(self) -> Path:
        return self.gamedata_path / "SCENARIO.HDR"

    @property
    def pcfile_dbs_path(self) -> Path:
        return self.gamedata_path / "PCFILE.DBS"

    @property
    def savegame_dbs_path(self) -> Path:
        return self.gamedata_path / "SAVEGAME.DBS"

    def validate_gamedata(self) -> list[str]:
        """Check for required game data files. Returns list of missing files."""
        required = [
            self.scenario_dbs_path,
            self.scenario_hdr_path,
        ]
        return [str(p) for p in required if not p.exists()]

    def save(self, path: Path | str) -> None:
        """Save configuration to a JSON file."""
        data = {
            "gamedata_path": str(self.gamedata_path),
            "window_width": self.window_width,
            "window_height": self.window_height,
            "fullscreen": self.fullscreen,
            "scale_factor": self.scale_factor,
            "vsync": self.vsync,
            "master_volume": self.master_volume,
            "sfx_volume": self.sfx_volume,
            "music_volume": self.music_volume,
            "movement_speed": self.movement_speed,
            "combat_speed": self.combat_speed,
            "text_speed": self.text_speed,
            "show_automap": self.show_automap,
            "show_minimap": self.show_minimap,
            "debug_overlay": self.debug_overlay,
            "log_level": self.log_level,
            "mod_path": str(self.mod_path),
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: Path | str) -> EngineConfig:
        """Load configuration from a JSON file."""
        data = json.loads(Path(path).read_text())
        return cls(
            gamedata_path=Path(data.get("gamedata_path", "gamedata")),
            window_width=data.get("window_width", 960),
            window_height=data.get("window_height", 600),
            fullscreen=data.get("fullscreen", False),
            scale_factor=data.get("scale_factor", 3),
            vsync=data.get("vsync", True),
            master_volume=data.get("master_volume", 1.0),
            sfx_volume=data.get("sfx_volume", 1.0),
            music_volume=data.get("music_volume", 0.7),
            movement_speed=data.get("movement_speed", "normal"),
            combat_speed=data.get("combat_speed", "normal"),
            text_speed=data.get("text_speed", "normal"),
            show_automap=data.get("show_automap", True),
            show_minimap=data.get("show_minimap", True),
            debug_overlay=data.get("debug_overlay", False),
            log_level=data.get("log_level", "INFO"),
            mod_path=Path(data.get("mod_path", "mods")),
        )
