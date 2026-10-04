"""Shrine room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.io import Prompt
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class ShrineEvent(RoomEvent):
    """A gamble: pray for a blessing (50/50: +10 HP or −5 HP) or ignore it."""

    id = "shrine"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        io = game.io
        io.slow_out("  You find an ancient shrine.")
        io.out("  [1] Pray (50% chance: +10 HP or -5 HP)")
        io.out("  [2] Ignore")
        choice = io.ask(Prompt("shrine", "  > ", {"floor": player.floor}))
        if choice.strip() != "1":
            io.slow_out("  You leave the shrine undisturbed.")
            return
        if game.rng.randint(1, 20) > 10:
            player.hp = min(player.max_hp, player.hp + 10)
            io.slow_out("  The gods smile. +10 HP.")
        else:
            player.take_damage(5)
            io.slow_out("  The gods are displeased. -5 HP.")
