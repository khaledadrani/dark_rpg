# dark_rpg — a terminal dungeon-crawl text RPG

A config-driven, plugin-based dungeon crawler written in **pure Python
(stdlib only)**.  Descend 10 floors, fight **12 scaled enemies** — several
with special abilities — equip **rarity-based gear**, manage food and gold,
survive **11 different room events**, and face the re-scaled **Dungeon
Tyrant**.  It's a roguelite loop with a feedback you can read: every hit is
numbered, every choice is visible, and your run ends with a recap.

```
   ╔══════════════════════════════════════╗
   ║         D U N G E O N  R U N        ║
   ║    A text RPG with a feedback loop   ║
   ╚══════════════════════════════════════╝
```

## Install & play anywhere

**Install globally with `uv` (recommended).** `uv tool` keeps the game in its
own isolated venv and puts a `dark-rpg` command on your `PATH`, so you can
launch it from any directory:

```bash
uv tool install dark-rpg          # from PyPI, once published
# or, from a local checkout:
uv tool install .
```

Then just run:

```bash
dark-rpg
```

Your save lives in **`~/.config/dark_rpg/save.json`** — not in the current
folder — so a run started in one place continues from anywhere, every time.
On Windows it's `%APPDATA%\dark_rpg\`. (Honors `XDG_CONFIG_HOME` if set.)

### Other ways to run

```bash
# run a local checkout without installing (pure stdlib)
python run.py

# install into your normal environment
pip install -e .

# pick a combat mode / seed / save location
dark-rpg --combat-mode posture --seed 42 --save /tmp/myrun.json

# list registered plugins
dark-rpg --list-modes
dark-rpg --list-events
```

### Where config and saves live

* **Save file** — `~/.config/dark_rpg/save.json` by default. Override with
  `--save PATH` or the `DARK_RPG_SAVE` env var; pass `--save None` to disable.
* **Config** — loaded in this order: a personal `~/.config/dark_rpg/config.json`
  (if you made one) → the `config.json` shipped inside the package →
  `./config.json` in a dev checkout. To customize the game permanently, copy
  the default once and edit it:

  ```bash
  mkdir -p ~/.config/dark_rpg
  cp config.json ~/.config/dark_rpg/config.json   # from the repo
  ```

  Every subsequent `dark-rpg` run picks it up automatically.

## Two swappable combat systems

| Mode | Key | Style |
|---|---|---|
| Classic stamina combat | `stamina` | Stamina gates actions; exhaustion forces a recovery turn; combo chains build damage. |
| Posture combat | `posture` | Read-the-enemy: the enemy's intent is revealed before you act; posture drains on hits received; broken = amplified damage + forced recovery. |

Both modes share **status effects** (burn / poison damage-over-time), a
`[u] Use item` action for consumables (potion heal, oil burn, poison vial),
and **enemy special abilities**:

* **Assassin** — can land a critical (2x) strike.
* **Vampire** — drains HP for each hit it lands.
* **Wraith** — drains your stamina/posture on hit.
* **Lich** — resurrects once at 40% HP.
* **Cave Spider** — poisons you on hit.

## What you'll find in the dungeon

