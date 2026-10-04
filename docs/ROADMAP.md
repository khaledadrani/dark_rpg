# Roadmap

Priority-ordered ideas for making the game *highly* fun, roughly by
fun-per-effort.

## Done — publish pass (this iteration)

- [x] **Gear system** — loot is now equipment that *replaces* a slot
  (weapon / armor / trinket) instead of stacking flat bonuses forever.
  Kills the late-game power explosion; every find is a real decision.
- [x] **Rarity tiers** — common / uncommon / rare / epic, with per-rarity
  stat multipliers and weighted drops.
- [x] **Playstyle loot + status effects** — burn / poison DoT, plus
  consumables (oil flask, poison vial, potion, rations) usable *in combat*
  via the `[u] Use item` action.
- [x] **Enemy special abilities** — data-driven: crit (Assassin), lifesteal
  (Vampire), drain (Wraith), revive (Lich), status-on-hit (Cave Spider
  poisons).  The player's own template is empty.
- [x] **Expanded roster** — 5 → 12 enemies across 10 floors (Giant Rat,
  Cave Spider, Cultist, Assassin, Wraith, Vampire, Lich added), each with
  its own ASCII art.
- [x] **Re-scaled boss + curve** — the Dungeon Tyrant is 130 HP / ATK 17 /
  DEF 8 and actually fights back; floor/tier scaling retuned.
- [x] **Food re-tune** — starting food 15 → 25, key-drop chance raised,
  merchants a little more frequent, traps/ambush/secret give food back.
- [x] **New room events** — vault (guarded treasure), curse (DoT altar),
  ambush (surprise strike), gamble (coin-flip), secret passage — 6 → 11
  events total.
- [x] **Expanded shop** — potions, rations, oil, poison vials, sharpen
  stone, bracer (two purchase kinds: consume / stat).
- [x] **Expanded flavor** — 7 → 25 room flavor lines.
- [x] **Pacing** — removed the redundant "Press Enter" after the enemy
  reveal.
- [x] **Death recap + victory screen** — a RUN RECAP block prints
  outcome, level, fights, deaths, rooms, gold.
- [x] **ANSI colour** — HP/STA/PST bars are tinted and broken-state
  flashes red, only on an interactive TTY (piped logs stay clean),
  toggle `ui.ansi_color`.
- [x] **Balance verified** — smart-policy win rates: stamina ~36%,
  posture ~77% (200-run simulation).  See `docs/EXPERIENCE_REVIEW.md`.
- [x] **107 tests** — unit + headless E2E + dedicated `test_new_features.py`
  covering gear, statuses, abilities, consumables, and the new events.

## Still open (future ideas)

- [ ] **Boss telegraphs** — the Tyrant already fights hard; give it a
  dedicated 2-turn "charging" move the player must interrupt.
- [ ] **Merchant rerolls / limited stock** — a "refresh for 5g" option.
- [ ] **Per-enemy hit/kill lines** — varied combat prose per enemy.
- [ ] **Story spine** — why descend? named NPCs, choices that pay off later,
  2–3 endings.
- [ ] **Branching floor map** (Slay-the-Spire style) — choose your route.
- [ ] **Meta-progression** — spend earned gold to unlock starting gear.
- [ ] **Stat system** (`legacy/stats-idea.md`) — build choice on level-up.
- [ ] `rich`/`textual` TUI for panels and mouse support.
