"""Save/load tests: roundtrips, atomicity, corruption handling."""
from __future__ import annotations

import json

import pytest

from dark_rpg.entities import Player
from dark_rpg.save import SaveError, delete_save, load_game, save_game


def test_save_load_roundtrip(cfg, tmp_path):
    path = str(tmp_path / "save.json")
    p = Player("Hero", cfg)
    p.xp, p.level, p.floor, p.gold, p.food = 60, 3, 4, 30, 5
    p.has_key, p.scars = True, 1

    save_game(p, path)
    loaded = load_game(path, cfg)
    assert loaded.to_dict() == p.to_dict()


def test_save_is_atomic_and_no_tmp_left_behind(cfg, tmp_path):
    path = str(tmp_path / "save.json")
    p = Player("Hero", cfg)
    save_game(p, path)
    assert not (tmp_path / "save.json.tmp").exists()


def test_corrupt_json_raises_save_error(cfg, tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{definitely not json")
    with pytest.raises(SaveError):
        load_game(str(path), cfg)


def test_missing_save_file_raises_save_error(cfg, tmp_path):
    with pytest.raises(SaveError):
        load_game(str(tmp_path / "nope.json"), cfg)


def test_incomplete_save_raises_save_error(cfg, tmp_path):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"name": "Hero"}))  # missing most keys
    with pytest.raises(SaveError):
        load_game(str(path), cfg)


def test_delete_save(cfg, tmp_path):
    path = tmp_path / "save.json"
    save_game(Player("Hero", cfg), str(path))
    assert path.exists()
    delete_save(str(path))
    assert not path.exists()
    delete_save(str(path))  # no-op on missing file
