"""Room event plugin registry.

Built-in events live in sibling modules and self-register via
``@register_event``.  Add a new event anywhere: subclass
:class:`~dark_rpg.world.events.base.RoomEvent`, decorate it, and (optionally)
add its id to ``config.json -> room_weights``.
"""
from __future__ import annotations

from dark_rpg.registry import PluginRegistry
from dark_rpg.world.events.base import RoomEvent

EVENTS: PluginRegistry[RoomEvent] = PluginRegistry("room event")


def register_event(cls: type) -> type:
    """Class decorator that registers a :class:`RoomEvent` subclass."""
    if not (isinstance(cls, type) and issubclass(cls, RoomEvent)):
        raise TypeError("register_event expects a RoomEvent subclass")
    EVENTS.register(cls.id, cls())
    return cls


def get_event(event_id: str) -> RoomEvent:
    return EVENTS.get(event_id)


def event_ids() -> list:
    return EVENTS.keys()


# ── register the built-in events (imports trigger the decorators) ───────
from dark_rpg.world.events import ambush  # noqa: E402,F401
from dark_rpg.world.events import curse  # noqa: E402,F401
from dark_rpg.world.events import enemy  # noqa: E402,F401
from dark_rpg.world.events import gamble  # noqa: E402,F401
from dark_rpg.world.events import loot  # noqa: E402,F401
from dark_rpg.world.events import merchant  # noqa: E402,F401
from dark_rpg.world.events import rest  # noqa: E402,F401
from dark_rpg.world.events import secret  # noqa: E402,F401
from dark_rpg.world.events import shrine  # noqa: E402,F401
from dark_rpg.world.events import trap  # noqa: E402,F401
from dark_rpg.world.events import vault  # noqa: E402,F401
