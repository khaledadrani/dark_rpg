"""Enemy selection and scaling.

Enemies are pure data in ``config.json``; this module picks one for the
current floor and scales it.  Higher-tier enemies (later in the list) get
less aggressive floor scaling, and the boss is created with
``scale_override=1.0`` so it always fights at its raw stats.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from dark_rpg.combat.base import CombatMode
from dark_rpg.entities import Entity
from dark_rpg.status import apply_status


def pick_enemy_for_floor(cfg: Dict[str, Any], floor: int, rng: random.Random) -> Dict[str, Any]:
    """Weight the enemy pool toward tougher enemies as the floor rises."""
    enemies = cfg["enemies"]
    max_idx = min((floor + 1) // 2, len(enemies) - 1)
    idx = rng.randint(max(0, max_idx - 1), max_idx)
    return enemies[idx]


def scale_factor(
    cfg: Dict[str, Any],
    template: Dict[str, Any],
    floor: int,
    enemy_list: Optional[List[Dict[str, Any]]] = None,
    scale_override: Optional[float] = None,
) -> float:
    """Compute the stat multiplier for *template* at *floor*.

    Tuning knobs (config.json -> game): ``floor_scale`` grows stats per
    floor, ``tier_scale`` discounts later (tougher) enemy tiers.
    """
    if scale_override is not None:
        return scale_override
    floor_scale = cfg["game"].get("floor_scale", 0.15)
    tier_scale = cfg["game"].get("tier_scale", 0.1)
    tier_discount = 0.0
    if enemy_list and template in enemy_list:
        tier_discount = enemy_list.index(template) * tier_scale
    return max(1.0, 1 + (floor - 1) * floor_scale - tier_discount)


def make_combatant(
    cfg: Dict[str, Any],
    mode: CombatMode,
    template: Dict[str, Any],
    floor: int,
    scale_override: Optional[float] = None,
    enemy_list: Optional[List[Dict[str, Any]]] = None,
) -> Entity:
    """Build a scaled enemy combatant for the given combat mode."""
    scale = scale_factor(cfg, template, floor, enemy_list, scale_override)
    enemy = Entity(
        name=template["name"],
        hp=int(template["hp"] * scale),
        atk=int(template["atk"] * scale),
        defense=int(template["defense"] * scale),
        stamina=mode.max_stamina(),
    )
    enemy.xp = template["xp"]
    enemy.gold = template["gold"]  # normalized to a (min, max) tuple by load_config
    # the raw template drives special abilities (lifesteal/drain/crit/revive)
    enemy.template = template
    return enemy
