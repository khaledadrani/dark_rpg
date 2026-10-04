"""Combat mode interface (Strategy pattern).

A *combat mode* owns everything about how a fight resolves: what actions the
player can pick, how the enemy chooses, whether intent is revealed, and how a
turn is resolved.  The dungeon loop (:meth:`dark_rpg.app.Game.run_combat`) is
mode-agnostic — it only calls this interface.

The two built-in modes are:

* :class:`dark_rpg.combat.stamina.StaminaCombatMode` — simultaneous
  resolution, stamina spent on actions, exhaustion forces a recovery turn.
* :class:`dark_rpg.combat.posture.PostureCombatMode` — sequential resolution
  with the enemy's intent revealed before you act; posture drains on hits
  received; being "broken" forces a recovery turn.

To add a third mode: subclass :class:`CombatMode`, set ``key``/``name``/
``config_key``, implement the abstract methods, and decorate the class with
``@register_combat_mode``.  Then switch to it via
``config.json -> game.combat_mode``.
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from dark_rpg.entities import Entity

if TYPE_CHECKING:
    from dark_rpg.entities import Player


class CombatModeError(Exception):
    """Raised when a combat mode key is unknown or misconfigured."""


class CombatMode(ABC):
    """Strategy interface for a full combat system."""

    #: unique registry key, e.g. ``"stamina"``
    key: str = ""
    #: human-readable name
    name: str = ""
    #: which section of the config holds this mode's tuning
    config_key: str = ""

    def __init__(self, cfg: Dict[str, Any], color_on: bool = False) -> None:
        self.cfg = cfg
        self.color_on = color_on

    # ── setup ───────────────────────────────────────────────────────────
    @abstractmethod
    def max_stamina(self) -> int:
        """The size of the stamina/posture pool this mode uses."""

    @abstractmethod
    def start_combat(self, combatant: Entity) -> None:
        """Reset a combatant for a fresh fight (pool, flags, ...)."""

    # ── the menu the player sees ────────────────────────────────────────
    @abstractmethod
    def action_menu(self) -> List[Tuple[str, str]]:
        """Return ``[(key, label), ...]`` for the player's actions.

        The ``f`` (flee) option is added by the game loop, not here.
        """

    #: maps menu input keys (e.g. ``"1"``) to action names (e.g. ``"attack"``)
    ACTION_KEYS: Dict[str, str] = {}

    def action_for_key(self, key: str) -> str:
        """Translate a menu key into an action name; falls back to idle."""
        return self.ACTION_KEYS.get(key, self.idle_action())

    # ── per-turn hooks ──────────────────────────────────────────────────
    @abstractmethod
    def forced_action(self, combatant: Entity) -> Optional[Tuple[str, str]]:
        """Return ``(action, message)`` if the combatant must act a certain
        way this turn (e.g. exhausted/broken -> weak_block), else None."""

    def idle_action(self) -> str:
        """Action used on invalid input / hesitation / timeout."""
        return "weak_block"

    @abstractmethod
    def pick_enemy_action(self, enemy: Entity, weights: Dict[str, float], rng: random.Random) -> str:
        """Choose the enemy's action from its AI weights."""

    @abstractmethod
    def reveal_intent(self, enemy: Entity, action: str) -> Optional[str]:
        """Text shown *before* the player chooses (posture mode reveals,
        stamina mode hides).  Returns None to reveal nothing."""

    @abstractmethod
    def resolve(
        self,
        player: Entity,
        enemy: Entity,
        p_action: str,
        e_action: str,
        rng: random.Random,
    ) -> List[str]:
        """Resolve one turn; returns the messages to display."""

    @abstractmethod
    def hud(self, player: Entity, enemy: Entity) -> List[str]:
        """Lines drawn at the top of each combat turn."""

    def flee_fail(self, combatant: Entity) -> List[str]:
        """Consequence of a failed flee (mode-specific resource penalty)."""
        return []

    def _use_item(self, player: Entity, enemy: Entity, rng) -> List[str]:
        """Shared "use a consumable" action.

        Priority: heal with a potion if hurt, else apply oil (burn) or poison
        to the enemy.  Returns the messages to display.
        """
        from dark_rpg.status import apply_status
        player = cast("Player", player)  # only the player carries consumables/food
        msgs: List[str] = []
        # 1) drink a potion if damaged
        if player.use_consumable("potion") and player.hp < player.max_hp:
            healed = min(20, player.max_hp - player.hp)
            player.hp += healed
            msgs.append(f"  You drink a potion. +{healed} HP.")
            return msgs
        # 2) throw oil to ignite the enemy
        if player.use_consumable("oil"):
            specs = {s["name"]: s for s in self.cfg.get("status_effects", [])}
            spec = specs.get("burn", {"power": 3, "duration": 2})
            apply_status(enemy, "burn", spec["duration"], spec["power"])
            msgs.append(f"  You hurl a vial of oil — {enemy.name} is engulfed in flames! (burn)")
            return msgs
        # 3) use a poison vial
        if player.use_consumable("poison_vial"):
            specs = {s["name"]: s for s in self.cfg.get("status_effects", [])}
            spec = specs.get("poison", {"power": 2, "duration": 3})
            apply_status(enemy, "poison", spec["duration"], spec["power"])
            msgs.append(f"  You smear a blade in poison — {enemy.name} is poisoned! (poison)")
            return msgs
        # 4) eat rations for food (out-of-combat survival, but usable here)
        if player.use_consumable("rations"):
            player.food += 4
            msgs.append("  You gnaw on rations. +4 food.")
            return msgs
        msgs.append("  You reach for your pouch... but it's empty.")
        return msgs
