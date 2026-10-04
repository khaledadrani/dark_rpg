# Testing

```
python -m pytest            # everything (93 tests)
python -m pytest tests/test_combat_stamina.py -v
python scripts/simulate.py --runs 500 --policy smart --all-modes
python scripts/playthrough.py --mode posture --policy smart --seed 5   # transcript log
```

## Test layers

| Layer | Files | What it proves |
|---|---|---|
| Unit — config | `test_config.py` | config loads, validates, fails loudly; every registered mode is instantiable |
| Unit — entities | `test_entities.py` | player init, level-ups, food/hunger, save roundtrips |
| Unit — save | `test_save.py` | atomic writes, corruption detection |
| Unit — stamina combat | `test_combat_stamina.py` | exhaustion semantics, forced recovery, combo, defend halving |
| Unit — posture combat | `test_combat_posture.py` | deflect/dodge, broken recovery + amplification, defend |
| Unit — registry | `test_combat_registry.py` | plugin registration, unknown-key errors |
| Unit — events | `test_events.py` | loot/trap/rest/merchant/shrine logic |
| Unit — scars & key | `test_scars_key.py` | scar death spiral, scar cap, key guarantee |
| Unit — ASCII art | `test_art.py` | registry coverage (every event/enemy/boss), config toggle, headless-safe static vs animated paths, article helper |
| E2E — full game | `test_e2e.py` | full headless runs under both modes, invariants, save/continue, starvation, reproducibility |
| E2E — simulation | `test_simulation.py` (inside `test_e2e.py`) | simulation guard-rails |

## Headless machinery (`src/dark_rpg/testing.py`)

* `StubRng` — fixed-value RNG (`randint` clamped to bounds) for scripted
  scenarios ("always hit", "always lose the flee roll").
* `FakeIO` — answers prompts from a queue, per-kind defaults, or a policy
  callable; records every prompt and printed line.  An unexpected prompt
  with no answer fails the test loudly.
* `make_game(cfg, ...)` — a ready headless `Game`.
* Policies: `attack_policy`, `random_policy`, `smart_policy`.
* `run_simulation(cfg, combat_mode, policy, runs, seed_base)` — plays N
  seeded full games and aggregates win rate, floors, deaths, etc.

## Determinism

The game draws all randomness from an injected `random.Random`.  Same seed +
same policy ⇒ identical `GameResult` (asserted in `test_e2e.py`).  The
simulation uses `seed_base + i` per run, so any reported table is
reproducible.

## E2E invariants checked on every full run

* outcome ∈ {win, dead}; floors cleared within [0, floor_count]
* `deaths == scars` (every scar came from a combat death)
* scars ≤ `scar_limit + 1`; level ≥ 1; HP never negative (clamped)

## Balance simulation results (seed 0, 1000 runs, current `config.json`)

```
policy   stamina   posture
smart     35.3%     82.4%
attack    19.7%     43.3%
random    18.8%     24.6%
```

Reading: a modestly smart player wins about a third of classic-mode runs —
challenging but very winnable — and most posture-mode runs (the intended
"easier, skill-based" mode).  Dumb/random play clearly loses more: skill
matters in both modes.

### What the simulation taught us (balance fixes applied)

1. **The game was unwinnable.** Original tuning: smart-policy win rate 0%,
   average floors cleared ~1.2–1.8 out of 10; even the human author's old
   save showed floor 1, 2 scars, max HP 15.  Rebalanced player start
   (30 HP / 5 ATK / 2 DEF / 15 food), scar penalty (−3 instead of −5),
   enemy HP, boss (100/15/8), floor scaling, XP curve, and heavy weights.
2. **Hunger was the biggest damage source** (2 HP per room, no food)
   — softened to configurable `hunger_damage` (1) with more starting food.
3. **Stamina defend (`defense * 2`) did nothing** against 20+ heavy hits —
   changed to halve incoming damage.
4. **Blind stamina combat had no decisions** — attack-spam was optimal
   (smart ≈ attack ≈ random).  Added read-the-enemy intent reveal to both
   modes.
5. **Fleeing at low HP is a death trap** in stamina mode (simulation: any
   flee policy lost ~5x more).  The smart policy no longer flees; the flee
   parting blow is capped so retreat never kills outright.
6. **Posture deflect-spam was trivially +EV** — deflect cost 1→2, drain
   4/7→3/5, broken multiplier 1.75→1.5.

## Adding a test

* Combat mechanic → add to `tests/test_combat_stamina.py` or
  `tests/test_combat_posture.py` using `StubRng` to force outcomes.
* Event → `tests/test_events.py` with `make_game(...)` + scripted answers.
* Full-run behavior → `tests/test_e2e.py` with a seeded `make_game` and a
  policy; assert `GameResult` invariants.
* Balance → run `scripts/simulate.py`; record new numbers here if the
  default config changed.
