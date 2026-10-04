"""A minimal plugin registry.

The game uses two registries: combat modes (:data:`dark_rpg.combat.COMBAT_MODES`)
and room events (:data:`dark_rpg.world.events.EVENTS`).  Any new plugin simply
registers itself with a unique string key; the core dispatch code never needs
to change.

Example::

    from dark_rpg.registry import PluginRegistry

    things = PluginRegistry("thing")

    @things.decorator("my_thing")
    class MyThing:
        ...

    things.get("my_thing")  # the class
"""
from __future__ import annotations

from typing import Dict, Generic, List, TypeVar

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Maps string keys to plugin objects (classes or instances)."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._items: Dict[str, T] = {}

    def register(self, key: str, item: T) -> T:
        """Register *item* under *key*; raises on duplicate keys."""
        if key in self._items:
            raise ValueError(f"{self.kind} {key!r} is already registered")
        self._items[key] = item
        return item

    def decorator(self, key: str):
        """Use as a class/function decorator: ``@reg.decorator("name")``."""
        def wrap(item: T) -> T:
            return self.register(key, item)
        return wrap

    def get(self, key: str) -> T:
        """Fetch a plugin; raises KeyError with a helpful message."""
        try:
            return self._items[key]
        except KeyError:
            available = ", ".join(sorted(self._items)) or "(none)"
            raise KeyError(
                f"Unknown {self.kind} {key!r}; available: {available}"
            ) from None

    def has(self, key: str) -> bool:
        return key in self._items

    def all(self) -> Dict[str, T]:
        return dict(self._items)

    def keys(self) -> List[str]:
        return sorted(self._items)
