"""Command-line entry point.

    dark-rpg [--config PATH] [--save PATH]
             [--combat-mode stamina|posture] [--seed N]
             [--list-modes] [--list-events]

By default the save file lives in ``~/.config/dark_rpg/save.json`` so your run
continues no matter which directory you launch the tool from.  The config is
loaded from (in order): a personal ``~/.config/dark_rpg/config.json``, the
packaged ``config.json``, or ``./config.json`` in a dev checkout.  Both can be
overridden with ``--config`` / ``--save`` or the ``DARK_RPG_SAVE`` env var.
"""
from __future__ import annotations

import argparse
import random
import sys
from typing import List, Optional

from dark_rpg.app import Game
from dark_rpg.combat import available_combat_modes
from dark_rpg.config import ConfigError, load_config
from dark_rpg.io import GameIO
from dark_rpg.paths import default_save_path, resolve_config_path
from dark_rpg.world.events import event_ids


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dark-rpg",
        description="A terminal dungeon-crawl text RPG with pluggable combat systems.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="path to a config file (defaults to ~/.config/dark_rpg/config.json, "
             "the packaged config, or ./config.json)",
    )
    parser.add_argument(
        "--save",
        default=None,
        help="path to the save file (defaults to ~/.config/dark_rpg/save.json; "
             "pass 'None' to disable saving)",
    )
    parser.add_argument("--combat-mode", default=None, help="override config game.combat_mode")
    parser.add_argument("--seed", type=int, default=None, help="seed the RNG for reproducible runs")
    parser.add_argument("--list-modes", action="store_true", help="list registered combat modes and exit")
    parser.add_argument("--list-events", action="store_true", help="list registered room events and exit")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.list_modes:
        print("Combat modes:", ", ".join(available_combat_modes()))
        return 0
    if args.list_events:
        print("Room events:", ", ".join(event_ids()))
        return 0

    config_path = resolve_config_path(args.config)
    try:
        cfg = load_config(str(config_path))
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.combat_mode:
        cfg["game"]["combat_mode"] = args.combat_mode

    # save path: --save wins, then the default ~/.config/dark_rpg/save.json.
    # "--save None" (the string) disables saving.
    if args.save is None:
        save_path = str(default_save_path())
    elif args.save.lower() == "none":
        save_path = None
    else:
        save_path = args.save

    rng = random.Random(args.seed)
    game = Game(cfg, io=GameIO(cfg), rng=rng, save_path=save_path)
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
