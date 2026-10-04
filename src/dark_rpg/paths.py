"""Filesystem locations for the installed game.

When you install ``dark-rpg`` as a ``uv tool`` and run it from any directory,
the game still needs two things that live in a *stable* place:

* the **save file** — so your run continues wherever you launch the tool, and
* the **user config** — a personal copy of ``config.json`` that lets you tweak
  the game without editing the installed package.

Both default to the user config home: ``~/.config/dark_rpg/`` (overridable
with the ``XDG_CONFIG_HOME`` env var on POSIX; ``%APPDATA%`` on Windows).

Precedence for the *save file* (highest wins):

1. ``--save PATH`` on the command line
2. ``$DARK_RPG_SAVE`` environment variable
3. the default ``~/.config/dark_rpg/save.json``

Precedence for the *config* (highest wins):

1. ``--config PATH`` on the command line
2. ``~/.config/dark_rpg/config.json`` (if you made a personal copy)
3. the packaged ``config.json`` shipped inside the installed wheel
4. ``config.json`` in the current directory (only used in a dev checkout)

``config.json`` is the *default* tuning file.  Copy it to
``~/.config/dark_rpg/config.json`` once to make your own, and the game will
pick it up automatically on every run.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

APP = "dark_rpg"


def user_config_dir() -> Path:
    """Return ``~/.config/dark_rpg`` (created on demand).

    Honors ``XDG_CONFIG_HOME`` on POSIX; falls back to ``%APPDATA%`` on
    Windows.  Creation is best-effort: if the home is not writable the path
    is still returned (callers that need to write will fail gracefully), so a
    read-only config home can never crash the game.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP
    try:
        d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass  # not writable / read-only; fall through
    return d


def default_save_path() -> Path:
    """The save file location used when neither ``--save`` nor
    ``$DARK_RPG_SAVE`` is given."""
    env = os.environ.get("DARK_RPG_SAVE")
    if env:
        p = Path(env).expanduser()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        return p
    return user_config_dir() / "save.json"


def resolve_config_path(cli_value: Optional[str] = None) -> Path:
    """Pick the config file to load.

    * *cli_value* is a **relative** path only when it points to an existing
      file (dev checkouts, scripts, or an explicit ``--config``); absolute
      paths are always honored.
    * Otherwise, a user config in the config home wins, then the packaged
      ``config.json`` (installed wheels), then ``./config.json``.
    """
    if cli_value:
        p = Path(cli_value).expanduser()
        if p.is_absolute() or p.exists():
            return p
        # a non-existent relative --config: fall through to the defaults so
        # the user still gets a working game (the error is reported by
        # load_config, which is clearer than "file not found: config.json").
    user = user_config_dir() / "config.json"
    if user.exists():
        return user
    packaged = _packaged_config()
    if packaged is not None and packaged.exists():
        return packaged
    return Path("config.json")


def _packaged_config() -> Optional[Path]:
    """Locate the ``config.json`` installed next to the package, if any."""
    try:
        return Path(__file__).resolve().parent / "config.json"
    except Exception:  # pragma: no cover - defensive
        return None
