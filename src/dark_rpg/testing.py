"""Testing & simulation helpers.

This module is **tooling**, not game logic.  It provides:

* :class:`StubRng` — deterministic RNG for scripted scenarios.
* :class:`FakeIO` — headless IO that answers prompts from a scripted queue,
  from per-prompt-kind defaults, or from a policy callable.
* :class:`SeededGame` factory — build a :class:`~dark_rpg.app.Game` with a
  real seeded RNG for reproducible full runs.
* :func:`run_simulation` — play N headless games under a policy and
  aggregate the results (see ``scripts/simulate.py``).
"""
from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Sequence

from dark_rpg.app import Game, GameResult
from dark_rpg.io import GameIO, Prompt

# ─────────────────────────────────────────────────────────────────────────
#  Deterministic RNG
# ─────────────────────────────────────────────────────────────────────────

class StubRng:
    """A fixed-value RNG: ``randint`` always returns ``roll``, ``random``
    always returns ``rand``, and choices pick the first item.  Great for
    scripted scenario tests where you want to *force* an outcome."""

    def __init__(self, roll: int = 20, rand: float = 0.0) -> None:
        self.roll = roll
        self.rand = rand

    def randint(self, a: int, b: int) -> int:
        # clamp into the requested range so bounds are always respected
        return min(b, max(a, self.roll))

    def random(self) -> float:
        return self.rand

    def choice(self, seq: Sequence) -> Any:
        return seq[0]

    def choices(self, seq: Sequence, weights: Optional[Sequence] = None, *, k: int = 1) -> List[Any]:
        return [seq[0] for _ in range(k)]


# ─────────────────────────────────────────────────────────────────────────
#  Headless IO
# ─────────────────────────────────────────────────────────────────────────

#: Fallback answers for prompt kinds that scripts rarely care about.
DEFAULT_ANSWERS: Dict[str, str] = {
    "pause": "",
    "name": "Hero",
    "menu": "n",
    "descend": "d",
    "merchant": "",      # invalid choice -> leave
    "shrine": "2",       # ignore
    "gamble": "2",       # walk away from the coin-flip gamble
    "combat_action": "1",
}


class FakeIO(GameIO):
    """Headless GameIO.

    Answers are resolved in order: a ``respond`` callable (policies), then a
    scripted queue, then kind-based defaults.  An unexpected prompt with no
    answer raises AssertionError so tests fail loudly instead of silently.
    """

    def __init__(
        self,
        answers: Optional[List[str]] = None,
        defaults: Optional[Dict[str, str]] = None,
        cfg: Optional[dict] = None,
        respond: Optional[Callable[[Prompt], Optional[str]]] = None,
    ) -> None:
        self.answers = list(answers or [])
        self.defaults = {**DEFAULT_ANSWERS, **(defaults or {})}
        self.respond = respond
        self.prompt_log: List[Prompt] = []
        self.print_log: List[str] = []
        super().__init__(
            cfg,
            input_fn=self._input,
            print_fn=lambda *a, **k: self.print_log.append(a[0] if a else ""),
            sleep_fn=lambda s: None,
            clear_fn=lambda: None,
            slow_print_delay=0.0,
            turn_timer_enabled=False,
        )

    def _input(self, prompt: Prompt) -> str:
        self.prompt_log.append(prompt)
        if self.respond:
            answer = self.respond(prompt)
            if answer is not None:
                return str(answer)
        if self.answers:
            return str(self.answers.pop(0))
        default = self.defaults.get(prompt.kind)
        if default is not None:
            return default
        raise AssertionError(f"Unexpected prompt with no scripted answer: {prompt}")

    def text(self) -> str:
        return "\n".join(self.print_log)


# ─────────────────────────────────────────────────────────────────────────
#  Policies (used by simulations and E2E tests)
# ─────────────────────────────────────────────────────────────────────────

def attack_policy(prompt: Prompt) -> Optional[str]:
    """Always attack in combat; defaults everywhere else."""
    if prompt.kind == "combat_action":
        return "1"
    return None


def random_policy(rng: random.Random) -> Callable[[Prompt], Optional[str]]:
    """Pick a random valid combat action; defaults everywhere else."""
    def respond(prompt: Prompt) -> Optional[str]:
        if prompt.kind == "combat_action":
            n_actions = 4 if prompt.state.get("mode") == "stamina" else 6  # actions + flee
            return str(rng.randint(1, n_actions))
        return None
    return respond


