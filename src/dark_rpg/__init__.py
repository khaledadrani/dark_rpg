"""dark_rpg — a terminal dungeon-crawl text RPG.

The game is built around two plugin systems:

* **Combat modes** (`dark_rpg.combat`) — swappable turn-resolution engines
  ("stamina" and "posture").  Add a new mode by subclassing
  :class:`dark_rpg.combat.base.CombatMode` and decorating it with
  ``@register_combat_mode``.
* **Room events** (`dark_rpg.world.events`) — swappable room content.  Add a
  new event by subclassing :class:`dark_rpg.world.events.base.RoomEvent` and
  decorating it with ``@register_event``.

Everything else (enemies, loot, shop, weights, tuning) is data-driven from
``config.json``.
"""

__version__ = "0.2.0"
