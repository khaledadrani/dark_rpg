"""Room resolution: pick an event, run it, handle key/descend and death."""
from __future__ import annotations

from typing import Any, Literal

from dark_rpg.art import play_art, scenery_art
from dark_rpg.io import Prompt
from dark_rpg.save import save_game
from dark_rpg.world.events import get_event

RoomResult = Literal["alive", "dead", "descend"]


def run_room(game: Any, player: Any, room_num: int) -> RoomResult:
    """Resolve one room; returns how the room ended.

    * ``"alive"``  — room completed, player continues exploring
    * ``"descend"`` — player used the floor key and descended
    * ``"dead"``   — permanent game over (starvation, >5 scars, fatal wounds)
    """
    cfg, io, rng = game.cfg, game.io, game.rng
    io.clear()

    # ── pick the event first so the scenery art matches the room ─────────
    weights = cfg["room_weights"]
    event_id = rng.choices(list(weights.keys()), list(weights.values()), k=1)[0]
    event = get_event(event_id)

    # animated scenery reveal, then the flavor line
    play_art(io, scenery_art(event_id))
    flavor = rng.choice(cfg["room_flavors"])
    key_indicator = "  🗝  [KEY HELD]" if player.has_key else ""
    io.slow_out(f"\n  Room {room_num} — {flavor}{key_indicator}")
    io.pause("Enter room...")

    # food is consumed before the event (rest rooms give it back)
    msg = player.eat()
    if msg:
        io.slow_out(msg)
    if not player.is_alive():
        io.slow_out("  You collapse from starvation.")
        return "dead"

    event.run(game, player, room_num)

    # ── death checks ────────────────────────────────────────────────────
    if player.scars > player.scar_limit():
        io.slow_out("  You are too broken to continue. The dungeon claims you.")
        return "dead"
    if not player.is_alive():
        io.slow_out("  Your wounds finally take you.")
        return "dead"

    for line in player.status(cfg["game"]["floor_count"]):
        io.slow_out(line)

    # ── descend or keep exploring ───────────────────────────────────────
    if player.has_key:
        io.slow_out("\n  🗝  You hold the floor key.")
        choice = io.ask(Prompt(
            "descend",
            "  [D] Descend to next floor   [S] Stay and explore\n  > ",
            {"floor": player.floor},
        ))
        if choice.strip().lower() == "d":
            save_game(player, game.save_path)
            return "descend"

    save_game(player, game.save_path)
    io.pause()
    return "alive"
