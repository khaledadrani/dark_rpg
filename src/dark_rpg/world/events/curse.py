"""Curse room event."""
from __future__ import annotations

from typing import Any

from dark_rpg.status import apply_status
from dark_rpg.world.events import register_event
from dark_rpg.world.events.base import RoomEvent


@register_event
class CurseEvent(RoomEvent):
    """A cursed altar.  The player is afflicted with a temporary status
    effect (e.g. poison) that will bite back during the next fights, but the
    altar may also have been disarmed by an earlier adventurer (a small heal)."""

    id = "curse"

    def run(self, game: Any, player: Any, room_num: int) -> None:
        io, rng = game.io, game.rng
        # 75% of the time the curse is live; otherwise it has been disarmed.
        if rng.randint(1, 100) <= 75:
            # pick a DoT from the config (poison preferred if present)
            curses = [s["name"] for s in game.cfg.get("status_effects", [])
                      if s.get("kind") in ("poison", "burn")]
            if not curses:
                curses = ["poison"]
            kind = rng.choice(curses)
            specs = {s["name"]: s for s in game.cfg.get("status_effects", [])}
            spec = specs.get(kind, {"power": 2, "duration": 3})
            apply_status(player, kind, spec.get("duration", 3), spec.get("power", 2))
            io.slow_out(
                f"  A dark altar clutches at you! You are {kind}ed for the "
                f"next {spec.get('duration', 3)} turns of combat."
            )
        else:
            heal = rng.randint(4, 10)
            player.hp = min(player.max_hp, player.hp + heal)
            io.slow_out(
                f"  The altar has been disarmed by an earlier soul. "
                f"Its blessing lingers: +{heal} HP."
            )
