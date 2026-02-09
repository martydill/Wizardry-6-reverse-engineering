# Bane Engine — Modern Wizardry 6 Engine Remake

## Project Overview

**Bane Engine** is a modern, open-source game engine capable of loading and playing Wizardry VI: Bane of the Cosmic Forge using original game data files. The engine will faithfully reproduce all gameplay mechanics while providing modern rendering, resolution support, and quality-of-life features.

This is a **clean-room engine reimplementation** — no original code is used. The engine reads the original binary data files (`SCENARIO.DBS`, `SAVEGAME.DBS`, `PCFILE.DBS`, etc.) and renders the game using modern technology.

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.11+ | Rapid development, excellent binary parsing (struct), rich ecosystem |
| Build System | pyproject.toml + pip | Standard Python packaging |
| Rendering | pygame-ce (SDL2) | Cross-platform 2D/3D, active community fork |
| Image Processing | Pillow (PIL) | Sprite extraction, format conversion |
| Serialization | struct (binary) + json | Binary for original format compat, JSON for new saves |
| Testing | pytest | Unit + integration tests for parsers and game logic |
| Linting | ruff + mypy | Fast linting and static type checking |
| Scripting | Lua via lupa (future) | Event scripting, moddability |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Bane Engine                        │
├─────────────┬─────────────┬─────────────┬───────────────┤
│  Rendering  │   Audio     │   Input     │   UI Layer    │
│  (SDL3/GL)  │  (SDL3)     │  (SDL3)     │  (ImGui)      │
├─────────────┴─────────────┴─────────────┴───────────────┤
│                    Game Layer                            │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ Combat   │ Magic    │ Party    │ World/Exploration │  │
│  │ System   │ System   │ Manager  │ System            │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                   Core Systems                          │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ ECS      │ Event    │ State    │ Resource          │  │
│  │ Registry │ Bus      │ Machine  │ Manager           │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                  Data Layer                              │
│  ┌──────────┬──────────┬──────────┬──────────────────┐  │
│  │ DBS      │ Sprite   │ Map      │ Save/Load         │  │
│  │ Parser   │ Decoder  │ Loader   │ Handler           │  │
│  └──────────┴──────────┴──────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
Bane/
├── PLAN.md                   # This document
├── pyproject.toml            # Python project configuration
├── .gitignore
├── bane/                     # Main Python package
│   ├── __init__.py
│   ├── __main__.py           # Entry point (python -m bane)
│   ├── data/                 # Original data file parsers
│   │   ├── binary_reader.py          # BinaryReader/Writer utilities
│   │   ├── enums.py                  # All game enumerations
│   │   ├── models.py                 # Dataclass models for all entities
│   │   ├── scenario_parser.py        # SCENARIO.DBS master parser
│   │   ├── character_parser.py       # PCFILE.DBS character parser
│   │   ├── savegame_parser.py        # SAVEGAME.DBS save file parser
│   │   ├── sprite_decoder.py         # EGA sprite decoder + palette
│   │   └── map_loader.py             # Map/maze loader + DungeonMap
│   ├── engine/               # Core engine systems
│   │   ├── config.py                 # EngineConfig
│   │   ├── engine.py                 # Main engine class + game loop
│   │   ├── renderer.py               # 2D/3D rendering (pygame)
│   │   ├── event_bus.py              # Publish/subscribe events
│   │   ├── state_machine.py          # Game state stack
│   │   └── resource_manager.py       # Asset caching & loading
│   ├── game/                 # Game logic & mechanics
│   │   ├── character.py              # Character creation, leveling, class change
│   │   ├── party.py                  # Party management (6 members)
│   │   ├── combat.py                 # Turn-based combat engine
│   │   ├── magic.py                  # Spell casting & effects
│   │   └── inventory.py              # Items, equipment, merchants
│   ├── world/                # World/dungeon systems (future)
│   └── ui/                   # User interface
│       ├── main_menu.py              # Title screen & menu
│       └── exploration.py            # First-person dungeon exploration
├── tools/                    # Standalone data inspection tools
│   ├── dbs_dumper.py         # Dump DBS file contents
│   ├── sprite_viewer.py     # View extracted sprites
│   └── map_viewer.py        # Visualize map data
├── tests/                    # pytest test suite (100 tests)
│   ├── test_binary_reader.py
│   ├── test_enums.py
│   ├── test_character.py
│   ├── test_combat.py
│   ├── test_map_loader.py
│   └── test_sprite_decoder.py
├── assets/                   # Engine-provided assets
├── docs/                     # Reverse engineering documentation
└── mods/                     # User mod directory
```

---

## Phase 1 — Data Layer & Reverse Engineering Tools

**Goal:** Parse every original Wizardry 6 data file and expose structured data.

### 1.1 Project Scaffolding
- [x] Initialize Python project with pyproject.toml
- [x] Set up dependency management (pygame-ce, Pillow, pytest, ruff, mypy)
- [x] Create directory structure
- [ ] Configure CI (GitHub Actions: build + test on Linux/macOS/Windows)
- [ ] Set up ruff / mypy linting

### 1.2 Binary File Infrastructure
- [x] Implement `BinaryReader` utility class (little-endian reads, seek, bounds checking)
- [x] Implement `BinaryWriter` for save game output
- [x] Create hex dump / inspection tool (`tools/dbs_dumper`)

### 1.3 SCENARIO.DBS Parser
This is the most critical and complex file — it contains the entire game world.

- [ ] Parse file header and identify section offsets
- [ ] **Monster Data Loader**
  - [ ] Parse monster names, stats (HP, AC, level, XP reward)
  - [ ] Parse 9 attack mode AC modifiers per monster
  - [ ] Parse attack types, damage ranges, number of attacks
  - [ ] Parse spell casting data (spell list, cast probability)
  - [ ] Parse resistances (fire, cold, electric, mental, divine, etc.)
  - [ ] Parse HP regeneration parameters
  - [ ] Parse loot table references
  - [ ] Parse special abilities (breath weapons, group attacks, etc.)
  - [ ] Parse the "double damage type" byte (and document the Fighter type 0 bug)
- [ ] **Item Data Loader**
  - [ ] Parse item names, types, weight, value
  - [ ] Parse equipment slot restrictions
  - [ ] Parse weapon damage, to-hit bonuses, attack modes
  - [ ] Parse armor AC values per attack mode
  - [ ] Parse special effects (cursed, quest items, castable spells)
  - [ ] Parse class/race/sex equip restrictions
  - [ ] Parse item flags (identified, equipped, cursed, etc.)
- [ ] **Spell Data Loader**
  - [ ] Parse spell names, schools (Mage/Priest/Alchemist/Psionic)
  - [ ] Parse spell levels (1–7), power levels
  - [ ] Parse spell effects, target types, damage/healing formulas
  - [ ] Parse spell costs (SP)
  - [ ] Parse status effect durations
- [ ] **Loot Table Loader**
  - [ ] Parse per-monster/chest drop probability tables
  - [ ] Parse item pool references and drop weights
- [ ] **Class/Race Data Loader**
  - [ ] Parse race stat modifiers, min/max stats
  - [ ] Parse race resistances and special abilities
  - [ ] Parse class requirements (stat minimums)
  - [ ] Parse class spell school access
  - [ ] Parse experience tables per class
  - [ ] Parse HP/Stamina/SP gain formulas per class
  - [ ] Parse starting equipment lists
  - [ ] Parse skill lists per class (learnable, improvable-by-use)
- [ ] **Map/Maze Data Loader**
  - [ ] Parse dungeon dimensions per level
  - [ ] Parse tile wall data (4 walls × 2-bit encoding: none/wall/door/secret)
  - [ ] Parse tile floor/ceiling types
  - [ ] Parse texture palette references per zone
  - [ ] Parse special tile types (stairs, teleporters, spinners, dark zones, anti-magic)
  - [ ] Parse encounter zones (random encounter probability per tile)
  - [ ] Parse fixed encounter placements
- [ ] **Event/Trigger Data Loader**
  - [ ] Parse event trigger positions (tile x, y, level)
  - [ ] Parse event types (dialogue, trap, chest, NPC, scripted encounter)
  - [ ] Parse event conditions (flags, items required, etc.)
  - [ ] Parse event actions (give item, set flag, teleport, etc.)

### 1.4 SCENARIO.HDR Parser
- [ ] Parse scenario header fields
- [ ] Identify version/configuration data

### 1.5 Character & Save File Parsers

#### PCFILE.DBS (Character Data)
- [ ] Parse character name (ASCII string)
- [ ] Parse race, sex, profession (class), portrait index
- [ ] Parse 7 core ability scores (STR, INT, PIE, VIT, DEX, SPD, PER)
- [ ] Parse current/max HP, Stamina, Spell Points
- [ ] Parse level, experience, age, gold
- [ ] Parse all skills and skill levels
- [ ] Parse equipment slots (8 bytes per equipped item)
- [ ] Parse inventory (swag bag, 12 item slots)
- [ ] Parse known spells (bitfield decoding)
- [ ] Parse resistances and active conditions/status effects
- [ ] Parse monster kill count, carrying capacity, rebirths

#### SAVEGAME.DBS (Game State)
- [ ] Parse party composition reference
- [ ] Parse current dungeon level and position
- [ ] Parse facing direction
- [ ] Parse world state flags (quest progression, NPC states)
- [ ] Parse chest opened/looted states
- [ ] Parse game clock / time progression

### 1.6 EGA Sprite Decoder
- [ ] Implement EGA planar format decoder (4 planes × 1-bit → 16-color pixel)
- [ ] Implement EGA 64-color RGBI palette mapping
- [ ] Locate and parse sprite atlas/index within SCENARIO.DBS
- [ ] Extract individual sprites by ID
  - [ ] Monster sprites (front-facing combat portraits)
  - [ ] Wall/door/ceiling/floor textures
  - [ ] Item sprites
  - [ ] Character portrait sprites
  - [ ] UI element sprites (buttons, frames, borders)
  - [ ] NPC sprites
  - [ ] Spell effect sprites/animations
- [ ] Upscale sprites to target resolution (nearest-neighbor or configurable filter)
- [ ] Build `tools/sprite_viewer` — browse all extracted sprites in a window

### 1.7 Validation & Testing
- [ ] Write unit tests comparing parsed data against known Cosmic Forge Editor outputs
- [ ] Cross-reference monster stats with community wikis and guides
- [ ] Cross-reference item properties with known game data
- [ ] Build `tools/map_viewer` — top-down 2D visualization of parsed maze data
- [ ] Document all discovered binary format details in `docs/file_formats.md`

---

## Phase 2 — Core Engine Systems

**Goal:** Build the runtime engine framework that game systems plug into.

### 2.1 Engine Foundation
- [ ] Implement main game loop (fixed timestep update, variable render)
- [ ] Implement SDL3 window creation and OpenGL context setup
- [ ] Implement input system (keyboard, mouse, gamepad mapping)
- [ ] Implement game state machine (MainMenu → CharCreate → Exploration → Combat → etc.)
- [ ] Implement event bus (publish/subscribe for decoupled communication)
- [ ] Implement resource manager (load-once cache for parsed game data)
- [ ] Implement configuration system (resolution, fullscreen, keybinds, volume)

### 2.2 Rendering System
- [ ] Implement 2D sprite batch renderer (for UI, portraits, items)
- [ ] Implement first-person dungeon renderer
  - [ ] Raycasting or pre-computed view rendering for grid-based dungeon
  - [ ] Wall texture mapping from parsed tile wall types
  - [ ] Door rendering (closed, open, locked indicators)
  - [ ] Floor/ceiling rendering
  - [ ] Distance-based shading / fog
  - [ ] Support for special visual effects (dark zones, teleporter shimmer)
- [ ] Implement animation system for sprites (monster idle, attack, death)
- [ ] Implement screen transition effects (fade, wipe)
- [ ] Support multiple resolutions (original 320×200 scaled up, or 1920×1080 native UI)
- [ ] Implement optional CRT/scanline shader for retro aesthetic

### 2.3 Audio System
- [ ] Implement PC speaker emulation (original Wiz6 sound)
- [ ] Implement sound effect playback system
- [ ] Implement music playback (if original music data can be decoded)
- [ ] Implement volume controls (master, SFX, music)
- [ ] Support modern audio replacements (load WAV/OGG from an override folder)

### 2.4 UI Framework
- [ ] Implement text rendering (bitmap font from original + scalable TTF option)
- [ ] Implement dialogue box system (scrolling text, word wrap)
- [ ] Implement menu system (selectable lists, tabs)
- [ ] Implement tooltip system
- [ ] Implement modal dialogs (confirmation prompts, item inspection)

---

## Phase 3 — Game Logic Implementation

**Goal:** Implement all Wizardry 6 gameplay mechanics.

### 3.1 Character System
- [ ] Implement 11 races with stat modifiers, resistances, special abilities
  - Human, Elf, Dwarf, Gnome, Hobbit, Faerie, Lizardman, Dracon, Felpurr, Rawulf, Mook
- [ ] Implement 14 classes with stat requirements and progression
  - Fighter, Mage, Priest, Thief, Ranger, Alchemist, Bard, Psionic
  - Valkyrie, Bishop, Lord, Samurai, Monk, Ninja
- [ ] Implement character creation flow
  - Bonus point rolling, stat allocation, race/class validation
  - Portrait selection
  - Starting equipment assignment
  - Mana recovery rate determination (based on starting class)
- [ ] Implement class changing (multiclass) system
  - Stat reversion to race/class defaults
  - Spell retention at power level 1
  - Base miss chance tracking across class changes
- [ ] Implement level-up system
  - HP/Stamina/SP gains per class
  - Skill point allocation
  - Stat increases
  - New spell unlocks at skill thresholds (18/36/54/72/90/98)

### 3.2 Skill System
- [ ] Implement all skill categories
  - **Weapon skills** (Sword, Axe, Mace & Flail, Pole & Staff, Throwing, Sling, Bow, etc.)
  - **Physical skills** (Scouting, Swimming, Climbing, Skulduggery, etc.)
  - **Magic skills** (Alchemy, Theology, Theosophy, Thaumaturgy)
  - **Special skills** (Ninjutsu, Kirijutsu, Oratory, Legerdemain, etc.)
- [ ] Implement skill improvement through use (weapon skills, physical skills)
- [ ] Implement skills that only improve via level-up allocation (magic skills, Ninjutsu, Kirijutsu)
- [ ] Implement skill checks (lock picking, trap disarming, swimming, climbing)

### 3.3 Combat System
- [ ] Implement turn-based combat loop
  - Initiative / speed-based turn order
  - Action selection per character (Attack, Spell, Use Item, Defend, Flee, etc.)
  - Enemy AI action selection
- [ ] Implement attack resolution
  - Hit chance (attacker level vs. defender level, weapon skill, AC)
  - Damage calculation (weapon damage + modifiers)
  - Critical hits (Kirijutsu one-hit kill mechanic)
  - Multiple attacks per round
  - Base miss chance per class/level
- [ ] Implement 9 attack modes and damage types
  - Physical, Fire, Cold, Electric, Mental, Divine, etc.
  - Per-attack-mode AC calculations
  - Per-attack-mode resistances
- [ ] Implement group/party targeting
  - Single target, group, all enemies
  - Friendly fire considerations
  - Row/position mechanics
- [ ] Implement combat rewards
  - XP distribution
  - Loot drops (from parsed loot tables)
  - Gold
- [ ] Implement flee mechanics
- [ ] Implement monster special abilities
  - Breath weapons (Dracon breath, dragon breath)
  - Spell casting monsters
  - Level drain, poison, paralysis, petrification, etc.
  - HP regeneration during combat

### 3.4 Magic System
- [ ] Implement 4 spell schools: Mage, Priest, Alchemist, Psionic
- [ ] Implement 7 spell power levels per school
- [ ] Implement spell skill threshold unlocking (L2@18, L3@36, L4@54, L5@72, L6@90, L7@98)
- [ ] Implement spell effects
  - Direct damage (single, group, all)
  - Healing (HP, status cure)
  - Buffs (AC boost, stat boost, haste)
  - Debuffs (sleep, paralyze, poison, fear, silence)
  - Utility (light, levitate, identify, teleport, mapping)
- [ ] Implement spell power scaling with caster skill level
- [ ] Implement spell failure / backfire (low Oratory skill, except Alchemy)
- [ ] Implement Alchemy's immunity to Silence
- [ ] Implement spell point costs and regeneration
- [ ] Implement mana recovery rate (determined by base class at creation)

### 3.5 Item & Inventory System
- [ ] Implement equipment slots (weapon, shield, head, torso, legs, feet, hands, accessory)
- [ ] Implement equip restrictions (class, race, sex, stat requirements)
- [ ] Implement cursed item mechanics (cannot unequip without Remove Curse)
- [ ] Implement item identification (Identify spell / Legerdemain skill)
- [ ] Implement usable items (potions, scrolls, wands)
- [ ] Implement quest items and key items
- [ ] Implement item weight and carrying capacity
- [ ] Implement party gold pool
- [ ] Implement merchant buy/sell with price calculations

### 3.6 World & Exploration
- [ ] Implement grid-based movement (forward, back, strafe left/right, turn left/right)
- [ ] Implement wall collision detection
- [ ] Implement door interaction (open, locked, key required, bashed)
- [ ] Implement secret door detection (Scouting skill check)
- [ ] Implement special tile effects
  - Stairs up/down (level transitions)
  - Teleporters
  - Spinners (silently rotate player facing)
  - Dark zones (no light spell = blind)
  - Anti-magic zones
  - Damage floors (lava, poison)
  - One-way walls
- [ ] Implement random encounter system (per-tile probability)
- [ ] Implement fixed encounters and event triggers
- [ ] Implement NPC dialogue system
  - Text display with choices
  - Keyword-based conversation
  - Trade/shop interactions
  - Quest-giving and quest-completion checks
- [ ] Implement trap detection and disarming (chest traps, floor traps)

### 3.7 Game Progression
- [ ] Implement quest flag system (global state booleans/counters)
- [ ] Implement key story events and branching paths
- [ ] Implement the three endings (tied to Cosmic Forge pen choices)
- [ ] Implement party export for Wizardry 7 import (.BCF file generation)

---

## Phase 4 — User Interface Screens

**Goal:** Build all game screens faithful to the original, with optional modern enhancements.

### 4.1 Title Screen & Main Menu
- [ ] Title artwork display
- [ ] New Game / Continue / Load / Options / Quit

### 4.2 Character Creation
- [ ] Race selection with stat previews
- [ ] Class selection with requirement validation
- [ ] Stat rolling and point allocation
- [ ] Portrait selection
- [ ] Name entry
- [ ] Party composition screen (add/remove/reorder 6 characters)

### 4.3 Exploration HUD
- [ ] First-person 3D viewport (center of screen)
- [ ] Compass / facing indicator
- [ ] Party status bar (HP/SP per character, conditions)
- [ ] Message log / text area
- [ ] Quick-action buttons (camp, automap, formation)
- [ ] Minimap overlay (optional modern enhancement)

### 4.4 Combat Screen
- [ ] Monster group display with sprites
- [ ] Per-character action selection
  - Attack (choose target group)
  - Cast spell (school → level → spell → target)
  - Use item
  - Defend
  - Flee
  - Hide (Thief/Ninja)
- [ ] Combat log with damage/effect messages
- [ ] Monster HP indicators (optional enhancement)
- [ ] Turn order display (optional enhancement)

### 4.5 Character Sheet
- [ ] Stats display (7 core attributes)
- [ ] Skills list with levels
- [ ] Equipment slots (visual paper doll or list)
- [ ] Inventory grid (12 slots)
- [ ] Spell book access
- [ ] Class change interface

### 4.6 Spell Book
- [ ] Spell school tabs
- [ ] Spell list per level
- [ ] Spell descriptions and costs
- [ ] Castable vs. known indicators

### 4.7 Automap
- [ ] 2D top-down map of explored tiles
- [ ] Current position and facing indicator
- [ ] Level selection
- [ ] Points of interest markers (stairs, NPCs, shops)
- [ ] Fog of war for unexplored areas

### 4.8 Camp / Rest Screen
- [ ] Rest options (short rest, full rest, guard duty)
- [ ] Ambush encounter possibility during rest
- [ ] Spell memorization during rest
- [ ] HP/SP recovery

### 4.9 Merchant / Shop
- [ ] Buy/sell item lists
- [ ] Price display with haggle modifiers
- [ ] Item inspection before purchase
- [ ] Identify services

---

## Phase 5 — Polish, QA & Extended Features

**Goal:** Bring the engine to release quality.

### 5.1 Save/Load System
- [ ] Read original SAVEGAME.DBS + PCFILE.DBS files (backward compatibility)
- [ ] Write new save format (JSON or custom binary) for engine-native saves
- [ ] Multiple save slots
- [ ] Quick save / quick load

### 5.2 Quality of Life Enhancements
- [ ] Automap (the original game had no built-in map)
- [ ] Configurable movement speed (instant step vs. animated walk)
- [ ] Text speed control
- [ ] Combat speed control (fast/normal/slow)
- [ ] Item sort and filter in inventory
- [ ] Spell favorites / quick-cast
- [ ] Keyboard shortcuts for common actions
- [ ] Controller / gamepad support
- [ ] Fullscreen / windowed toggle
- [ ] Resolution scaling (integer scaling for pixel-perfect, or smooth upscale)

### 5.3 Mod Support
- [ ] Asset override system (drop replacement PNG/OGG files into `mods/` folder)
- [ ] Lua scripting hooks for event customization
- [ ] Custom palette / shader support
- [ ] Data override files (JSON patches for monster/item/spell stats)

### 5.4 Debug & Development Tools
- [ ] ImGui debug overlay (toggle with F12)
  - Monster stat inspector
  - Item database browser
  - Map editor (view/edit tiles)
  - Teleport to any location
  - Give items / set flags
  - Party stat editor
- [ ] Console command system
- [ ] Frame rate / performance overlay
- [ ] Log output system (file + console)

### 5.5 Testing & Validation
- [ ] Unit tests for all parsers (verify against known data)
- [ ] Unit tests for combat calculations (verify against known formulas)
- [ ] Integration tests (load real game data, verify no crashes)
- [ ] Playtest: complete full game walkthrough verifying all encounters, events, and endings
- [ ] Compatibility testing across Windows, macOS, Linux

---

## Phase 6 — Stretch Goals

These are aspirational features beyond core parity:

- [ ] **Enhanced Graphics Mode** — HD sprite replacements, higher-res textures, lighting effects
- [ ] **3D Dungeon Mode** — True 3D rendering of dungeon geometry (walls as 3D meshes)
- [ ] **Music Pack Support** — Load custom soundtrack (OGG/MP3) for each dungeon level
- [ ] **Wizardry 7 Data Compatibility** — Extend parsers to load Crusaders of the Dark Savant data
- [ ] **Wizardry 8 Data Compatibility** — Extend parsers to load Wizardry 8 `.SLF` archives
- [ ] **Multiplayer Spectator Mode** — Stream game state for co-op decision making
- [ ] **Accessibility** — Screen reader support, colorblind palettes, remappable everything
- [ ] **Mobile Port** — Touch controls, responsive UI layout for tablets

---

## Key Technical Challenges

### 1. Reverse Engineering SCENARIO.DBS
The biggest risk. This single file contains monsters, items, maps, events, spells, and more in an undocumented binary format. Strategy:
- Use the Cosmic Forge Editor as a reference (it can read/write this file)
- Use the Wizardry-6-API (.NET library) for save game format reference
- Binary diff approach: make small in-game changes, compare save files
- Cross-reference parsed values against community wikis and FAQs

### 2. EGA Sprite Extraction
Sprites are packed in a proprietary format within the data files. Strategy:
- Study EGA planar format (4 planes × 1 bit = 16 colors per pixel)
- Use ripped sprites from The Spriters Resource as ground truth
- Match extracted sprites against known screenshots pixel-by-pixel

### 3. Map Event Scripting
The original game has complex scripted events (NPC conversations with branching, puzzle sequences, multi-step quests). These may be encoded as bytecode in SCENARIO.DBS. Strategy:
- Identify the event bytecode format through pattern analysis
- Document each opcode's behavior
- Implement a bytecode interpreter or transpile to Lua

### 4. Combat Formula Accuracy
Wizardry 6 has nuanced combat math that differs from documentation in subtle ways. Strategy:
- Reference GOG forum reverse-engineering posts on combat calculations
- Implement formulas, then validate by running parallel combat in DOSBox and the engine
- A/B testing: same party, same encounter, compare outcomes statistically

---

## Reference Resources

| Resource | URL / Location |
|----------|---------------|
| Cosmic Forge Editor | https://mad-god.webs.com/cosmicforge.htm |
| Wizardry-6-API (GitHub) | https://github.com/dsx75/Wizardry-6-API |
| Spriters Resource (Wiz6) | https://www.spriters-resource.com/ms_dos/wizardryvibaneofthecosmicforge/ |
| Wizardry Legacy - Maze Data | http://wl.lariennalibrary.com/index.php?n=Development.DVmazedata |
| PCGamingWiki | https://www.pcgamingwiki.com/wiki/Wizardry:_Bane_of_the_Cosmic_Forge |
| Combat Calculations (GOG) | https://www.gog.com/forum/wizardry_series/wizardry_6_combat_calculations |
| Sorcery (Wiz1 remake, C++) | https://github.com/davemoore22/sorcery |
| Internet Archive (Wiz6) | https://archive.org/details/Wizardry_6_Bane_of_the_Cosmic_Forge |
| Wiz6 in Wiz7 Engine Remaster | https://rpghq.org/forums/viewtopic.php?t=3170 |

---

## Development Milestones

| Milestone | Target | Description |
|-----------|--------|-------------|
| M0 | Phase 1.1–1.2 | Project builds, binary reader works, dbs_dumper runs |
| M1 | Phase 1.3–1.6 | All data files parseable, sprite viewer shows monsters |
| M2 | Phase 2 | Engine runs, renders a dungeon level, accepts movement input |
| M3 | Phase 3.1–3.2 | Character creation works, skills and stats functional |
| M4 | Phase 3.3–3.4 | Combat and magic fully playable |
| M5 | Phase 3.5–3.7 | Items, exploration, quests — game is completable |
| M6 | Phase 4 | All UI screens polished and complete |
| M7 | Phase 5 | Save/load, QoL, mod support, testing done |
| **v1.0** | All phases | Full game playable start to finish with all 3 endings |

---

## Legal Considerations

- This engine is a **clean-room reimplementation** — no original Wizardry 6 source code is used
- Users must provide their own copy of the original Wizardry 6 data files (purchasable on GOG/Steam)
- The engine reads the original data files at runtime, similar to OpenMW (Morrowind) or OpenEnroth (Might & Magic)
- No copyrighted assets are distributed with the engine
- The project should include clear documentation that original game files are required
