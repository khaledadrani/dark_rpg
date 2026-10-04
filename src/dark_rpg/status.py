"""Status effects (burn / poison / ...).

A :class:`StatusEffect` is a small piece of per-entity state that ticks each
turn: it deals (or heals) damage, counts down, and reports whether it is still
active.  Effects are data-driven from ``config.json -> status_effects`` so new
kinds can be added without touching combat code.

Both combat modes apply effects through a single shared hook
(:func:`tick_statuses`), so adding a status never diverges the two modes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StatusEffect:
    """A single active status on a combatant.

    * ``kind``     — registry key, e.g. ``"burn"`` or ``"poison"``
    * ``duration`` — remaining turns (decrements each tick)
    * ``power``    — per-tick magnitude (damage for DoTs)
    """

    kind: str
    duration: int
    power: int
    data: Dict = field(default_factory=dict)

    def is_active(self) -> bool:
        return self.duration > 0

    def to_dict(self) -> Dict[str, Any]:
        return {"kind": self.kind, "duration": self.duration,
                "power": self.power, "data": self.data}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusEffect":
        return cls(kind=data["kind"], duration=data["duration"],
                   power=data["power"], data=data.get("data", {}))


def tick_statuses(entity, cfg: dict, rng) -> List[str]:
    """Advance every status on *entity* by one turn; return messages.

    Damage-over-time effects deal damage each tick.  The ``rng`` argument is
    reserved for future probabilistic effects (e.g. a 50% poison tick); it is
    currently unused so determinism is preserved.
    """
    statuses: List[StatusEffect] = getattr(entity, "statuses", None) or []
    specs = {s["name"]: s for s in cfg.get("status_effects", [])}
    msgs: List[str] = []

    for status in list(statuses):
        if not status.is_active():
            continue
        spec = specs.get(status.kind, {})
        per_tick = status.power
        if spec.get("kind") in ("burn", "poison"):
            entity.take_damage(per_tick)
            msgs.append(
                f"  ☣  {entity.name} is {status.kind}ing — {per_tick} damage."
            )
        elif spec.get("kind") == "regen":
            healed = min(per_tick, entity.max_hp - entity.hp)
            entity.hp = min(entity.max_hp, entity.hp + per_tick)
            if healed:
                msgs.append(f"  ✚  {entity.name} regenerates {healed} HP.")
        status.duration -= 1
        if not status.is_active():
            msgs.append(f"  {entity.name} is no longer {status.kind}.")

    # drop expired effects
    entity.statuses = [s for s in statuses if s.is_active()]
    return msgs


def apply_status(entity, kind: str, duration: int, power: int) -> None:
    """Add (or refresh) a status of *kind* on *entity*.

    Stacking rule: a fresh application replaces an existing effect of the same
    kind with the *stronger* of the two (longer duration / higher power), so
    repeated poisons don't snowball.
    """
    entity.statuses = getattr(entity, "statuses", None) or []
    for s in list(entity.statuses):
        if s.kind == kind:
            s.duration = max(s.duration, duration)
            s.power = max(s.power, power)
            return
    entity.statuses.append(StatusEffect(kind=kind, duration=duration, power=power))
