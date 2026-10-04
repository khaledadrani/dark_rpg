"""Game entities.

Both combat modes operate on the same :class:`Entity` shape: ``hp``/``atk``/
``defense`` for damage, plus ``stamina`` (interpreted as stamina *or* posture
depending on the active combat mode), and two state flags:

* ``exhausted`` — used by the stamina combat mode (forced recovery turn).
* ``broken``   — used by the posture combat mode (forced recovery turn).

:class:`Player` extends :class:`Entity` with progression and run state.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List

from dark_rpg.status import apply_status
from dark_rpg.ui import bar


def crit_amplify(attacker: "Entity", dmg: int, template: Dict[str, Any], rng: random.Random) -> int:
    """If *attacker*'s template carries a crit ability, roll it and return the
    (possibly amplified) damage.  Otherwise returns *dmg* unchanged."""
    ability = (template or {}).get("ability") or {}
    if ability.get("type") == "crit" and rng.random() < ability.get("chance", 0.2):
        return int(dmg * ability.get("mult", 2.0))
    return dmg


def apply_post_hit(
    attacker: "Entity",
    defender: "Entity",
    dmg: int,
    template: Dict[str, Any],
    cfg: Dict[str, Any],
    rng: random.Random,
) -> List[str]:
    """After *attacker* hits *defender* for *dmg*, apply the attacker's
    ongoing special effects (status-on-hit, lifesteal, drain, revive).
    Returns the messages to display."""
    msgs: List[str] = []
    template = template or {}
    ability = template.get("ability") or {}

    soh = template.get("status_on_hit") or {}
    if soh and dmg > 0:
        kind = next(iter(soh))
        power = soh[kind]
        specs = {s["name"]: s for s in cfg.get("status_effects", [])}
        spec = specs.get(kind, {})
        duration = spec.get("duration", 3)
        apply_status(defender, kind, duration, max(power, spec.get("power", power)))
        msgs.append(f"  ☣  {defender.name} is {kind}ed!")

    if ability.get("type") == "lifesteal" and dmg > 0:
        if rng.random() < ability.get("chance", 0.5):
            healed = int(dmg * ability.get("fraction", 0.5))
            healed = min(healed, attacker.max_hp - attacker.hp)
            if healed > 0:
                attacker.hp = min(attacker.max_hp, attacker.hp + healed)
                msgs.append(f"  🩸  {attacker.name} drains {healed} HP!")

    if ability.get("type") == "drain" and dmg > 0:
        amount = ability.get("amount", 3)
        defender.spend_sta(amount)
        attacker.regen_sta(amount)
        msgs.append(f"  👻  {attacker.name} drains {amount} stamina/posture from {defender.name}!")

    if ability.get("type") == "revive":
        if defender.hp <= 0 and not getattr(defender, "_revived", False):
            defender._revived = True
            revived_hp = max(1, int(defender.max_hp * ability.get("fraction", 0.4)))
            defender.hp = revived_hp
            msgs.append(f"  ✨  {defender.name} reconstitutes from dust! ({revived_hp} HP)")

    return msgs


class Entity:
    """Base combatant: a bag of stats plus HP/stamina bookkeeping."""

    def __init__(self, name: str, hp: int, atk: int, defense: int, stamina: int = 10) -> None:
        self.name = name
        self.hp = hp
        self.max_hp = hp
        self.atk = atk
        self.defense = defense
        self.stamina = stamina
        self.max_sta = stamina
        self.exhausted = False
        self.broken = False
        # active status effects (burn/poison/...); list of StatusEffect
        self.statuses: List[Any] = []
        # raw config template driving special abilities (default: none)
        self.template: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return (f"{type(self).__name__}({self.name!r}, hp={self.hp}/{self.max_hp}, "
                f"atk={self.atk}, def={self.defense}, sta={self.stamina}/{self.max_sta})")

    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, dmg: int) -> None:
        self.hp = max(0, self.hp - dmg)

    def spend_sta(self, cost: int) -> None:
        """Spend stamina/posture; clamps at 0 (never negative)."""
        self.stamina = max(0, self.stamina - cost)

    def regen_sta(self, amount: int) -> None:
        self.stamina = min(self.max_sta, self.stamina + amount)

    def set_stamina_pool(self, amount: int) -> None:
        """Normalize this entity to a stamina pool (called at combat start)."""
        self.max_sta = amount
        self.stamina = amount

    # Effective stats: base stat plus any equipment/accessory bonuses.  The
    # gear/accessory fields only exist on Player; for a plain Entity they are
    # absent, so effective stats simply equal the base stats.
    @property
    def effective_atk(self) -> int:
        return self.atk + self._gear_bonus("atk")

    @property
    def effective_defense(self) -> int:
        return self.defense + self._gear_bonus("defense")

    def _gear_bonus(self, stat: str) -> int:
        bonus = 0
        gear = getattr(self, "gear", None)
        if gear:
            for item in gear.values():
                if item and item.get("stat") == stat:
                    bonus += item.get("bonus", 0)
        accessories = getattr(self, "accessories", None)
        if accessories:
            bonus += accessories.get(stat, 0)
        return bonus

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        e = cls.__new__(cls)
        e.__dict__.update(data)
        return e


class Player(Entity):
    """The player character: Entity + XP/level, gold, food, scars, run state,
    equipment (gear slots + accessory pool), and consumables."""

    #: the equipment slot names; ``player.gear[slot]`` holds the item dict
    GEAR_SLOTS = ("weapon", "armor", "trinket")

    SAVE_KEYS = {
        "name", "hp", "max_hp", "atk", "defense", "stamina", "max_sta",
        "exhausted", "broken", "xp", "level", "gold", "food", "combo",
        "scars", "floor", "has_key", "gear", "accessories", "consumables",
    }

    def __init__(self, name: str, cfg: Dict[str, Any]) -> None:
        p = cfg["player"]
        super().__init__(name, p["hp"], p["atk"], p["defense"], p["stamina"])
        self.xp = 0
        self.level = 1
        self.gold = p["gold"]
        self.food = p["food"]
        self.combo = 0
        self.scars = 0
        self.floor = 1
        self.has_key = False
        # equipment: {slot: item_dict or None}
        self.gear: Dict[str, Optional[Dict[str, Any]]] = {
            slot: None for slot in self.GEAR_SLOTS
        }
        # flat permanent bonuses from trinkets found as loot
        self.accessories: Dict[str, int] = {}
        # consumable pouch: {"potion": n, "rations": n, ...}
        self.consumables: Dict[str, int] = {}
        # tuning knobs (kept off the save file via to_dict)
        self._game_cfg = cfg["game"]

    # ── equipment / effective stats ─────────────────────────────────────
    @property
    def effective_atk(self) -> int:
        """Base ATK + weapon bonus + trinket/flat bonuses.

        Equipment *replaces* a slot (it does not stack with a previous item in
        the same slot), which is what keeps late-game stats from exploding.
        """
        total = self.atk
        for slot, item in self.gear.items():
            if item:
                total += item.get("bonus", 0)
        total += self.accessories.get("atk", 0)
        return total

    @property
    def effective_defense(self) -> int:
        total = self.defense
        for slot, item in self.gear.items():
            if item:
                total += item.get("bonus", 0)
        total += self.accessories.get("defense", 0)
        return total

    def equip(self, item: Dict[str, Any]) -> None:
        """Put *item* into its slot (replacing whatever was there) or add a
        flat accessory bonus.  Loot always *replaces* — it never stacks."""
        slot = item.get("slot")
        if slot and slot in self.gear:
            self.gear[slot] = item
        else:
            stat = item.get("stat", "atk")
            self.accessories[stat] = self.accessories.get(stat, 0) + item.get("bonus", 0)

    # ── progression ─────────────────────────────────────────────────────
    def xp_to_next(self) -> int:
        return self._game_cfg.get("xp_per_level", 40) * self.level

    def try_level_up(self) -> List[str]:
        """Apply all pending level-ups; returns the messages to display."""
        hp_bonus = self._game_cfg.get("level_hp", 8)
        atk_bonus = self._game_cfg.get("level_atk", 2)
        msgs: List[str] = []
        while self.xp >= self.xp_to_next():
            self.xp -= self.xp_to_next()
            self.level += 1
            self.max_hp += hp_bonus
            self.hp = min(self.hp + hp_bonus, self.max_hp)
            self.atk += atk_bonus
            msgs.append(f"\n  ✦ LEVEL UP! You are now level {self.level}.")
            msgs.append(f"    Max HP +{hp_bonus} | ATK +{atk_bonus}")
        return msgs

    # ── display ─────────────────────────────────────────────────────────
    def status(self, floor_count: int) -> List[str]:
        lines = [
            f"\n  {self.name}  |  Level {self.level}  |  Floor {self.floor}/{floor_count}",
            f"  HP  {bar(self.hp, self.max_hp)}",
            f"  STA {bar(self.stamina, self.max_sta, width=10)}",
            f"  XP  {bar(self.xp, self.xp_to_next())}",
            f"  ATK {self.effective_atk}  DEF {self.effective_defense}  GOLD {self.gold}  FOOD {self.food}",
        ]
        # equipment summary (only non-empty slots)
        equipped = [(s, i["name"]) for s, i in self.gear.items() if i]
        if equipped:
            lines.append("  Gear: " + " · ".join(f"{s} {n}" for s, n in equipped))
        # consumables summary
        carried = [f"{k}×{v}" for k, v in self.consumables.items() if v]
        if carried:
            lines.append("  Pouch: " + "  ".join(carried))
        if self.scars:
            penalty = self._game_cfg.get("scar_penalty", 5)
            lines.append(f"  Scars: {'⚔ ' * self.scars} (max HP reduced by {self.scars * penalty})")
        return lines

    # ── survival ────────────────────────────────────────────────────────
    def eat(self) -> str:
        """Consume one food.  Without food, hunger deals configurable damage.

        Returns a message to display (empty string when nothing happens).
        """
        if self.food <= 0:
            hunger = self._game_cfg.get("hunger_damage", 2)
            self.hp = max(0, self.hp - hunger)
            return f"  You have no food left. Hunger gnaws at you (-{hunger} HP)."
        self.food -= 1
        return ""

    def apply_scar(self) -> List[str]:
        """Death penalty (tuning from config): max HP −penalty, revive at
        half HP, scar count +1.  Returns the lines to display; the "wake"
        line should only be shown when the player survives (scar_limit)."""
        penalty = self._game_cfg.get("scar_penalty", 5)
        self.max_hp = max(10, self.max_hp - penalty)
        self.hp = self.max_hp // 2
        self.scars += 1
        return [
            "\n  You fall...",
            f"  A scar remains. Max HP -{penalty}. You wake with {self.hp} HP.",
        ]

    def scar_limit(self) -> int:
        return self._game_cfg.get("scar_limit", 5)

    # ── consumables ─────────────────────────────────────────────────────
    def has_consumable(self, key: str) -> bool:
        return self.consumables.get(key, 0) > 0

    def use_consumable(self, key: str, n: int = 1) -> int:
        """Consume *n* of the consumable *key*; returns the amount used."""
        have = self.consumables.get(key, 0)
        used = min(n, have)
        if used:
            self.consumables[key] = have - used
        return used

    def add_consumable(self, key: str, n: int = 1) -> None:
        self.consumables[key] = self.consumables.get(key, 0) + n

    # ── save / load ─────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        data = dict(self.__dict__)
        data.pop("_game_cfg", None)  # tuning is not player state
        data["statuses"] = [s.to_dict() for s in self.statuses]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any], cfg: Dict[str, Any]) -> "Player":
        """Rebuild a player from a save dict; validates required keys."""
        missing = cls.SAVE_KEYS - set(data)
        if missing:
            raise ValueError(f"save file missing keys: {sorted(missing)}")
        player = cls(data["name"], cfg)
        statuses = data.pop("statuses", []) or []
        for key, value in data.items():
            setattr(player, key, value)
        player.statuses = [StatusEffect.from_dict(s) for s in statuses]
        player.hp = min(player.hp, player.max_hp)
        return player
