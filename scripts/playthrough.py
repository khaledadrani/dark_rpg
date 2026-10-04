"""Generate a full playthrough transcript for experience review.

Plays one headless game under a policy and writes the complete transcript
(everything the player would see, plus the scripted answers) to a file, so
you can read the game like a book and evaluate the experience.

Usage (from the repo root):

    python scripts/playthrough.py --mode stamina --policy smart --seed 5 \
        --out logs/stamina_smart_seed5.log
    python scripts/playthrough.py --mode posture --policy smart --seed 5

Output goes to ``logs/<mode>_<policy>_seed<seed>.log`` unless ``--out`` is
given.
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from dark_rpg.app import Game  # noqa: E402
from dark_rpg.config import load_config  # noqa: E402
from dark_rpg.io import GameIO, Prompt  # noqa: E402
from dark_rpg.testing import (  # noqa: E402
    DEFAULT_ANSWERS,
    attack_policy,
    random_policy,
    smart_policy,
)

POLICIES = {
    "attack": lambda rng: attack_policy,
    "random": random_policy,
    "smart": lambda rng: smart_policy,
}


class TranscriptIO(GameIO):
    """Captures every printed line and every scripted answer in order."""

    def __init__(self, cfg, responder):
        self.lines: list[str] = []
        self.responder = responder
        super().__init__(
            cfg,
            input_fn=self._input,
            print_fn=lambda s: self.lines.append(s),
            sleep_fn=lambda s: None,
            clear_fn=lambda: None,
            slow_print_delay=0.0,
            turn_timer_enabled=False,
        )

    def _input(self, prompt: Prompt) -> str:
        answer = self.responder(prompt)
        # echo the prompt + the answer like a real terminal would
        self.lines.append(f"{prompt.text} {answer}")
        return answer

    def write(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--mode", choices=["stamina", "posture"], default="stamina")
    parser.add_argument("--policy", choices=list(POLICIES), default="smart")
    parser.add_argument("--seed", type=int, default=5)
    parser.add_argument("--out", default=None, help="output path (default: logs/<mode>_<policy>_seed<seed>.log)")
    args = parser.parse_args()

    cfg = load_config(args.config)
    cfg = {**cfg, "game": {**cfg["game"], "combat_mode": args.mode}}
    rng = random.Random(args.seed)
    policy_factory = POLICIES[args.policy]

    def responder(prompt: Prompt):
        answer = policy_factory(rng)(prompt)
        return answer if answer is not None else DEFAULT_ANSWERS.get(prompt.kind, "")

    io = TranscriptIO(cfg, responder)
    game = Game(cfg, io=io, rng=rng, save_path=None)
    result = game.run()

    out = args.out or f"logs/{args.mode}_{args.policy}_seed{args.seed}.log"
    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    io.write(out)

    print(f"transcript written: {out}")
    print(f"outcome={result.outcome} floors={result.floors_cleared} "
          f"level={result.level} scars={result.scars} deaths={result.deaths} "
          f"fights={result.fights} rooms={result.rooms} lines={len(io.lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
