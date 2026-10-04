"""Configuration loading and validation.

All game tuning lives in ``config.json``.  :func:`load_config` validates the
structure and raises :class:`ConfigError` with a precise message when
something is wrong, so misconfiguration fails loudly instead of crashing
mid-game with a confusing traceback.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from dark_rpg.registry import PluginRegistry  # noqa: F401  (re-exported for typing)


class ConfigError(Exception):
    """Raised when the config file is missing, malformed, or invalid."""


# ── structural requirements ──────────────────────────────────────────────

_GAME_KEYS = {"floor_count", "rooms_per_floor", "key_drop_chance", "turn_timer"}
_TURN_TIMER_KEYS = {"enabled", "seconds"}
_PLAYER_KEYS = {"hp", "atk", "defense", "gold", "food", "stamina"}
_STAMINA_KEYS = {
    "max", "cost_attack", "cost_heavy", "cost_defend_block",
    "cost_flee_fail", "regen_defend_idle", "exhaustion_restore",
}
_POSTURE_KEYS = {
    "max", "cost_attack", "cost_heavy", "cost_deflect", "cost_deflect_fail",
    "cost_dodge", "cost_dodge_fail", "hit_drain", "heavy_drain",
    "broken_dmg_mult", "broken_restore", "defend_regen", "flee_fail_cost",
}
_ENEMY_KEYS = {"name", "hp", "atk", "defense", "xp", "gold", "ai"}
_LOOT_KEYS = {"name", "stat", "bonus"}
_SHOP_KEYS = {"label", "cost", "stat", "bonus", "desc"}


def _require(section: Dict[str, Any], key: str, errors: list[str]) -> None:
    if key not in section:
        errors.append(f"missing key {key!r}")


def load_config(path: str = "config.json") -> Dict[str, Any]:
    """Load, validate and normalize ``config.json``."""
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except OSError as exc:
        raise ConfigError(f"Cannot open config file {path!r}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file {path!r} is not valid JSON: {exc}") from exc

    validate_config(cfg)
    return _normalize(cfg)


def _normalize(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON lists into game-friendly types (e.g. gold ranges → tuples)."""
    for enemy in cfg["enemies"]:
        enemy["gold"] = tuple(enemy["gold"])
    cfg["boss"]["gold"] = tuple(cfg["boss"]["gold"])
    return cfg


