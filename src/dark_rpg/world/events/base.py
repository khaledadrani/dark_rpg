"""Room event plugin interface.

A room event is a small self-contained scene that mutates the player (and/or
the world).  Events are dispatched by id from ``config.json ->
room_weights``; the weight decides how often each event fires.

To add a new event:

1. Subclass :class:`RoomEvent`, set a unique ``id``, implement ``run``.
2. Decorate with ``@register_event``.
3. Optionally add it to ``room_weights`` in ``config.json``.

No other code changes are required.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class RoomEvent(ABC):
    """One kind of room encounter."""

    #: unique registry key matching a key in ``config.room_weights``
    id: str = ""

    @abstractmethod
    def run(self, game: Any, player: Any, room_num: int) -> None:
        """Execute the event.

        *game* is the running :class:`dark_rpg.app.Game` (use ``game.io``,
        ``game.rng``, ``game.cfg``, ``game.run_combat``, ...).
        *player* is the player character.  Death is communicated by the
        player's state afterwards (``hp <= 0`` or ``scars > 5``).
        """
