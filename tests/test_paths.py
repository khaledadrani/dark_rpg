"""Tests for the installed-game file locations (config home, save path).

These lock in the behavior that makes ``dark-rpg`` work as a global ``uv tool``:
the save file and a personal config live in ``~/.config/dark_rpg/`` so the game
continues from any working directory.
"""
from __future__ import annotations

from pathlib import Path


from dark_rpg import paths


def test_user_config_dir_default(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("HOME", "/tmp/fakehome")
    d = paths.user_config_dir()
    assert d == Path("/tmp/fakehome/.config/dark_rpg")
    assert d.is_dir()  # created on demand


def test_user_config_dir_xdg(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg")
    d = paths.user_config_dir()
    assert d == Path("/tmp/xdg/dark_rpg")
    assert d.is_dir()


def test_default_save_path_home(monkeypatch):
    monkeypatch.delenv("DARK_RPG_SAVE", raising=False)
    monkeypatch.setenv("HOME", "/tmp/fakehome2")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    p = paths.default_save_path()
    assert p == Path("/tmp/fakehome2/.config/dark_rpg/save.json")


def test_default_save_path_env_override(monkeypatch, tmp_path):
    target = tmp_path / "custom" / "save.json"
    monkeypatch.setenv("DARK_RPG_SAVE", str(target))
    p = paths.default_save_path()
    assert p == target
    assert p.parent.is_dir()  # parent dir created


def test_resolve_config_prefers_explicit_existing(tmp_path):
    p = tmp_path / "my.json"
    p.write_text("{}")
    assert paths.resolve_config_path(str(p)) == p


def test_resolve_config_falls_back_to_cwd(monkeypatch, tmp_path):
    # No --config, no user config, no packaged config -> ./config.json
    monkeypatch.chdir(tmp_path)  # clean dir, no config.json present
    monkeypatch.setattr(paths, "user_config_dir", lambda: tmp_path / "nope")
    monkeypatch.setattr(paths, "_packaged_config", lambda: None)
    assert paths.resolve_config_path(None) == Path("config.json")


def test_resolve_config_prefers_user_over_packaged(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # clean dir
    home = tmp_path / "home"
    home.mkdir()
    (home / "config.json").write_text("{}")
    monkeypatch.setattr(paths, "user_config_dir", lambda: home)
    # packaged config exists but user config takes priority
    monkeypatch.setattr(paths, "_packaged_config", lambda: tmp_path / "packaged.json")
    assert paths.resolve_config_path(None) == home / "config.json"


def test_resolve_config_packaged_when_no_user(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # clean dir
    monkeypatch.setattr(paths, "user_config_dir", lambda: tmp_path / "nohome")
    packaged = tmp_path / "packaged.json"
    packaged.write_text("{}")  # must exist for the fallback to pick it
    monkeypatch.setattr(paths, "_packaged_config", lambda: packaged)
    assert paths.resolve_config_path(None) == packaged


def test_packaged_config_is_loadable():
    """The config shipped inside the package must be valid & loadable."""
    p = paths._packaged_config()
    if p is not None:
        from dark_rpg.config import load_config
        cfg = load_config(str(p))
        assert cfg["game"]["floor_count"] == 10
