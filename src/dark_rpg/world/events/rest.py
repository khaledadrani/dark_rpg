"""Rest room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class RestEvent(RoomEvent):
    """A quiet alcove: heal some HP and find food."""

    id = "rest"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        heal = game.rng.randint(8, 18)
        food = game.rng.randint(1, 3)
        player.hp = min(player.max_hp, player.hp + heal)
        player.food += food
        game.io.slow_out(f"  A quiet alcove. You rest. +{heal} HP | +{food} food.")
