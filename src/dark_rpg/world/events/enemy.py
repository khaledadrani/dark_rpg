"""Enemy encounter room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.enemies import pick_enemy_for_floor
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class EnemyEvent(RoomEvent):
    """Fight a scaled enemy.  Losing applies a scar and revives the player
    at half HP; more than 5 scars is permanent death."""

    id = "enemy"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        template = pick_enemy_for_floor(game.cfg, player.floor, game.rng)
        result = game.run_combat(player, template, player.floor, room_num=room_num)
        if result == "dead":
            game.stats.deaths += 1
            lines = player.apply_scar()
            if player.scars <= player.scar_limit():
                # surviving: show the full scar message (fall + wake)
                for line in lines:
                    game.io.slow_out(line)
            else:
                # final death: only the fall — run_room prints the verdict
                game.io.slow_out(lines[0])
