# Project Context: dark_rpg

## Overview
A terminal-based dungeon-crawl text RPG written in pure Python (stdlib only).
The player descends 10 floors, fights 12 scaled enemies (several with special
abilities), equips rarity-based gear, manages food/gold/consumables, triggers
11 different room events, and faces a re-scaled final boss.  Two **swappable
combat modes** exist: classic stamina combat and posture (read-the-enemy)
combat.

## Stack
- **Language / Runtime**: Python 3.10+ (tested on 3.13)
- **Package Manager / Runner**: none required for the game (stdlib only);
  `pytest` (dev) for tests; `pip install -e .` optional for the `dark-rpg`
  console script
- **Framework(s)**: none — plugin registries + strategy pattern
- **Infrastructure / DevOps**: none (local scripts only)
- **Testing**: `pytest` — 107 tests (unit + headless end-to-end + new
  feature tests) + `scripts/simulate.py` balance simulation

## Project Structure
```
dark_rpg/
├── pyproject.toml            # package metadata, dark-rpg script, pytest config
├── run.py                    # run without installing: python run.py
├── README.md                 # quickstart + structure
├── config.json               # ALL game tuning (combat modes, enemies, loot, weights)
├── src/dark_rpg/             # the standardized package
│   ├── cli.py / __main__.py  # entry points (python -m dark_rpg)
│   ├── app.py                # Game orchestration (floors/rooms/combat/boss)
│   ├── art.py                # animated ASCII art (scenery + enemies, ui.ascii_art)
│   ├── config.py / io.py / ui.py / registry.py / entities.py / save.py
│   ├── testing.py            # FakeIO, StubRng, policies, run_simulation
│   ├── combat/               # plugin combat modes: base, stamina, posture
│   └── world/                # enemies, rooms, events/ (6 event plugins)
├── tests/                    # unit + E2E tests (94)
├── logs/                      # playthrough transcripts
├── art.py                     # animated ASCII art (scenery/enemies)
├── scripts/                  # simulate.py (balance) + playthrough.py (logs)
├── docs/                     # DESIGN, COMBAT, TESTING, ROADMAP
└── legacy/                   # archived rpg.py, rpg2.py, duel.py, old tests
```

## Entrypoints
- `dark-rpg` (installed via `uv tool install .` or `pip install -e .`) — play anywhere
- `python run.py` / `python -m dark_rpg` — play from a checkout without installing
- `dark-rpg --combat-mode posture` — switch combat mode
- `dark-rpg --list-modes` / `--list-events` — list plugins
- `python -m pytest` — run all tests (116)
- `python scripts/simulate.py --runs 500 --policy smart --all-modes` — balance simulation
- `python scripts/playthrough.py --mode posture --policy smart --seed 5` — transcript log

## Install / run-anywhere (uv tool)
- Installed as a `uv tool` → `dark-rpg` on PATH; works from any directory.
- **Save file**: `~/.config/dark_rpg/save.json` (overridable with `--save` or
  `$DARK_RPG_SAVE`; `--save None` disables). Windows: `%APPDATA%\dark_rpg\`.
- **Config**: personal `~/.config/dark_rpg/config.json` → packaged
  `config.json` (shipped in the wheel via `package-data`) → `./config.json`
  (dev checkout). All location logic in `src/dark_rpg/paths.py`.
- `config.json` is symlinked into `src/dark_rpg/` so the wheel always ships a
  copy without drift from the root file.

## Key Architecture
- **Combat modes as plugins**: `CombatMode` interface (strategy pattern);
  `@register_combat_mode`; selected by `config.json -> game.combat_mode`
  ("stamina" | "posture").  Both modes reveal enemy intent before the turn.
- **Room events as plugins**: `RoomEvent` + `@register_event`; dispatched by
  `config.room_weights`.  Events: enemy, loot, rest, trap, merchant, shrine,
  vault, curse, ambush, gamble, secret (11 total).
- **Gear system**: `Player.equip(item)` puts an item into a slot
  (`gear[slot]`) or adds a flat accessory bonus.  Loot *replaces* the slot —
  it never stacks, which keeps late-game stats in check.
  `effective_atk` / `effective_defense` are properties that add gear bonuses.
- **Status effects**: `StatusEffect` dataclass + `tick_statuses()` shared by
  both combat modes.  Burn / poison (DoT), regen (HoT).  Applied via
  `apply_status()` (stronger effect wins on re-apply).
- **Enemy abilities**: `crit_amplify()` + `apply_post_hit()` in
  `dark_rpg.entities`.  Data-driven from each enemy's `ability` /
  `status_on_hit` fields.  The player's template is `{}` (no abilities).
- **Consumables in combat**: `[u] Use item` action in both modes (base
  `CombatMode._use_item`) — potion heal, oil burn, poison vial, rations.
- **IO abstraction**: all interaction via `GameIO` (headless-testable);
  `Prompt(kind, text, state)` lets test policies make informed decisions.
- **Determinism**: injected `random.Random`; same seed ⇒ same run.
- **Exhaustion (stamina)**: hitting 0 stamina → forced weak_block recovery
  turn next turn; stamina restores at END of recovery; symmetric for enemies.
- **Broken (posture)**: 0 posture → broken; amplified damage (1.5x) while
  broken incl. the recovery turn; recovery clears broken at end of turn.
- **Defend** halves incoming damage (both modes); weak_block halves too.
- **Flee** never kills outright (parting blow capped at 1 HP).
- **Scars**: combat death → max HP −3 (config), revive at half HP; >6 scars
  (`scar_limit`) = permanent game over.
- **Save**: atomic (`.tmp` + replace), validated on load; corrupt saves
  degrade to a fresh game with a clear message.
- **Balance**: simulation-verified (see docs/TESTING.md); smart-policy win
  rate ~36% (stamina) / ~77% (posture); attack-spam/random clearly lower.
  The boss is a real fight (130 HP / ATK 17) and the gear system caps
  late-game stats so the player doesn't out-scale the finale.
- **ASCII art**: scenery (per room event) + enemies (per name) + boss,
  animated on TTYs, static when piped, toggle via `ui.ascii_art`.
- **ANSI colour**: HP/STA/PST bars tinted, broken-state flashes red, only on
  an interactive TTY (piped logs stay clean), toggle `ui.ansi_color`.
- **Run recap**: a RUN RECAP block (outcome, level, fights, deaths, rooms,
  gold) prints at the end of every run (win or death).
- **Playthrough logs**: `scripts/playthrough.py` writes full transcripts to
  `logs/`; evaluated in `docs/EXPERIENCE_REVIEW.md`.

## Environment
- Config: `config.json` (game params), `save.json` (runtime save, gitignored)
- No `.env` or external services; no dependencies outside Python stdlib

## Open Questions / Next Steps
- Difficulty tuning is intentionally deferred by the user (60s timer kept as
  configured; further tuning in `config.json`)
- `docs/ROADMAP.md` lists the remaining fun upgrades (boss telegraphs,
  merchant rerolls, per-enemy kill lines, story spine, branching map,
  meta-progression, stat system)
- Old prototypes archived in `legacy/` — safe to delete once the package is
  proven stable
