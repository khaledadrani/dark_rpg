# Experience Review — after the publish pass

Regenerated with `scripts/playthrough.py` (headless, scripted policies, seed 5)
and `scripts/simulate.py` (200 runs, smart policy, both modes).

## Balance (200-run simulation, smart policy)

| Mode | Win % | Avg floors | Avg level | Avg scars |
|---|---|---|---|---|
| posture | 77% | 9.7 | 5.6 | 0.1 |
| stamina | 36% | 9.0 | 5.0 | 0.2 |

Both modes are **winnable but challenging**: posture (read-the-enemy) is
rewarding for attentive play, stamina (classic) is a real test.  The attack-spam
and random policies win far less, as they should.

## What the publish pass fixed

1. **🔴 The boss is no longer a joke.** Before the pass, loot bonuses stacked
   without limit and by floor 10 the player had ATK 46 / DEF 26 — the Tyrant
   died in 3 hits.  Now:
   - Loot is **equipment** (weapon / armor / trinket slots) that *replaces*
     what you're wearing, so stats can't run away.
   - The Tyrant was re-scaled to **130 HP / ATK 17 / DEF 8** and has a heavy
     swing that lands ~18 damage through a defend.
   - A smart player reaches the boss around level 5–6 with ~ATK 30 / DEF 15 —
     a tense, several-turn fight, not a stomp.
2. **🔴 Food pressure is manageable.** Starting food raised 15 → 25, key-drop
   chance raised, merchants a little more frequent, and the new
   secret / rest / vault events all give food back.  The hunger spiral is gone.
3. **🟠 Content depth.** The roster grew 5 → 12 enemies (several with
   *special abilities* — crit, lifesteal, drain, revive, poison-on-hit),
   events grew 6 → 11 (vault, curse, ambush, gamble, secret), the shop got
   consumables (potion / rations / oil / poison vial / sharpen / bracer), and
   the loot table is now rarity-tiered gear + playstyle items.
4. **🟠 Status effects make combat a system.** Burn and poison (damage-over-time)
   tick each turn in **both** combat modes, with HUD indicators
   (`[poison, burn]`).  You can *apply* them to foes via the new
   `[u] Use item` action (oil flask, poison vial) or drink a potion.
5. **🟠 Atmosphere & feel.** 25 room flavor lines (was 7), per-enemy ASCII art
   for all 12, a RUN RECAP screen at the end of every run, the redundant
   "Press Enter" after the enemy reveal removed, and ANSI-coloured bars on a
   real terminal (green HP, cyan stamina, red broken-state).  Piped logs
   (scripts, CI) stay plain — no escape codes leak in.

## What the transcript shows

A winning stamina run (seed 5, smart policy): the player is poisoned by a
Cave Spider, drinks a potion mid-fight, equips progressively better gear
(Iron Shortsword → Runed Warblade → Dragonbone Cleaver; Cloth Vest →
Dragon Scale; Copper Ring → Ward of Thorns), triggers an ambush, finds a
hidden vault, gets cursed at an altar, and finally faces the Tyrant at
level 6 — a fight that lasts several turns with heavies landing 18 damage.

## How to regenerate

```bash
python scripts/playthrough.py --mode stamina --policy smart --seed 5
python scripts/playthrough.py --mode posture --policy smart --seed 5
python scripts/simulate.py --runs 200 --policy smart --all-modes
```
