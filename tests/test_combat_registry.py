"""Plugin registry tests: combat modes and room events are pluggable."""
from __future__ import annotations

import pytest

from dark_rpg.combat import (
    CombatModeError,
    available_combat_modes,
    get_combat_mode,
)
from dark_rpg.combat.base import CombatMode
from dark_rpg.registry import PluginRegistry
from dark_rpg.world.events import EVENTS, event_ids, get_event
from dark_rpg.world.events.base import RoomEvent


def test_plugin_registry_basics():
    reg = PluginRegistry("thing")

    @reg.decorator("alpha")
    class Alpha:
        pass

    assert reg.get("alpha") is Alpha
    assert reg.has("alpha") and not reg.has("beta")
    assert reg.keys() == ["alpha"]

    with pytest.raises(ValueError):
        reg.register("alpha", object())  # duplicate key rejected

    with pytest.raises(KeyError) as exc:
        reg.get("nope")
    assert "alpha" in str(exc.value)


def test_builtin_combat_modes_are_registered():
    assert set(available_combat_modes()) == {"stamina", "posture"}
    for key in available_combat_modes():
        assert issubclass(get_combat_mode.__globals__["COMBAT_MODES"].get(key), CombatMode)


def test_unknown_combat_mode_raises_combat_mode_error(cfg):
    with pytest.raises(CombatModeError) as exc:
        get_combat_mode("space-magic", cfg)
    assert "stamina" in str(exc.value) and "posture" in str(exc.value)


def test_builtin_events_are_registered():
    assert set(event_ids()) == {
        "enemy", "loot", "rest", "trap", "merchant", "shrine",
        "vault", "curse", "ambush", "gamble", "secret",
    }
    for event_id in event_ids():
        assert isinstance(get_event(event_id), RoomEvent)


def test_registry_rejects_non_plugin_types():
    from dark_rpg.combat import register_combat_mode

    with pytest.raises(TypeError):
        register_combat_mode(int)


def test_room_weights_all_map_to_registered_events(cfg):
    for event_id in cfg["room_weights"]:
        assert EVENTS.has(event_id), f"room_weights references unregistered event {event_id!r}"
