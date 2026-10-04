"""Combat mode plugin registry.

New combat systems register themselves here with the
``@register_combat_mode`` decorator; the active mode is selected by
``config.json -> game.combat_mode`` (e.g. ``"stamina"`` or ``"posture"``).
"""
from __future__ import annotations

from typing import Any, Dict, List

from dark_rpg.combat.base import CombatMode, CombatModeError
from dark_rpg.registry import PluginRegistry

COMBAT_MODES: PluginRegistry[type] = PluginRegistry("combat mode")


def register_combat_mode(cls: type) -> type:
    """Class decorator that registers a :class:`CombatMode` subclass."""
    if not (isinstance(cls, type) and issubclass(cls, CombatMode)):
        raise TypeError("register_combat_mode expects a CombatMode subclass")
    COMBAT_MODES.register(cls.key, cls)
    return cls


def get_combat_mode(key: str, cfg: Dict[str, Any], color_on: bool = False) -> CombatMode:
    """Instantiate the combat mode registered under *key*."""
    try:
        cls = COMBAT_MODES.get(key)
    except KeyError as exc:
        raise CombatModeError(str(exc)) from None
    return cls(cfg, color_on=color_on)


def available_combat_modes() -> List[str]:
    return COMBAT_MODES.keys()


# ── register the built-in modes ─────────────────────────────────────────
# Imported after register_combat_mode exists so the decorators can fire.
from dark_rpg.combat import posture  # noqa: E402,F401
from dark_rpg.combat import stamina  # noqa: E402,F401
