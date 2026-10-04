"""Merchant room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.io import Prompt
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class MerchantEvent(RoomEvent):
    """A shop.  One purchase per visit; leave by picking an invalid option.

    Items come in two flavours:

    * ``consume`` — adds a consumable (potion/rations/oil/poison vial) to the
      player's pouch.
    * ``stat`` — a flat permanent stat bonus (sharpener / bracer).

    Quality-of-life guard: you cannot waste gold on a health potion at full HP.
    """

    id = "merchant"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        shop = game.cfg["shop"]
        io = game.io
        io.slow_out("  A hooded merchant grins at you.")
        io.out(f"  Your gold: {player.gold}")
        io.out("")
        for i, item in enumerate(shop, 1):
            io.out(f"  [{i}] {item['label']}  ({item['cost']}g) — {item['desc']}")
        io.out(f"  [{len(shop) + 1}] Leave")

        choice = io.ask(Prompt("merchant", "  > ", {
            "gold": player.gold,
            "food": player.food,
            "hp": player.hp,
            "max_hp": player.max_hp,
        }))
        if not choice.strip().isdigit() or not (1 <= int(choice) <= len(shop)):
            io.slow_out("  You walk away.")
            return
        item = shop[int(choice) - 1]

        # You can't waste gold on a health potion at full HP.
        if item.get("kind") == "consume" and item.get("item") == "potion" \
                and player.hp >= player.max_hp:
            io.slow_out("  You're already at full health. The merchant pockets nothing.")
            return
        if player.gold < item["cost"]:
            io.slow_out(f"  Not enough gold. You need {item['cost']}g.")
            return

        player.gold -= item["cost"]
        if item.get("kind") == "consume":
            player.add_consumable(item["item"])
            io.slow_out(f"  {item['label']} acquired. {item['desc']}.")
        else:
            stat = item["stat"]
            old = getattr(player, stat)
            setattr(player, stat, old + item["bonus"])
            io.slow_out(f"  {item['label']} acquired. {stat.upper()} {old} → {old + item['bonus']}.")
