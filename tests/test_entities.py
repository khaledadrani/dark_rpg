"""Tests for entities: player init, level-ups, food, save roundtrips."""
from __future__ import annotations

from dark_rpg.entities import Entity, Player


def test_player_init(cfg):
    p = Player("Hero", cfg)
    assert p.hp == cfg["player"]["hp"] == p.max_hp
    assert p.atk == cfg["player"]["atk"]
    assert p.level == 1 and p.xp == 0 and p.scars == 0 and p.floor == 1
    assert not p.has_key
    assert p.is_alive()


def test_level_up_math(cfg):
    p = Player("Hero", cfg)
    threshold = cfg["game"]["xp_per_level"]  # level 1 -> 2 needs this many XP
    p.xp = threshold - 1
    assert p.try_level_up() == []
    assert p.level == 1

    p.xp = threshold  # exactly one level-up
    msgs = p.try_level_up()
    assert p.level == 2
    assert p.xp == 0
    assert p.max_hp == cfg["player"]["hp"] + cfg["game"]["level_hp"]
    assert p.atk == cfg["player"]["atk"] + cfg["game"]["level_atk"]
    assert msgs and "LEVEL UP" in msgs[0]


def test_multi_level_up(cfg):
    p = Player("Hero", cfg)
    step = cfg["game"]["xp_per_level"]
    p.xp = step + step * 2  # enough for levels 2 and 3
    p.try_level_up()
    assert p.level == 3


def test_eat_consumes_food(cfg):
    p = Player("Hero", cfg)
    p.food = 1
    hp = p.hp
    assert p.eat() == ""
    assert p.food == 0 and p.hp == hp


def test_eat_without_food_hurts(cfg):
    p = Player("Hero", cfg)
    p.food = 0
    hp = p.hp
    msg = p.eat()
    assert f"-{cfg['game']['hunger_damage']} HP" in msg
    assert p.hp == hp - cfg["game"]["hunger_damage"]


def test_entity_damage_clamps_at_zero():
    e = Entity("Dummy", hp=5, atk=1, defense=0)
    e.take_damage(99)
    assert e.hp == 0
    assert not e.is_alive()


def test_entity_to_from_dict_roundtrip():
    e = Entity("Goblin", hp=12, atk=3, defense=1, stamina=10)
    e.exhausted = True
    restored = Entity.from_dict(e.to_dict())
    assert restored.name == "Goblin"
    assert restored.hp == 12 and restored.exhausted is True


def test_player_save_roundtrip(cfg):
    p = Player("Hero", cfg)
    p.xp, p.level, p.gold, p.food = 55, 3, 42, 7
    p.floor, p.has_key, p.scars = 4, True, 2
    p.hp = 10

    restored = Player.from_dict(p.to_dict(), cfg)
    assert restored.to_dict() == p.to_dict()


def test_player_from_dict_rejects_missing_keys(cfg):
    data = Player("Hero", cfg).to_dict()
    del data["max_hp"]
    import pytest
    with pytest.raises(ValueError):
        Player.from_dict(data, cfg)


def test_player_from_dict_clamps_hp_to_max(cfg):
    p = Player("Hero", cfg)
    data = p.to_dict()
    data["hp"] = 9999
    restored = Player.from_dict(data, cfg)
    assert restored.hp == restored.max_hp
