# Project Context: dark_rpg

Orientation snapshot for agents/humans. Conventions → [AGENTS.md](AGENTS.md). Player-facing docs → [README.md](README.md). Counts that rot (tests, events, enemies) are deliberately not hard-coded here — run the commands below.

## Overview
Terminal turn-based dungeon-crawl RPG, pure Python (stdlib only at runtime). 10 floors, scaled enemies with special abilities, rarity-based gear, consumables, plugin room events, a re-scaled final boss. Two swappable combat modes: **stamina** (simultaneous, hidden intent) and **posture** (intent revealed first; deflect/break mechanics).

**Long-term goal:** explore a deflection-centric combat system (Sekiro × Dark Souls, turn-based first) and learn the limits of terminal games. See "Deflection" in AGENTS.md.

## Stack
- Python ≥ 3.10 (CI matrix 3.10–3.13); setuptools ≥ 77 build; `uv` for dev env
- Dev deps (dependency group `dev`): pytest, ruff, mypy
- No runtime dependencies, no services, no `.env`

## Structure
```
src/dark_rpg/   app.py (Game loop) · combat/ (base, stamina, posture) · world/ (enemies, rooms, events/*)
                entities.py · status.py · gear.py · io.py (GameIO, timed input) · ui.py · art.py
                config.py · paths.py · save.py · registry.py · testing.py (FakeIO, StubRng, policies)
config.json     all tuning; src/dark_rpg/config.json is a symlink to it (wheel ships it)
tests/          headless pytest + e2e
scripts/        simulate.py (balance) · playthrough.py (transcripts → logs/, gitignored *.log)
docs/           DESIGN · COMBAT · TESTING · ROADMAP · EXPERIENCE_REVIEW
legacy/         archived prototypes (not imported)
```

## Commands
```sh
uv sync --dev
uv run pytest
uv run ruff check src tests scripts      # E/F baseline
uv run mypy                              # clean as of 2026-10-04
uv run python scripts/simulate.py --runs 200 --policy smart --all-modes
python run.py | dark-rpg [--combat-mode posture] [--list-modes] [--list-events]
```
CI (`.github/workflows/ci.yml`): lint job (ruff + mypy) and test job (pytest, 50-run simulation smoke, wheel build + config.json-in-wheel check).

## Key architecture
- **Plugins**: `PluginRegistry`; `@register_combat_mode` (`CombatMode` strategy, chosen by `game.combat_mode`), `@register_event` (`RoomEvent`, dispatched by `room_weights`).
- **Headless by design**: all I/O via `GameIO`, all randomness via injected `random.Random` ⇒ deterministic, simulatable.
- **Gear replaces per slot** (never stacks) to cap late-game power.
- **Status effects** shared by both modes (`tick_statuses`); **enemy abilities** data-driven (`crit_amplify`, `apply_post_hit`).
- **Scars**: combat death → max HP −N, revive at half HP; past `scar_limit` = game over.
- **Saves**: atomic, validated; corrupt ⇒ fresh game. Path: `~/.config/dark_rpg/save.json` (`--save`, `$DARK_RPG_SAVE`); config lookup order in `paths.py`.
- **Turn timer**: `io.timed_input` (thread around `input()`); Enter-based, not suited to real-time play.

## Balance baseline (smart policy, `simulate.py`)
≈ 35% win (stamina) / ≈ 77% (posture). Re-measure after any combat/config change.

## Open questions / next
- Deflection mode design (third `CombatMode`; may require multi-phase `resolve`).
- Roadmap ideas in docs/ROADMAP.md (boss telegraphs, story spine, branching map, meta-progression, stat system).
- Difficulty tuning intentionally deferred (60 s turn timer kept).
- `legacy/` deletable once the package is judged stable.
- Not yet adopted from agentnet: Makefile (`make check`), pre-commit, coverage gate.
