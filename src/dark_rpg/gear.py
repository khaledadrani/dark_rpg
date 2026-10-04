"""The equipment (gear) system.

Loot is no longer a pile of ever-growing flat bonuses.  The player carries a
small set of *equipment slots* (weapon / armor / trinket) plus an *accessory
pool* of permanent trinket bonuses.  Loot and shop gear **replace** what is
equipped in a slot rather than stacking on top of it, so stats can no longer
run away to absurd values by floor 10 — and every piece of loot becomes a real
decision (does this beat what I'm wearing?).

Everything is data-driven:

* ``config.json -> gear_slots``        — the slot names and their base stat.
* ``config.json -> loot_table``         — each entry has ``slot`` and a
  ``rarity`` (common/uncommon/rare/epic).  ``stat``/``bonus`` are used only for
  the legacy flat items (``slot: null``).
* ``config.json -> rarity``             — per-rarity stat multiplier + weights.

:func:`gear_power` scores a piece of equipment so the player can see at a glance
whether it is an upgrade or a downgrade.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

#: slot -> the base player stat it scales
DEFAULT_GEAR_SLOTS: Dict[str, str] = {
    "weapon": "atk",
    "armor": "defense",
    "trinket": "atk",
}

#: per-rarity tuning (stat multiplier, relative drop weight)
DEFAULT_RARITY: Dict[str, Dict[str, Any]] = {
    "common":   {"mult": 1.0, "weight": 60},
    "uncommon": {"mult": 1.4, "weight": 27},
    "rare":     {"mult": 1.9, "weight": 10},
    "epic":     {"mult": 2.5, "weight": 3},
}

RARITY_ORDER = ["common", "uncommon", "rare", "epic"]


def gear_power(item: Dict[str, Any], base_stat: int) -> int:
    """Score a piece of gear: its bonus scaled by its rarity.

    ``base_stat`` is the player's base stat for that slot (the number the bonus
    is expressed relative to); we score against the *bonus* itself for display
    simplicity, so the same item scores the same regardless of the wearer.
    """
    rarity = item.get("rarity", "common")
    mult = DEFAULT_RARITY.get(rarity, {"mult": 1.0})["mult"]
    # a flat legacy item (no slot) scores its raw bonus
    bonus = item.get("bonus", 0)
    return max(1, int(round(bonus * mult)))


def slot_label(slot: Optional[str]) -> str:
    return slot.title() if slot else "Flat"


def describe(item: Dict[str, Any]) -> str:
    """One-line human description of a loot/shop item."""
    rarity = item.get("rarity")
    name = item["name"]
    if item.get("slot"):
        return f"{name}  [{rarity} {item['slot']}] +{item['bonus']}"
    return f"{name}  +{item['bonus']} {item['stat'].upper()} (flat)"
