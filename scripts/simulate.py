"""Headless balance simulation — "does this game make sense?"

Plays N full games per combat mode under configurable player policies and
prints a report card: win rate, floors cleared, deaths, fights, gold.

Usage (from the repo root):

    python scripts/simulate.py --runs 100 --policy smart --seed 0
    python scripts/simulate.py --runs 200 --policy random --all-modes
    python scripts/simulate.py --policy attack --mode posture

Policies:
    attack   — always attack in combat
    random   — random valid combat actions
    smart    — defend when low, deflect/dodge in posture mode

Anything printed by the game is suppressed; only the summary table appears.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dark_rpg.combat import available_combat_modes  # noqa: E402
from dark_rpg.config import load_config  # noqa: E402
from dark_rpg.testing import (  # noqa: E402
    attack_policy,
    random_policy,
    run_simulation,
    smart_policy,
)

POLICIES = {
    "attack": lambda rng: attack_policy,
    "random": random_policy,
    "smart": lambda rng: smart_policy,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--policy", choices=list(POLICIES), default="smart")
    parser.add_argument("--mode", default=None, help="combat mode (default: all)")
    parser.add_argument("--all-modes", action="store_true", help="run every combat mode")
    args = parser.parse_args()

    cfg = load_config(args.config)
    modes = available_combat_modes() if args.all_modes or args.mode is None else [args.mode]

    import random as _random
    rng = _random.Random(args.seed)
    policy_factory = POLICIES[args.policy]

    print(f"Simulating {args.runs} runs per mode | policy={args.policy} | seed={args.seed}")
    print(f"{'mode':<10}{'win%':>6}{'wins':>6}{'losses':>8}{'floors':>8}{'level':>7}"
          f"{'scars':>7}{'deaths':>8}{'fights':>8}{'rooms':>7}{'gold':>7}")
    print("-" * 82)

    for mode in modes:
        stats = run_simulation(
            cfg,
            combat_mode=mode,
            policy=policy_factory(rng),
            runs=args.runs,
            seed_base=args.seed,
        )
        print(f"{mode:<10}{stats['win_rate'] * 100:>5.1f}%{stats['wins']:>6}{stats['losses']:>8}"
              f"{stats['avg_floors_cleared']:>8.1f}{stats['avg_level']:>7.1f}"
              f"{stats['avg_scars']:>7.1f}{stats['avg_deaths']:>8.1f}"
              f"{stats['avg_fights']:>8.1f}{stats['avg_rooms']:>7.1f}{stats['avg_gold']:>7.0f}")

    print("-" * 82)
    print("floors: avg floors cleared (10 = won the game)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
