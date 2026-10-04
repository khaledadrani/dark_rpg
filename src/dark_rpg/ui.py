"""Pure display helpers (no IO side effects)."""
from __future__ import annotations

from typing import Optional

#: ANSI colour codes for visual emphasis (HP/STA/PST bars, crits, level-ups).
#: Applied only when the output is interactive and ``ui.ansi_color`` is on.
ANSI = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "red": "\033[91m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "cyan": "\033[96m",
    "magenta": "\033[95m",
}


def bar(
    current: int,
    maximum: int,
    width: int = 20,
    fill: str = "\u2588",
    empty: str = "\u2591",
    color: str = "",
    reset: str = "",
) -> str:
    """Render a progress bar, e.g. ``[█████░░░░░] 5/10``.

    *color* and *reset* are optional ANSI codes used to tint the bar and
    restore the terminal style afterwards (empty strings in no-colour mode).
    """
    current = max(0, current)
    filled = int(width * current / max(maximum, 1))
    return f"{color}[{fill * filled}{empty * (width - filled)}]{reset} {current}/{maximum}"


def article(name: str) -> str:
    """Indefinite article for an entity name: ``"a "`` / ``"an "``, or
    ``""`` when the name already starts with an article.

    >>> article("Goblin")              # 'a '
    >>> article("Orc")                 # 'an '
    >>> article("The Dungeon Tyrant")  # ''  (no "A The ...")
    """
    if not name:
        return ""
    lowered = name.lower()
    if lowered.startswith(("the ", "a ", "an ")):
        return ""
    return "an " if lowered[0] in "aeiou" else "a "
