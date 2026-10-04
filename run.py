"""Run the game without installing the package.

    python run.py [--combat-mode stamina|posture] [--seed N] [--save PATH]

Equivalent to installing with `pip install -e .` and running `dark-rpg`.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "src"))

from dark_rpg.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