**Equipment (gear)** — loot is not a pile of ever-growing bonuses.  It's gear
that goes into **weapon / armor / trinket slots** and *replaces* whatever you
were wearing, across **common / uncommon / rare / epic** rarities.  That means
every find is a real decision (does this beat what I've got?) and your stats
can't snowball into making the boss a joke.

**Room events (11)** — each floor is a mix of:

* `enemy` — a scaled fight
* `loot` — a gear find
* `rest` — heal + food
* `trap` — take damage
* `merchant` — potions, rations, oil, poison, sharpen stone, bracer
* `shrine` — a gamble for a blessing
* `vault` — a bigger haul, sometimes guarded
* `curse` — a DoT altar (or a disarmed blessing)
* `ambush` — a surprise strike before the duel
* `gamble` — a coin-flip that can double or lose your gold
* `secret` — a hidden passage with food + gold (and a dart)

**Surprises & reactions** — 25 room flavor lines, per-enemy animated ASCII
art, a `RUN RECAP` screen at the end of every run (outcome, level, fights,
deaths, rooms, gold), and ANSI-coloured HP/stamina bars on a real terminal
(green HP, cyan stamina, red when you're broken).

## Configuration

Everything that affects gameplay lives in `config.json` — no magic numbers in
code.  Highlights:

* `game.combat_mode` — `"stamina"` or `"posture"`
* `game.turn_timer` — per-turn countdown (`enabled`, `seconds`)
* `ui.slow_print_delay` — typewriter speed (**auto-disabled when piped**)
* `ui.ascii_art` / `ui.art_frame_delay` — ASCII art toggle + animation speed
* `ui.ansi_color` — colour toggle (auto-off when stdout is not a TTY)
* `game.xp_per_level`, `level_hp`, `level_atk` — progression curve
* `game.scar_penalty`, `scar_limit` — death penalty tuning
* `game.floor_scale`, `tier_scale` — enemy growth per floor
* `game.hunger_damage` — food pressure
* `enemies[]` / `boss` — stats, XP, gold, AI weights, and optional
  `ability` / `status_on_hit` per enemy
* `stamina{}` / `posture{}` — the two combat modes' tuning
* `status_effects[]` — burn / poison / regen definitions
* `gear_slots` / `rarity` — equipment tuning
* `loot_table`, `shop`, `room_weights`, `room_flavors` — content

## Plugin systems

The game is built on two registries (see `docs/DESIGN.md`):

* **Combat modes** — subclass `CombatMode`, decorate with
  `@register_combat_mode`, select via config.
* **Room events** — subclass `RoomEvent`, decorate with `@register_event`,
  add a weight in `config.json`.

Content (enemies, loot, shop, status effects, gear) is **data-driven** —
adding a new enemy, item, or status effect never requires code changes.

## Run the tests

```bash
python -m pytest                                   # 107 unit + headless E2E tests
python scripts/simulate.py --runs 200 --policy smart --all-modes   # balance sim
python scripts/playthrough.py --mode posture --policy smart --seed 5  # transcript
```

## Project layout

```
dark_rpg/
├── pyproject.toml          # package metadata, dark-rpg console script
├── run.py                  # run without installing
├── config.json             # ALL game tuning (enemies, gear, statuses, events)
├── LICENSE                 # MIT
├── logs/                   # sample playthrough transcripts
├── src/dark_rpg/
│   ├── cli.py / __main__.py
│   ├── app.py              # Game orchestration (floors, rooms, combat, boss, recap)
│   ├── art.py              # animated ASCII art (scenery + enemies)
│   ├── config.py           # validated config loading
│   ├── io.py               # IO abstraction (headless-testable, TTY-aware colour)
│   ├── ui.py               # pure display helpers (bars, articles, ANSI codes)
│   ├── registry.py         # the plugin registry (design pattern core)
│   ├── entities.py         # Entity + Player (gear, consumables, abilities)
│   ├── gear.py             # equipment slot / rarity helpers
│   ├── status.py           # StatusEffect + tick_statuses (burn/poison/regen)
│   ├── save.py             # atomic, validated save/load
│   ├── testing.py          # simulation & test tooling (FakeIO, StubRng, policies)
│   ├── combat/             # combat-mode plugins (strategy pattern)
│   │   ├── base.py         #   CombatMode interface (+ shared "use item")
│   │   ├── stamina.py      #   classic stamina combat
│   │   └── posture.py      #   posture / read-the-enemy combat
│   └── world/
│       ├── enemies.py      # enemy selection + floor scaling
│       ├── rooms.py        # room resolution
│       └── events/         # room-event plugins (11 events)
├── tests/                  # unit + E2E tests (107)
├── scripts/                # simulate.py (balance), playthrough.py (transcripts)
├── docs/                   # DESIGN, COMBAT, TESTING, ROADMAP, EXPERIENCE_REVIEW
└── legacy/                 # archived one-file prototypes (rpg.py, rpg2.py, duel.py)
```

## License

MIT — see [LICENSE](LICENSE).
