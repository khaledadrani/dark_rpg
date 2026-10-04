"""Tests for the animated ASCII art system (dark_rpg.art).

Covers: registry coverage (every event/enemy has art), the config toggle,
headless-safe static playback, and the interactive animated path.
"""
from __future__ import annotations

from dark_rpg.art import (
    DEFAULT_ENEMY_ART,
    DEFAULT_SCENERY_ART,
    ENEMY_ART,
    SCENERY_ART,
    enemy_art,
    play_art,
    scenery_art,
)
from dark_rpg.testing import FakeIO
from dark_rpg.ui import article


# ── registry coverage ───────────────────────────────────────────────────

def test_every_room_event_has_scenery_art(cfg):
    for event_id in cfg["room_weights"]:
        assert event_id in SCENERY_ART, f"no scenery art for event {event_id!r}"


def test_every_enemy_and_boss_has_art(cfg):
    for enemy in cfg["enemies"]:
        assert enemy["name"] in ENEMY_ART, f"no art for enemy {enemy['name']!r}"
    assert cfg["boss"]["name"] in ENEMY_ART


def test_stairs_scenery_exists():
    assert "stairs" in SCENERY_ART


def test_fallbacks_are_used_for_unknowns():
    assert enemy_art("Totally Unknown Monster") == DEFAULT_ENEMY_ART
    assert scenery_art("not-an-event") == DEFAULT_SCENERY_ART


# ── playback: static (headless) path ────────────────────────────────────

def test_static_playback_prints_first_frame_once():
    io = FakeIO()
    frames = scenery_art("loot")
    play_art(io, frames)
    joined = "\n".join(io.print_log)
    assert joined == frames[0]
    assert "\x1b" not in joined  # no cursor-up escapes when headless


def test_single_frame_prints_once():
    io = FakeIO()
    play_art(io, ["only frame"])
    assert "\n".join(io.print_log) == "only frame"


def test_empty_frames_are_safe():
    io = FakeIO()
    play_art(io, [])
    assert "\n".join(io.print_log) == ""


# ── playback: config toggle ─────────────────────────────────────────────

def test_disabled_art_prints_nothing():
    io = FakeIO()
    io.ascii_art = False
    play_art(io, enemy_art("Goblin"))
    assert io.print_log == []


def test_config_toggle_read_by_gameio(game_cfg):
    from dark_rpg.io import GameIO
    game_cfg["ui"]["ascii_art"] = False
    assert GameIO(game_cfg).ascii_art is False
    game_cfg["ui"]["ascii_art"] = True
    assert GameIO(game_cfg).ascii_art is True
    assert GameIO(game_cfg).art_frame_delay == game_cfg["ui"]["art_frame_delay"]


def test_full_game_with_art_disabled(game_cfg):
    """End-to-end: ui.ascii_art = false must not change gameplay at all."""
    import copy

    from dark_rpg.testing import attack_policy, run_simulation
    art_off = copy.deepcopy(game_cfg)
    art_off["ui"]["ascii_art"] = False
    stats = run_simulation(art_off, combat_mode="stamina", policy=attack_policy, runs=3, seed_base=1)
    assert stats["wins"] + stats["losses"] == 3


# ── playback: animated (interactive) path ───────────────────────────────

def test_animated_path_cycles_frames_with_cursor_up():
    """With slow_print_delay > 0 (interactive), frames cycle in place."""
    io = FakeIO()
    io.slow_print_delay = 0.01  # pretend we're on a TTY
    io.art_frame_delay = 0.0
    frames = ["line1\nline2", "line3\nline4"]
    play_art(io, frames, loops=2)
    joined = "\n".join(io.print_log)
    # each frame printed loops times, plus the settle frame, with cursor-up
    assert joined.count("line1") == 3        # 2 loops + settle
    assert joined.count("line3") == 2        # 2 loops
    assert "\x1b[2A" in joined               # cursor up by frame height (2)


# ── article helper (the "A The Dungeon Tyrant" fix) ─────────────────────

def test_article_helper():
    assert article("Goblin") == "a "
    assert article("Orc") == "an "
    assert article("Skeleton") == "a "
    assert article("The Dungeon Tyrant") == ""  # no "A The ..."
    assert article("") == ""