def smart_policy(prompt: Prompt) -> Optional[str]:
    """A modestly smart player:

    * buys rations when food runs low, potions when hurt,
    * flees fights it can't win (HP critically low),
    * stamina: defends when low on HP *and* can afford the stamina cost,
      otherwise attacks,
    * posture: deflects attacks when possible, dodges heavies it can't
      deflect, punishes broken enemies, defends when low on HP.
    """
    if prompt.kind == "merchant":
        st = prompt.state
        if st.get("food", 99) < 4 and st.get("gold", 0) >= 5:
            return "2"  # buy rations
        if st.get("hp", 1) < st.get("max_hp", 1) * 0.6 and st.get("gold", 0) >= 10:
            return "1"  # buy a potion
        return "0"  # leave (0 is never a valid shop option)
    if prompt.kind == "shrine":
        return "2"  # ignore the gamble
    if prompt.kind == "gamble":
        return "2"  # walk away
    if prompt.kind == "descend":
        return "d"  # descend when holding the key (prevents floor-1 stalling)
    if prompt.kind != "combat_action":
        return None
    st = prompt.state
    mode = st.get("mode")
    php, pmax = st.get("player_hp", 1), st.get("player_max_hp", 1)
    pst = st.get("player_sta", 0)
    intent = st.get("intent")

    if mode == "stamina":
        # Empirically tuned (docs/TESTING.md): attack; block telegraphed
        # heavies that would hurt; heavy the enemy when it defends.  Never
        # flee — fleeing is a death trap in stamina mode.
        if intent == "heavy" and pst >= 6:
            heavy_dmg = max(1, 2 * st.get("enemy_atk", 0) - st.get("player_def", 0))
            if heavy_dmg >= 10:
                return "3"
        if intent == "defend" and pst >= 8:
            return "2"  # punish the exposed defender
        return "1"

    # posture mode
    if st.get("enemy_broken"):
        return "1"  # punish the staggered enemy
    if intent in ("attack", "heavy") and pst >= 10:
        return "3"  # deflect
    if intent == "heavy" and pst < 10:
        return "4"  # dodge the heavy
    if php < pmax * 0.4:
        return "5"  # defend
    return "1"


# ─────────────────────────────────────────────────────────────────────────
#  Game factories & simulation
# ─────────────────────────────────────────────────────────────────────────

def make_game(
    cfg: dict,
    *,
    combat_mode: Optional[str] = None,
    answers: Optional[List[str]] = None,
    defaults: Optional[Dict[str, str]] = None,
    respond: Optional[Callable[[Prompt], Optional[str]]] = None,
    seed: Optional[int] = None,
    rng: Optional[Any] = None,
    save_path: Optional[str] = None,
) -> Game:
    """Build a headless Game.  Pass ``rng=StubRng(...)`` for scripted
    scenarios or ``seed=N`` for reproducible seeded runs."""
    if combat_mode:
        cfg = {**cfg, "game": {**cfg["game"], "combat_mode": combat_mode}}
    io = FakeIO(answers=answers, defaults=defaults, cfg=cfg, respond=respond)
    if rng is None:
        rng = random.Random(seed)
    return Game(cfg, io=io, rng=rng, save_path=save_path)


def run_simulation(
    cfg: dict,
    *,
    combat_mode: str,
    policy: Optional[Callable[[Prompt], Optional[str]]] = None,
    runs: int = 50,
    seed_base: int = 0,
) -> Dict[str, Any]:
    """Play *runs* headless games under *policy* and aggregate results.

    Returns a dict with win/loss counts, rates, and averaged stats — the
    "does this game make sense?" report card.
    """
    results: List[GameResult] = []
    for i in range(runs):
        run_cfg = {**cfg, "game": {**cfg["game"], "combat_mode": combat_mode}}
        rng = random.Random(seed_base + i)
        io = GameIO(
            run_cfg,
            input_fn=lambda p: (policy(p) if policy else None) or DEFAULT_ANSWERS.get(p.kind, ""),
            print_fn=lambda *a, **k: None,
            sleep_fn=lambda s: None,
            clear_fn=lambda: None,
            slow_print_delay=0.0,
            turn_timer_enabled=False,
        )
        game = Game(run_cfg, io=io, rng=rng, save_path=None)
        results.append(game.run())

    wins = [r for r in results if r.outcome == "win"]
    losses = [r for r in results if r.outcome == "dead"]
    n = len(results)
    return {
        "combat_mode": combat_mode,
        "runs": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": (len(wins) / n) if n else 0.0,
        "avg_floors_cleared": sum(r.floors_cleared for r in results) / n if n else 0.0,
        "avg_level": sum(r.level for r in results) / n if n else 0.0,
        "avg_scars": sum(r.scars for r in results) / n if n else 0.0,
        "avg_deaths": sum(r.deaths for r in results) / n if n else 0.0,
        "avg_fights": sum(r.fights for r in results) / n if n else 0.0,
        "avg_rooms": sum(r.rooms for r in results) / n if n else 0.0,
        "avg_gold": sum(r.gold for r in results) / n if n else 0.0,
    }
