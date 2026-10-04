"""Vault (treasure) room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class VaultEvent(RoomEvent):
    """A hidden vault: a bigger haul than a normal loot room, but it may be
    guarded.  The player either grabs the treasure or (with luck) finds it
    unguarded; sometimes a trap has been set around it."""

    id = "vault"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        io, rng = game.io, game.rng
        io.slow_out("  You find a hidden vault!")

        # 25% chance the vault is guarded by a (floor-appropriate) enemy.
        if rng.randint(1, 100) <= 25:
            from dark_rpg.world.enemies import pick_enemy_for_floor
            io.slow_out("  But it's guarded! Someone is waiting inside...")
            template = pick_enemy_for_floor(game.cfg, player.floor, rng)
            result = game.run_combat(player, template, player.floor, room_num=room_num)
            if result == "dead":
                game.stats.deaths += 1
                lines = player.apply_scar()
                if player.scars <= player.scar_limit():
                    for line in lines:
                        io.slow_out(line)
                else:
                    io.slow_out(lines[0])
                return
        self._grant_loot(game, player, big=True)

    @staticmethod
    def _grant_loot(game: Any, player: Any, big: bool) -> None:
        from dark_rpg.world.events.loot import LootEvent
        LootEvent().run(game, player, 0)
        if big and game.rng.randint(1, 100) <= 50:
            # a bonus gold find
            gold = game.rng.randint(10, 40)
            player.gold += gold
            game.io.slow_out(f"  You also find {gold} gold coins!")
