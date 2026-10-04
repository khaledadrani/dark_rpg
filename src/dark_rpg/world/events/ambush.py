"""Ambush room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.enemies import pick_enemy_for_floor
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class AmbushEvent(RoomEvent):
    """You are ambushed: the enemy strikes first, so you start the fight at a
    disadvantage (a free hit that can't be defended against).  A higher-risk
    version of a normal enemy room that still drops the floor key on a win."""

    id = "ambush"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        template = pick_enemy_for_floor(game.cfg, player.floor, game.rng)
        io, rng = game.io, game.rng
        io.slow_out(f"  ⚠  Ambush! A {template['name']} springs from the shadows!")
        # The ambusher lands one free strike before the duel begins.
        base_dmg = max(1, int(template["atk"] * 0.6) - player.defense)
        player.take_damage(base_dmg)
        io.slow_out(f"  The first blow catches you off guard: -{base_dmg} HP.")
        if not player.is_alive():
            return

        result = game.run_combat(player, template, player.floor, room_num=room_num)
        if result == "dead":
            game.stats.deaths += 1
            lines = player.apply_scar()
            if player.scars <= player.scar_limit():
                for line in lines:
                    io.slow_out(line)
            else:
                io.slow_out(lines[0])
