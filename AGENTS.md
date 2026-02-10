# Repository Guidelines

## Project Structure & Module Organization
- `bane/`: Core engine package.
- `bane/engine/`, `bane/game/`, `bane/ui/`, `bane/world/`: Runtime subsystems.
- `bane/data/`: Built-in data helpers (not the original game assets).
- `tools/`: Command-line utilities (`dbs_dumper.py`, `sprite_viewer.py`, `map_viewer.py`).
- `tests/`: Pytest suite for engine and data loaders.
- `gamedata/`: Local Wizardry VI assets (ignored by git; provide your own).

## Build, Test, and Development Commands
- `python -m pip install -e .[dev]`: Install editable package with dev tools.
- `python -m bane --gamedata gamedata`: Run the engine with local assets.
- `bane-dump --gamedata gamedata`: Dump DBS data (see `tools.dbs_dumper`).
- `bane-sprites --gamedata gamedata`: Inspect sprite decoding output.
- `bane-map --gamedata gamedata`: Launch the map viewer.
- `python -m pytest`: Run the full test suite.
- `python -m ruff check .`: Lint Python sources.
- `python -m mypy bane`: Type-check the core package.

## Coding Style & Naming Conventions
- Python 3.11 codebase; type hints are required (`disallow_untyped_defs = true`).
- Ruff enforces linting and import order; keep line length at 100.
- Use `snake_case` for functions/variables, `PascalCase` for classes, and
  `UPPER_SNAKE_CASE` for constants.
- Prefer small, focused modules in `bane/engine` and `bane/game`.

## Testing Guidelines
- Framework: `pytest` with tests in `tests/`.
- Name tests `test_*.py` and keep test functions prefixed with `test_`.
- Add regression tests near the affected subsystem (e.g., map parsing tests
  alongside other loader tests).
- When touching parsing/decoding logic, add cases covering malformed input.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and sentence case (e.g., “Add map loader
  validations”).
- PRs should include:
  - A concise summary of behavior changes.
  - Linked issue or plan reference when applicable.
  - Screenshots/GIFs for UI or rendering changes.

## Security & Configuration Tips
- Do not commit proprietary game assets; keep them in `gamedata/`.
- Avoid checking in large binary dumps; store derived artifacts in `tools/` output
  directories ignored by git if needed.
