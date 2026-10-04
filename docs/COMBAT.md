# Combat systems

Two combat modes share one interface (`CombatMode`) and one entity shape
(`Entity`: hp/atk/defense + stamina + `exhausted`/`broken` flags).  The
active mode is selected by `config.json -> game.combat_mode`.  Both modes
**reveal the enemy's intent before the player commits**, so every turn is a
read: the enemy telegraphs `attack` / `heavy` / `defend`, and you choose how
to answer.

Common rules:

* Hits roll `d20 + attacker.atk > threshold` (attack: 10, heavy: 12).
* Damage is `max(1, atk [* heavy_mult] [- defense])`; defending halves it.
* Stamina/posture pools reset at the start of each fight.

---

## Stamina mode (`stamina`)

Tuning: `config.json -> stamina`.

| Concept | Rule |
|---|---|
| Actions cost stamina | attack −2, heavy −4, defend −2 if hit, flee-fail −4 |
| Exhaustion | stamina hits 0 → `exhausted` |
| Recovery turn | the **next** turn is forced `weak_block` (half damage taken), stamina restores to `int(max * exhaustion_restore)` at the **end** of that turn |
| Combo | consecutive hits add `+1` damage each (resets on a miss) |
| Defend | halves incoming damage; costs stamina only when actually hit |

The loop: attack builds combo; heavy bursts (2x damage, 60% accuracy, 2x
stamina); defend answers telegraphed heavies; exhaustion is the cost of
overcommitting.  Simulation (see `docs/TESTING.md`) says the strongest
strategy is *attack, block big heavies, heavy an exposed defender, never
flee*.

### Exhaustion timeline (fixed semantics)

```
Turn 1..6: attack, attack, ...  stamina 16 → 0 → exhausted = True
Turn 7:    forced weak_block (enemy hits for half damage)
           stamina restored to int(16 * 0.75) = 12 at END of the turn
Turn 8:    back to normal
```

Both the player and enemies follow these exact rules — no free passes.

---

## Posture mode (`posture`)

Tuning: `config.json -> posture`.  Ported from the old `duel.py` and merged
into the dungeon run.

| Concept | Rule |
|---|---|
| Posture (PST) drains on hits **received** | attack −2, heavy −4, deflect −2 (or −7 whiff), dodge −3 (or −5 mistimed) |
| Hit-drain | a landed hit on you drains 3 PST (heavy: 5); defending halves it |
| Broken | PST hits 0 → `broken` |
| While broken | incoming damage × 1.5 (**amplified**) |
| Recovery turn | next turn: PST restored to `int(max * broken_restore)`, forced `weak_block` (no defense, no offense), still vulnerable (1.5x); `broken` cleared at the end of the turn |
| Deflect | beats `attack`/`heavy`: you spend 2 PST and drain the enemy 3/5; **whiffs against `defend`** (lose 7 PST) |
| Dodge | 60% evade; mistimed = damage + 5 PST loss |
| Defend | halves damage and drain; regen 4 PST if the enemy doesn't attack |

The core skill: read the intent.  Deflect attacks, dodge the heavy you can't
afford to deflect, punish a staggered (broken) enemy, and never deflect a
defender.  Broken is dangerous precisely because recovery leaves you exposed
for the amplified hit.

### Broken timeline (fixed semantics — the old multiplier was dead code)

```
Turn N:   enemy hits you, PST 3 → 0 → broken = True
Turn N+1: forced weak_block.  PST restored to int(24 * 0.5) = 12.
          Enemy attacks → damage × 1.5 applies (you are still broken).
          At END of the turn: PST > 0 → broken = False
```

---

## Shared combat flow (mode-agnostic game loop)

```
run_combat(player, template, floor):
    enemy = make_combatant(...)          # scaled by floor
    mode.start_combat(player)            # reset pool + flags
    loop while both alive:
        show HUD (mode.hud)
        e_action = mode.pick_enemy_action(enemy, ai_weights, rng)
        mode.reveal_intent(enemy, e_action)   # read the enemy
        forced = mode.forced_action(player)   # exhausted/broken?
        if forced: resolve(forced)
        else: input (timed) → action or flee
        msgs = mode.resolve(player, enemy, action, e_action, rng)
    rewards: xp / gold / key / level-ups
```

## Flee

`[f]` in the menu.  50% success; on success you take a parting blow but
**never die from it** (min 1 HP).  On failure you lose stamina/posture
(`flee_fail_cost`) and take extra damage, and the fight continues.  Fleeing
at low HP is usually a losing strategy in stamina mode — the scar system is a
better safety net for combat deaths.

## Damage formulas (both modes)

* Normal attack: `d20 + atk > 10` → `max(1, atk - def)`
* Heavy: `d20 + atk > 12` (60%) → `max(1, atk * 2 - def)` (stamina) /
  `max(1, int(atk * 1.8) - def)` (posture)
* Defend: final damage halved; defend in posture also halves posture drain
* Broken (posture): damage × 1.5 on top of anything else
