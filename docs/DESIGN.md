# Design

## Goals

1. **Fun = meaningful decisions.** Every combat turn should present a
   readable choice, not a blind coin-flip.
2. **Everything as a plugin.** Combat systems and room events are swappable
   without touching core dispatch.  Content is data, behavior is registry.
3. **Testable.** The entire game runs headless with injected IO and seeded
   RNG; balance is verified by simulation, not vibes.
4. **Config-driven tuning.** No magic numbers in code — `config.json` owns
   balance so difficulty can be tuned without code changes.

## Architecture

```
cli.py ──> Game (app.py) ──> world/rooms.py ──> world/events/* (plugins)
   │            │  │
   │            │  └─> combat/* (plugins, selected by config game.combat_mode)
   │            └──> entities.py, save.py, io.py, ui.py
   └─> config.py (validated JSON)
```

### The `Game` object

`Game` owns config, IO, RNG, combat mode and run statistics.  Everything the
game does goes through `game.cfg`, `game.io`, `game.rng`.  Tests construct a
`Game` with a `FakeIO` + seeded RNG and drive it headless.

### IO abstraction (the key to testability)

`GameIO` wraps every interaction: `ask(prompt)`, `out()`, `slow_out()`,
`pause()`, `clear()`, `timed_input()`.  A `Prompt` carries a `kind`
(what's being asked) and `state` (game context), so test policies can make
informed decisions.  `FakeIO` answers from a scripted queue, defaults, or a
policy callable.  The real terminal path is just one implementation.

### Plugin registries

`PluginRegistry` is a tiny generic key→item map with duplicate-key
protection and helpful errors.

* `dark_rpg.combat.COMBAT_MODES` — combat engine classes, registered via
  `@register_combat_mode`, instantiated per-game with config.
* `dark_rpg.world.events.EVENTS` — room event instances, registered via
  `@register_event`, dispatched by id from `config.room_weights`.

### ASCII art (atmosphere, headless-safe)

`dark_rpg.art` holds every picture as a *list of frames*.  `play_art(io,
frames)` decides at runtime:

* `io.ascii_art == False` → nothing (config `ui.ascii_art` off)
* non-interactive (pipe/file) or a single frame → static first frame
* interactive terminal → frames cycle in place via ANSI cursor-up escapes

Art never consumes RNG and never blocks on input, so transcripts and
simulations stay deterministic.  Scenery is keyed by room-event id (the room
picks its event before printing, so the art matches the room); enemies are
keyed by name with graceful fallbacks.

To add a combat mode:

```python
from dark_rpg.combat import register_combat_mode
from dark_rpg.combat.base import CombatMode

@register_combat_mode
class MyCombat(CombatMode):
    key = "my_combat"
    name = "My combat"
    config_key = "my_combat"
    # ... implement max_stamina / start_combat / action_menu / forced_action /
    #     pick_enemy_action / reveal_intent / resolve / hud / flee_fail
```

Then `config.json -> game.combat_mode = "my_combat"`.

To add a room event:

```python
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent

@register_event
class MyEvent(RoomEvent):
    id = "my_event"
    def run(self, game, player, room_num): ...
```

Then add `"my_event": <weight>` to `config.room_weights`.

### Design patterns used

| Pattern | Where |
|---|---|
| Strategy | `CombatMode` interface; the game loop only calls the interface |
| Plugin / Registry | combat modes and room events via `PluginRegistry` + decorators |
| Factory | `make_combatant` builds scaled enemies; `get_combat_mode` instantiates modes |
| Abstraction / Dependency injection | `GameIO`, RNG, and `save_path` injected into `Game` |
| Validation | config and save files validated at load time with clear errors |
| Atomic write | saves go through a `.tmp` file + `os.replace` |

## Key decisions (and why)

### Exhaustion forces a recovery turn (stamina mode)

The old code restored stamina *and cleared exhaustion at the start* of the
next turn, so the enemy effectively never paid for exhausting itself (the
player did, via a forced weak-block — an asymmetry players feel as unfair).
The fixed semantics: hitting 0 stamina sets `exhausted`; the **next** turn is
a forced `weak_block` recovery turn (still vulnerable, but takes half
damage); stamina restores at the **end** of that turn.  Both sides follow the
same rules.  See `docs/COMBAT.md`.

### Broken = amplified + forced recovery (posture mode)

In the old `duel.py`, the 1.75x broken-damage multiplier was dead code:
`broken` was cleared by the recovery restore *before* the incoming hit was
resolved, so the multiplier never applied.  The fixed semantics: while
`broken` you take amplified damage for the whole turn; recovery (partial
posture restore) happens at the start of your next turn but `broken` is only
cleared at the end of it, so the amplified hit lands during recovery.

### Stamina mode is read-the-enemy too

The original stamina combat was blind: the enemy's action was rolled in
secret, so the only viable strategy was attack-spam (confirmed by
simulation: smart ≈ attack ≈ random ≈ 20%).  Both modes now reveal the
enemy's intent **before** the player commits, turning every turn into a
decision.  The modes remain distinct through their resource systems:
stamina = action-cost + exhaustion + combo; posture = hit-drain + broken +
deflect/dodge.

### Defending halves damage (both modes)

The old stamina formula (`defense * 2` while defending) made defend nearly
useless once heavy attacks reached 20+ damage.  Both modes now halve incoming
damage when defending (weak_block halves too — "you weakly raise your
guard").

### Fleeing never kills outright

The parting blow when fleeing is capped so you always escape with at least
1 HP.  A final death should come from combat or hazards, not from retreating.
(Simulation also showed flee-at-low-HP is a losing strategy in stamina mode;
the scar system handles combat deaths instead.)

### Balance is verified by simulation

`scripts/simulate.py` plays hundreds of headless games under scripted
policies and reports win rates.  The current tuning (after rebalancing the
previously unwinnable game — see `docs/TESTING.md`) targets a modestly smart
player winning ~35% of stamina runs and ~80% of posture runs, with pure
attack-spam and random play clearly below that (skill matters).

## Testing strategy

See `docs/TESTING.md`: 82 tests covering config, entities, save/load, both
combat modes, events, scars/keys, full headless runs (E2E), and simulation
guard-rails.
