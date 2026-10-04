"""Shared pytest fixtures."""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))  # belt & suspenders for direct runs

from dark_rpg.config import load_config  # noqa: E402


@pytest.fixture(scope="session")
def cfg():
    """The real game config (tuning source of truth)."""
    return load_config(str(ROOT / "config.json"))


@pytest.fixture()
def game_cfg(cfg):
    """A deep copy of the config so tests can mutate it safely."""
    import copy
    return copy.deepcopy(cfg)
