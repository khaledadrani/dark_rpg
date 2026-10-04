"""Gamble / risk room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.io import Prompt
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class GambleEvent(RoomEvent):
    """A small risk event: the player can bet gold for a chance to double it,
    or walk away safely.  The choice is explicit and the outcome is visible."""

    id = "gamble"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        io, rng = game.io, game.rng
        io.slow_out("  A masked stranger offers a coin flip. Win and your gold doubles; lose and it is gone.")
        choice = io.ask(Prompt("gamble", "  [1] Bet all gold   [2] Walk away\n  > ", {
            "gold": player.gold,
            "hp": player.hp,
            "max_hp": player.max_hp,
        }))
        if choice.strip() != "1":
            io.slow_out("  You keep your coin purse safely tucked away.")
            return
        if player.gold <= 0:
            io.slow_out("  The stranger smiles. There is nothing to bet.")
            return
        if rng.randint(1, 20) > 10:
            gained = player.gold
            player.gold += gained
            io.slow_out(f"  Heads! The stranger pays out. +{gained} gold.")
        else:
            lost = player.gold
            player.gold = 0
            io.slow_out(f"  Tails. The stranger pockets {lost} gold.")
