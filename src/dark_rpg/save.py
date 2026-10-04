"""Save / load with validation.

Saves are written atomically (write to a ``.tmp`` then rename) so a crash in
the middle of a write can never corrupt an existing save.  Loading validates
the shape of the file and raises :class:`SaveError` on any problem; the CLI
catches that and offers a fresh game instead of crashing.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from dark_rpg.entities import Player


class SaveError(Exception):
    """Raised when a save file cannot be read or is corrupt."""


def save_game(player: Player, path: Optional[str]) -> None:
    """Write *player* to *path* atomically.  No-op when *path* is None."""
    if path is None:
        return
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(player.to_dict(), f, indent=2)
    os.replace(tmp, path)


def load_game(path: str, cfg: Dict[str, Any]) -> Player:
    """Load and validate a save file; raises :class:`SaveError`."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except OSError as exc:
        raise SaveError(f"Could not read save file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SaveError(f"Save file is not valid JSON: {exc}") from exc

    try:
        return Player.from_dict(data, cfg)
    except (ValueError, TypeError, KeyError) as exc:
        raise SaveError(f"Save file is corrupt: {exc}") from exc


def delete_save(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        os.remove(path)
