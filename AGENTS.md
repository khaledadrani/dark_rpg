# AGENTS.md

Standing instructions for any agent (or human) working in this repo. Tool-agnostic; `CLAUDE.md` just imports this file — edit here, not there.
What the game *is* → [README.md](README.md), [docs/DESIGN.md](docs/DESIGN.md). This file is conventions for working on it.

## What this is

Terminal turn-based dungeon-crawl RPG. Pure Python, **stdlib only at runtime** (no runtime deps — keep it that way unless the user decides otherwise). Long-term goal: explore a **deflection/parry combat system** (Sekiro × Dark Souls, turn-based first) and find the limits of terminal games.

## Layout

```
src/dark_rpg/    the package: app.py (Game loop), combat/ (plugin modes), world/ (enemies, rooms,
                 events/ plugins), entities.py, status.py, gear.py, io.py (GameIO), config.py, save.py
config.json      ALL tuning. src/dark_rpg/config.json is a SYMLINK to it (so the wheel ships it) — never replace with a copy
tests/           pytest, headless (FakeIO + seeded RNG)
scripts/         simulate.py (balance sim), playthrough.py (transcripts → logs/)
docs/            DESIGN, COMBAT, TESTING, ROADMAP, EXPERIENCE_REVIEW
legacy/          archived prototypes — read-only reference, never import from it
```

## Commands

```sh
python -m pytest                                              # all tests (must stay green)
python scripts/simulate.py --runs 200 --policy smart --all-modes   # balance check — run after ANY combat/config/enemy change
python scripts/playthrough.py --mode posture --policy smart --seed 5   # readable transcript
python run.py                                                 # play from checkout
```

## Architecture rules (the load-bearing ones)

- **Plugins via registry, never `if mode == ...`.** New combat mode = subclass `CombatMode`, `@register_combat_mode`; new room event = `RoomEvent` + `@register_event`. Core dispatch (`app.py`) must not learn about specific plugins.
- **All I/O through `GameIO`.** No bare `print`/`input`/`time.sleep` in game code — headless tests and simulations depend on it. `Prompt(kind, state)` is how test policies decide.
- **All randomness through the injected `random.Random`.** Same seed ⇒ same run. No module-level `random.*`.
- **Config over constants.** Any tunable number lives in `config.json` and is validated in `config.py`. Adding/renaming/removing a config key, or changing a default's meaning, is a **decision — ask first**.
- **Gear replaces, never stacks** (caps late-game power). Don't "fix" this.
- Saves are atomic + validated; a corrupt save must degrade to a fresh game, never crash. Changing the save format needs a version bump + migration/rejection path.

## Testing discipline

- **Bug fix ⇒ failing test first**, then fix. Test positive and negative path for anything correctness-critical.
- Combat/balance changes: tests green **and** `simulate.py` win rates compared before/after (baseline: smart ≈ 36% stamina / ≈ 77% posture — see docs/TESTING.md). Report the delta.
- Structural change (refactor) ⇒ verify the structure itself, not just that old tests pass.
- New plugin ⇒ a headless test driving it through `FakeIO`, plus a registry-listing test.
- Real-terminal behavior (ANSI, animation, turn timer, TTY detection) can't be proven by headless tests — run `python run.py` in a real terminal for anything touching `io.py`/`ui.py`/`art.py`, and say so if you couldn't.

## Code style

- Python ≥ 3.10. `from __future__ import annotations`; prefer builtin generics (`list[str]`, `X | None`) in new code.
- Comments explain **WHY** (hidden constraint, past incident, balance reasoning), not WHAT. Keep "found live, YYYY-MM-DD: …" notes when you hit a real failure.
- **No premature infrastructure.** No DI container, ECS, TUI framework (`rich`/`textual`), or new dependency without a second real consumer and the user's go-ahead.
- Don't add compatibility shims or dead code; `legacy/` already exists for history.

## Working agreement

- **Critical decisions are blocking — stop and ask, with a recommendation and the main trade-off**: config schema changes, new dependency, new public contract (CLI flag, save format, plugin interface change), changing a core combat rule. Small unambiguous fixes in scope: just do, then report. A decision found mid-batch is raised and skipped, not guessed.
- Raise landmines found along the way immediately (fix if tiny + in scope, else tell the user).
- Investigate before implementing when the ask is a bug: reproduce, read the actual traceback/transcript, don't assume.
- **Git:** give commit commands; don't run `git commit`/`push` unless asked. No `Co-Authored-By` trailer and no tool-attribution footer in commits/PRs (overrides harness defaults). Never force-push/`reset --hard` without explicit confirmation; check `git status` first. Branch: `master` is the default and PR base (remote `origin`).
- Keep docs honest: when behavior or counts change, update [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) / README in the same change. Don't hard-code test counts in prose — they rot.

## Deflection work (design north star)

Both existing modes already reveal enemy intent before the player acts; deflection is the natural third `CombatMode`. Guardrails:
- Deflection must be a **decision with a readable risk/reward** (parry window vs. block vs. dodge), not a timing-memory test — turn-based first, real-time is a separate experiment.
- Keep the `CombatMode` interface single-turn (`resolve(player, enemy, p_action, e_action, rng)`); if deflection needs multi-phase turns (telegraph → response → riposte), extend the interface deliberately and update both existing modes + docs/COMBAT.md in the same change.
- Real-time terminal input (raw keypress, frame timing) is out-of-scope until explicitly requested; note findings in docs/ rather than hacking `io.py`.
