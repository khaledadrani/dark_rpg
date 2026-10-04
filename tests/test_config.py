"""Tests for config loading and validation."""
from __future__ import annotations

import json

import pytest

from dark_rpg.combat import CombatModeError, available_combat_modes, get_combat_mode
from dark_rpg.config import ConfigError, load_config
from dark_rpg.app import Game


def test_loads_default_config(cfg):
    assert cfg["game"]["floor_count"] == 10
    assert cfg["game"]["combat_mode"] in available_combat_modes()
    assert cfg["game"]["turn_timer"]["seconds"] == 60  # user decision: 60s stays
    assert isinstance(cfg["enemies"][0]["gold"], tuple)  # normalized
    assert isinstance(cfg["boss"]["gold"], tuple)


def test_turn_timer_is_configurable(game_cfg, tmp_path):
    game_cfg["game"]["turn_timer"] = {"enabled": True, "seconds": 7}
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(game_cfg))
    assert load_config(str(p))["game"]["turn_timer"]["seconds"] == 7


def test_missing_section_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"game": {"floor_count": 10}}))
    with pytest.raises(ConfigError):
        load_config(str(p))


def test_bad_json_raises(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    with pytest.raises(ConfigError):
        load_config(str(p))


def test_unknown_combat_mode_fails_loudly(game_cfg):
    game_cfg["game"]["combat_mode"] = "banana"
    with pytest.raises(CombatModeError) as exc:
        Game(game_cfg)
    assert "banana" in str(exc.value)
    assert "stamina" in str(exc.value)


def test_every_registered_mode_is_instantiable(cfg):
    for key in available_combat_modes():
        mode = get_combat_mode(key, cfg)
        assert mode.key == key
        assert mode.max_stamina() > 0
        assert mode.action_menu()  # non-empty menu
