"""Loot room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.gear import describe
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class LootEvent(RoomEvent):
    """Find a piece of loot from ``config.loot_table``.

    Items with a ``slot`` are equipment that replaces whatever is currently
    equipped in that slot; items without a slot grant a one-off flat bonus or
    grant a consumable (fire flask / poison vial) into the player's pouch.
    """

    id = "loot"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        item = game.rng.choice(game.cfg["loot_table"])
        io = game.io
        if item.get("slot"):
            old = getattr(player, item["stat"], 0)
            player.equip(item)
            io.slow_out(
                f"  You find a {item['name']}! Equipped "
                f"{item['stat'].upper()} {old} → {getattr(player, item['stat'])}."
            )
        elif item.get("stat") in ("burn", "poison"):
            player.add_consumable(item["stat"] if item["stat"] == "poison" else "oil", item["bonus"])
            io.slow_out(
                f"  You find a {item['name']}! It's tucked into your pouch "
                f"for later use in combat."
            )
        else:
            old = getattr(player, item["stat"], 0)
            setattr(player, item["stat"], old + item["bonus"])
            io.slow_out(
                f"  You find a {item['name']}! {item['stat'].upper()} +{item['bonus']} "
                f"({old} → {old + item['bonus']})"
            )
