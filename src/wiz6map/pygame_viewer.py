from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .combat import CombatState, Monster, PartyMember
from .data import PortraitSet, RecordData
from .engine import GameEngine, PlayerState, load_game_data_bundle
from .tiles import TileSet


@dataclass(frozen=True)
class RenderConfig:
    tile_scale: int = 2
    portrait_scale: int = 2
    monster_width: int = 16
    monster_height: int = 16
    monster_scale: int = 2
    background: tuple[int, int, int] = (16, 16, 24)
    grid_color: tuple[int, int, int] = (40, 40, 56)
    player_color: tuple[int, int, int] = (255, 215, 0)
    combat_panel: tuple[int, int, int] = (24, 24, 36)
    combat_border: tuple[int, int, int] = (90, 90, 110)
    combat_text: tuple[int, int, int] = (230, 230, 230)


def run_pygame_viewer(
    *,
    map_path: str | Path,
    map_format: str | None = None,
    map_width: int | None = None,
    map_height: int | None = None,
    tiles_path: str | Path | None = None,
    tiles_format: str | None = None,
    tile_width: int | None = None,
    tile_height: int | None = None,
    tile_count: int | None = None,
    monsters_path: str | Path | None = None,
    items_path: str | Path | None = None,
    npcs_path: str | Path | None = None,
    conversations_path: str | Path | None = None,
    game_data_path: str | Path | None = None,
    save_game_path: str | Path | None = None,
    save_game_expected_size: int | None = None,
    portraits_path: str | Path | None = None,
    portrait_width: int | None = None,
    portrait_height: int | None = None,
    portrait_count: int | None = None,
    start_x: int = 0,
    start_y: int = 0,
    render_config: RenderConfig | None = None,
) -> int:
    try:
        import pygame
    except ImportError as exc:  # pragma: no cover - depends on local install
        raise RuntimeError("pygame is required for the graphical viewer") from exc

    data = load_game_data_bundle(
        map_path=map_path,
        map_format=map_format,
        map_width=map_width,
        map_height=map_height,
        tiles_path=tiles_path,
        tiles_format=tiles_format,
        tile_width=tile_width,
        tile_height=tile_height,
        tile_count=tile_count,
        monsters_path=monsters_path,
        items_path=items_path,
        npcs_path=npcs_path,
        conversations_path=conversations_path,
        game_data_path=game_data_path,
        save_game_path=save_game_path,
        save_game_expected_size=save_game_expected_size,
        portraits_path=portraits_path,
        portrait_width=portrait_width,
        portrait_height=portrait_height,
        portrait_count=portrait_count,
    )
    engine = GameEngine(data, PlayerState(x=start_x, y=start_y))
    config = render_config or RenderConfig()

    pygame.init()
    pygame.display.set_caption("Wizardry 6 Viewer")

    tile_pixel_width = data.tiles.tile_width if data.tiles else 1
    tile_pixel_height = data.tiles.tile_height if data.tiles else 1
    grid_width = engine.map_grid.width * tile_pixel_width * config.tile_scale + 20
    grid_height = engine.map_grid.height * tile_pixel_height * config.tile_scale + 20
    side_panel_width = 320
    window_size = (grid_width + side_panel_width, max(grid_height, 480))
    screen = pygame.display.set_mode(window_size)

    clock = pygame.time.Clock()
    combat_state = _build_combat_state(data.portraits, data.monsters)
    combat_mode = False
    last_combat_tick = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_c:
                    combat_mode = not combat_mode
                if event.key == pygame.K_UP:
                    engine.move("n")
                if event.key == pygame.K_DOWN:
                    engine.move("s")
                if event.key == pygame.K_LEFT:
                    engine.move("w")
                if event.key == pygame.K_RIGHT:
                    engine.move("e")

        screen.fill(config.background)
        if combat_mode:
            now = pygame.time.get_ticks()
            if now - last_combat_tick > 1000 and combat_state and not combat_state.over:
                combat_state.perform_attack()
                last_combat_tick = now
            _draw_combat(screen, combat_state, data.portraits, data.monsters, config)
        else:
            _draw_grid(screen, engine, data.tiles, config)
            _draw_portraits(screen, data.portraits, grid_width, config)
            _draw_monsters(screen, data.monsters, grid_width, 220, config)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return 0


def _draw_grid(screen, engine: GameEngine, tiles: TileSet | None, config: RenderConfig):
    import pygame

    offset_x = 10
    offset_y = 10
    tile_scale = config.tile_scale
    tile_pixel_width = tiles.tile_width if tiles else 1
    tile_pixel_height = tiles.tile_height if tiles else 1

    for y in range(engine.map_grid.height):
        for x in range(engine.map_grid.width):
            px = offset_x + x * tile_pixel_width * tile_scale
            py = offset_y + y * tile_pixel_height * tile_scale
            if tiles:
                tile_index = engine.map_grid.tile_at(x, y).value % len(tiles.tiles)
                tile_pixels = tiles.tile_pixels(tile_index)
                _blit_pixels(
                    screen,
                    tile_pixels,
                    px,
                    py,
                    tile_scale,
                )
            else:
                rect = pygame.Rect(
                    px,
                    py,
                    tile_pixel_width * tile_scale,
                    tile_pixel_height * tile_scale,
                )
                pygame.draw.rect(screen, config.grid_color, rect, 1)

            if x == engine.player.x and y == engine.player.y:
                player_rect = pygame.Rect(
                    px,
                    py,
                    tile_pixel_width * tile_scale,
                    tile_pixel_height * tile_scale,
                )
                pygame.draw.rect(screen, config.player_color, player_rect, 2)