def validate_config(cfg: Any) -> None:
    """Raise :class:`ConfigError` if *cfg* is structurally invalid."""
    if not isinstance(cfg, dict):
        raise ConfigError("Config root must be a JSON object")

    errors: list[str] = []
    game = cfg.get("game")
    if isinstance(game, dict):
        for key in _GAME_KEYS:
            _require(game, key, errors)
        if isinstance(game.get("turn_timer"), dict):
            for key in _TURN_TIMER_KEYS:
                _require(game["turn_timer"], key, errors)
        if "floor_count" in game and not (isinstance(game["floor_count"], int) and game["floor_count"] > 0):
            errors.append("game.floor_count must be a positive integer")
        if "rooms_per_floor" in game and not (isinstance(game["rooms_per_floor"], int) and game["rooms_per_floor"] > 0):
            errors.append("game.rooms_per_floor must be a positive integer")
        if "key_drop_chance" in game and not (0 <= game["key_drop_chance"] <= 1):
            errors.append("game.key_drop_chance must be between 0 and 1")
        if isinstance(game.get("turn_timer"), dict) and not (
            isinstance(game["turn_timer"].get("seconds"), (int, float))
            and game["turn_timer"]["seconds"] > 0
        ):
            errors.append("game.turn_timer.seconds must be a positive number")
    else:
        errors.append("missing section 'game'")

    for section, keys in (("player", _PLAYER_KEYS), ("stamina", _STAMINA_KEYS), ("posture", _POSTURE_KEYS)):
        sec = cfg.get(section)
        if isinstance(sec, dict):
            for key in keys:
                _require(sec, key, errors)
        else:
            errors.append(f"missing section {section!r}")

    enemies = cfg.get("enemies")
    if isinstance(enemies, list) and enemies:
        for i, enemy in enumerate(enemies):
            if not isinstance(enemy, dict):
                errors.append(f"enemies[{i}] must be an object")
                continue
            for key in _ENEMY_KEYS:
                _require(enemy, key, errors)
            if isinstance(enemy.get("gold"), (list, tuple)) and len(enemy["gold"]) != 2:
                errors.append(f"enemies[{i}].gold must be a [min, max] pair")
            if not isinstance(enemy.get("ai"), dict) or not enemy.get("ai"):
                errors.append(f"enemies[{i}].ai must be a non-empty object")
            # optional: a special ability (lifesteal/drain/crit/revive)
            if "ability" in enemy and not isinstance(enemy["ability"], dict):
                errors.append(f"enemies[{i}].ability must be an object")
            # optional: per-status effect on hit (e.g. {"poison": 3})
            if "status_on_hit" in enemy and not isinstance(enemy["status_on_hit"], dict):
                errors.append(f"enemies[{i}].status_on_hit must be an object")
    else:
        errors.append("'enemies' must be a non-empty list")

    boss = cfg.get("boss")
    if isinstance(boss, dict):
        for key in _ENEMY_KEYS:
            _require(boss, key, errors)
    else:
        errors.append("missing section 'boss'")

    loot = cfg.get("loot_table")
    if isinstance(loot, list) and loot:
        for i, item in enumerate(loot):
            if not isinstance(item, dict):
                errors.append(f"loot_table[{i}] must be an object")
                continue
            _require(item, "name", errors)
            # every item needs a numeric bonus; stat is required for flat items
            if "bonus" not in item:
                errors.append(f"loot_table[{i}].bonus is required")
            if not item.get("slot"):  # flat (legacy) items must name a stat
                _require(item, "stat", errors)
            # optional equipment fields: slot (weapon/armor/trinket) + rarity
            if "slot" in item and item["slot"] not in (None, "weapon", "armor", "trinket"):
                errors.append(f"loot_table[{i}].slot must be null, weapon, armor, or trinket")
            if "rarity" in item and item["rarity"] not in ("common", "uncommon", "rare", "epic"):
                errors.append(f"loot_table[{i}].rarity must be common/uncommon/rare/epic")
    else:
        errors.append("'loot_table' must be a non-empty list")

    # optional: status effect definitions (name -> kind/power/duration)
    status = cfg.get("status_effects")
    if isinstance(status, list):
        for i, s in enumerate(status):
            if not isinstance(s, dict) or "name" not in s:
                errors.append(f"status_effects[{i}] must be an object with a 'name'")
    # optional: equipment slot definitions (slot -> base stat)
    slots = cfg.get("gear_slots")
    if isinstance(slots, dict):
        for key in slots:
            if key not in ("weapon", "armor", "trinket"):
                errors.append(f"gear_slots key {key!r} must be weapon/armor/trinket")
    # optional: rarity tuning (rarity -> {mult, weight})
    rarity = cfg.get("rarity")
    if isinstance(rarity, dict):
        for key in rarity:
            if key not in ("common", "uncommon", "rare", "epic"):
                errors.append(f"rarity key {key!r} must be common/uncommon/rare/epic")

    if not isinstance(cfg.get("room_flavors"), list) or not cfg.get("room_flavors"):
        errors.append("'room_flavors' must be a non-empty list of strings")

    weights = cfg.get("room_weights")
    if isinstance(weights, dict) and weights:
        for key, value in weights.items():
            if not isinstance(value, (int, float)) or value < 0:
                errors.append(f"room_weights[{key!r}] must be a non-negative number")
    else:
        errors.append("'room_weights' must be a non-empty object")

    shop = cfg.get("shop")
    if isinstance(shop, list) and shop:
        for i, item in enumerate(shop):
            if not isinstance(item, dict):
                errors.append(f"shop[{i}] must be an object")
                continue
            _require(item, "label", errors)
            _require(item, "cost", errors)
            _require(item, "desc", errors)
            kind = item.get("kind", "stat")
            if kind == "consume":
                _require(item, "item", errors)
            elif kind == "stat":
                _require(item, "stat", errors)
                _require(item, "bonus", errors)
            else:
                errors.append(f"shop[{i}].kind must be 'consume' or 'stat'")
    else:
        errors.append("'shop' must be a non-empty list")

    if errors:
        raise ConfigError("Invalid config: " + "; ".join(errors))
