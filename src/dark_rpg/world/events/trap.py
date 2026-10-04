"""Trap room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class TrapEvent(RoomEvent):
    """Trigger a trap and take damage."""

    id = "trap"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        dmg = game.rng.randint(3, 10)
        player.take_damage(dmg)
        game.io.slow_out(f"  You trigger a trap! -{dmg} HP.")