def _draw_portraits(
    screen, portraits: PortraitSet | None, start_x: int, config: RenderConfig
):
    if portraits is None:
        return

    x = start_x + 10
    y = 10
    for portrait in portraits.portraits[:6]:
        pixels = _pixels_from_bytes(portrait, portraits.width, portraits.height)
        _blit_pixels(screen, pixels, x, y, config.portrait_scale)
        y += portraits.height * config.portrait_scale + 10


def _draw_monsters(
    screen,
    monsters: RecordData | None,
    start_x: int,
    start_y: int,
    config: RenderConfig,
):
    if monsters is None:
        return

    x = start_x + 170
    y = start_y
    for record in monsters.records[:4]:
        pixels = _pixels_from_bytes(record, config.monster_width, config.monster_height)
        _blit_pixels(screen, pixels, x, y, config.monster_scale)
        y += config.monster_height * config.monster_scale + 10


def _pixels_from_bytes(
    payload: bytes, width: int, height: int
) -> tuple[tuple[int, ...], ...]:
    expected = width * height
    if expected == 0:
        return tuple()
    data = payload[:expected].ljust(expected, b"\x00")
    rows = []
    for row in range(height):
        start = row * width
        rows.append(tuple(data[start : start + width]))
    return tuple(rows)


def _split_monster_frames(
    payload: bytes, width: int, height: int
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    frame_size = width * height
    if frame_size == 0:
        empty = tuple()
        return empty, empty
    first = _pixels_from_bytes(payload[:frame_size], width, height)
    second = _pixels_from_bytes(payload[frame_size : frame_size * 2], width, height)
    return first, second


def _blit_pixels(screen, pixels, x: int, y: int, scale: int) -> None:
    import pygame

    for row_index, row in enumerate(pixels):
        for col_index, value in enumerate(row):
            shade = int(value)
            color = (shade, shade, shade)
            rect = pygame.Rect(
                x + col_index * scale, y + row_index * scale, scale, scale
            )
            screen.fill(color, rect)


def _build_combat_state(
    portraits: PortraitSet | None, monsters: RecordData | None
) -> CombatState | None:
    if portraits is None or monsters is None:
        return None

    party = []
    for index in range(min(6, len(portraits.portraits))):
        party.append(PartyMember(name=f"Hero {index + 1}", hp=20, attack=6, defense=2))

    monster_list = []
    for index in range(min(3, len(monsters.records))):
        monster_list.append(
            Monster(
                name=f"Rat {index + 1}",
                hp=12,
                attack=4,
                defense=1,
                sprite_index=index,
            )
        )
    if not party or not monster_list:
        return None
    return CombatState(party=party, monsters=monster_list)


def _draw_combat(
    screen,
    combat_state: CombatState | None,
    portraits: PortraitSet | None,
    monsters: RecordData | None,
    config: RenderConfig,
) -> None:
    import pygame

    width, height = screen.get_size()
    panel = pygame.Rect(20, 20, width - 40, height - 40)
    pygame.draw.rect(screen, config.combat_panel, panel)
    pygame.draw.rect(screen, config.combat_border, panel, 2)

    font = pygame.font.Font(None, 24)
    title = font.render("Combat", True, config.combat_text)
    screen.blit(title, (panel.x + 10, panel.y + 10))

    if combat_state is None or portraits is None or monsters is None:
        notice = font.render(
            "Missing portraits or monsters data.", True, config.combat_text
        )
        screen.blit(notice, (panel.x + 10, panel.y + 40))
        return

    _draw_party_panel(screen, combat_state, portraits, panel, config)
    _draw_monster_panel(screen, combat_state, monsters, panel, config)

    status = combat_state.victors
    if status:
        message = f"{status.title()} win!"
    else:
        message = "Press C to exit combat."
    status_text = font.render(message, True, config.combat_text)
    screen.blit(status_text, (panel.x + 10, panel.bottom - 30))


def _draw_party_panel(
    screen,
    combat_state: CombatState,
    portraits: PortraitSet,
    panel,
    config: RenderConfig,
) -> None:
    import pygame

    x = panel.x + 20
    y = panel.y + 50
    font = pygame.font.Font(None, 20)

    for index, member in enumerate(combat_state.party):
        portrait = portraits.portraits[index % len(portraits.portraits)]
        pixels = _pixels_from_bytes(portrait, portraits.width, portraits.height)
        _blit_pixels(screen, pixels, x, y, config.portrait_scale)
        label = font.render(f"{member.name} HP {member.hp}", True, config.combat_text)
        screen.blit(label, (x + portraits.width * config.portrait_scale + 10, y + 5))
        y += portraits.height * config.portrait_scale + 12


def _draw_monster_panel(
    screen,
    combat_state: CombatState,
    monsters: RecordData,
    panel,
    config: RenderConfig,
) -> None:
    import pygame

    font = pygame.font.Font(None, 20)
    base_x = panel.centerx + 20
    base_y = panel.y + 80
    now = pygame.time.get_ticks()
    frame_index = 1 if (now // 250) % 2 else 0

    for index, monster in enumerate(combat_state.monsters):
        record = monsters.records[monster.sprite_index % len(monsters.records)]
        first, second = _split_monster_frames(
            record, config.monster_width, config.monster_height
        )
        pixels = second if frame_index else first
        _blit_pixels(screen, pixels, base_x, base_y, config.monster_scale)
        label = font.render(f"{monster.name} HP {monster.hp}", True, config.combat_text)
        screen.blit(
            label,
            (base_x, base_y + config.monster_height * config.monster_scale + 4),
        )
        base_x += config.monster_width * config.monster_scale + 30
