"""Main engine class — game loop, initialization, and shutdown."""

from __future__ import annotations

import logging
import time

import pygame

from bane.engine.config import ORIGINAL_HEIGHT, ORIGINAL_WIDTH, EngineConfig
from bane.engine.event_bus import EventBus
from bane.engine.renderer import Renderer
from bane.engine.resource_manager import ResourceManager
from bane.engine.state_machine import StateMachine

logger = logging.getLogger(__name__)

# Fixed timestep for game logic (60 updates per second)
FIXED_DT = 1.0 / 60.0
MAX_FRAME_TIME = 0.25  # prevent spiral of death


class Engine:
    """Main game engine — owns all subsystems and runs the game loop.

    Usage:
        config = EngineConfig(gamedata_path=Path("gamedata"))
        engine = Engine(config)
        engine.run()  # blocking — runs until quit
        engine.shutdown()
    """

    def __init__(self, config: EngineConfig) -> None:
        self.config = config
        self.running = False

        # Set up logging
        logging.basicConfig(
            level=getattr(logging, config.log_level, logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        logger.info("Bane Engine initializing...")

        # Initialize pygame
        pygame.init()
        pygame.display.set_caption("Bane Engine — Wizardry VI")

        # Create window
        window_size = (config.window_width, config.window_height)
        flags = pygame.RESIZABLE
        if config.fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(window_size, flags)

        # Core systems
        self.event_bus = EventBus()
        self.resources = ResourceManager(config)
        self.renderer = Renderer(self.screen, config.scale_factor, config.gamedata_path)
        self.state_machine = StateMachine()

        # Clock for frame timing
        self._clock = pygame.time.Clock()

        logger.info(
            "Engine initialized: %dx%d window, scale=%d",
            config.window_width,
            config.window_height,
            config.scale_factor,
        )

    def run(self) -> None:
        """Run the main game loop. Blocks until the game exits."""
        logger.info("Starting game loop")
        self.running = True

        # Load game data
        warnings = self.resources.load_all()
        for w in warnings:
            logger.warning("Resource load warning: %s", w)

        # Push initial state
        from bane.ui.main_menu import MainMenuState
        self.state_machine.push(MainMenuState, engine=self)

        accumulator = 0.0
        previous_time = time.perf_counter()

        while self.running:
            current_time = time.perf_counter()
            frame_time = min(current_time - previous_time, MAX_FRAME_TIME)
            previous_time = current_time
            accumulator += frame_time

            # Process input
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F12:
                        self.config.debug_overlay = not self.config.debug_overlay
                    if event.key == pygame.K_F11:
                        self._toggle_fullscreen()

            self.state_machine.handle_input(events)

            # Fixed timestep updates
            while accumulator >= FIXED_DT:
                self.state_machine.update(FIXED_DT)
                accumulator -= FIXED_DT

            # Render
            self.renderer.begin_frame()
            self.state_machine.render(self.renderer.internal)

            if self.config.debug_overlay:
                self._render_debug_overlay()

            self.renderer.end_frame()

            # Cap frame rate
            self._clock.tick(60)

    def shutdown(self) -> None:
        """Clean up and shut down."""
        logger.info("Shutting down engine")
        self.state_machine.clear()
        self.state_machine.process_pending()
        pygame.quit()

    def _toggle_fullscreen(self) -> None:
        self.config.fullscreen = not self.config.fullscreen
        if self.config.fullscreen:
            self.screen = pygame.display.set_mode(
                (self.config.window_width, self.config.window_height),
                pygame.FULLSCREEN,
            )
        else:
            self.screen = pygame.display.set_mode(
                (self.config.window_width, self.config.window_height),
                pygame.RESIZABLE,
            )
        self.renderer = Renderer(self.screen, self.config.scale_factor, self.config.gamedata_path)

    def _render_debug_overlay(self) -> None:
        """Render FPS and state info."""
        fps = self._clock.get_fps()
        self.renderer.draw_text(f"FPS: {fps:.0f}", 2, 2, (0, 255, 0))
        state = self.state_machine.current
        if state:
            self.renderer.draw_text(
                f"State: {type(state).__name__}", 2, 12, (0, 255, 0)
            )
        self.renderer.draw_text(
            f"Stack: {self.state_machine.stack_depth}", 2, 22, (0, 255, 0)
        )
