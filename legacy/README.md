# Legacy / Archived Scripts

These are the original one-file prototypes, kept for reference only.
They are **not** part of the current game — the standardized package in
`src/dark_rpg/` replaces them.

| File | What it was | Superseded by |
|---|---|---|
| `rpg.py` | First dungeon-crawl prototype | `src/dark_rpg/` |
| `rpg2.py` | Main stamina-combat dungeon run | `src/dark_rpg/combat/stamina.py` + `src/dark_rpg/app.py` |
| `duel.py` | Standalone posture duel (read-the-enemy) | `src/dark_rpg/combat/posture.py` (merged into the dungeon run) |
| `test_stamina_exhaustion.py` | Tests for the old stamina exhaustion logic | `tests/test_combat_stamina.py` (updated semantics) |
| `stats-idea.md` | Unfinished stat-system design notes (Vitality/Endurance/Intelligence) | `docs/ROADMAP.md` (Tier 2 feature) |

> Note: the old exhaustion tests encoded a logical gap (enemies restored
> stamina and attacked for free). The fixed semantics are documented in
> `docs/COMBAT.md` and tested in `tests/test_combat_stamina.py`.
