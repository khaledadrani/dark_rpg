"""Secret passage room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class SecretEvent(RoomEvent):
    """Un escondite con un hallazgo doble: comida recuperada y una pequeña
    cantidad de oro escondido. A veces la pared guarda una trampa."""

    id = "secret"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        io, rng = game.io, game.rng
        food = rng.randint(2, 5)
        gold = rng.randint(3, 9)
        player.food += food
        player.gold += gold
        io.slow_out(f"  Pasadizo secreto: hallas un alijo (+{food} comida, +{gold} oro).")
        # 20%: la pared guarda un dardo
        if rng.randint(1, 100) <= 20:
            dmg = rng.randint(2, 5)
            player.take_damage(dmg)
            io.slow_out(f"  ¡Un dardo oculto te alcanza! -{dmg} HP.")
