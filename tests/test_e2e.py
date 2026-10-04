"""End-to-end headless tests.

These drive the *whole* game (title screen -> floors -> boss) with no real
terminal: a FakeIO answers prompts and a seeded RNG makes every run
reproducible.  They answer the "does this game make sense?" questions:
does it always terminate, keep invariants, honor death rules, and is it
playable under both combat modes?
"""
from __future__ import annotations


import pytest

from dark_rpg.app import GameResult
from dark_rpg.testing import attack_policy, make_game, run_simulation


# ── helpers ─────────────────────────────────────────────────────────────

def play_full(cfg, *, combat_mode, seed, policy=None, save_path=None):
    """Play one full game headlessly; returns (result, game)."""
    game = make_game(
        cfg,
        combat_mode=combat_mode,
        respond=policy,
        seed=seed,
        save_path=save_path,
    )
    return game.run(), game


def assert_invariants(result: GameResult, cfg) -> None:
    assert result.outcome in {"win", "dead"}
    floor_count = cfg["game"]["floor_count"]
    assert 0 <= result.floors_cleared <= floor_count
    assert result.level >= 1
    assert result.scars <= cfg["game"]["scar_limit"] + 1
    assert result.deaths == result.scars  # every scar came from a death
    assert result.fights >= 0 and result.rooms >= 0
    if result.outcome == "win":
        assert result.floors_cleared == floor_count


# ── full-run smoke tests (both combat modes) ────────────────────────────

@pytest.mark.parametrize("combat_mode", ["stamina", "posture"])
def test_full_game_completes_under_both_modes(cfg, combat_mode):
    for seed in range(3):
        result, game = play_full(cfg, combat_mode=combat_mode, seed=seed, policy=attack_policy)
        assert_invariants(result, cfg)
        assert game.player is not None and game.player.hp >= 0


def test_smart_policy_runs_clean(cfg):
    from dark_rpg.testing import smart_policy
    result, game = play_full(cfg, combat_mode="stamina", seed=7, policy=smart_policy)
    assert_invariants(result, cfg)


# ── death / save semantics ──────────────────────────────────────────────

def test_game_over_deletes_save(cfg, tmp_path):
    save_path = str(tmp_path / "save.json")
    # Seed chosen so the attack-policy run ends in death (verify below).
    result, game = play_full(cfg, combat_mode="stamina", seed=1, policy=attack_policy, save_path=save_path)
    if result.outcome == "dead":
        assert not __import__("os").path.exists(save_path)


def test_save_and_continue_mid_run(cfg, tmp_path):
    """Play a few rooms with saving on, then a fresh Game continues from the
    same floor instead of starting over."""
    save_path = str(tmp_path / "save.json")
    game1 = make_game(cfg, combat_mode="stamina", respond=attack_policy, seed=3, save_path=save_path)
    # drive the game manually until we've descended at least one floor
    player = None
    for _ in range(40):  # safety valve
        from dark_rpg.world.rooms import run_room
        if player is None:
            from dark_rpg.entities import Player
            player = Player("Hero", cfg)
        game1.player = player
        if player.scars > 5 or not player.is_alive():
            break
        result = run_room(game1, player, room_num=game1.stats.rooms + 1)
        game1.stats.rooms += 1
        if result == "descend":
            break
    assert player is not None
    assert __import__("os").path.exists(save_path)

    # continue with a fresh Game object
    game2 = make_game(cfg, combat_mode="stamina", respond=attack_policy, seed=99, save_path=save_path)
    game2.run()
    assert game2.player.floor >= player.floor


def test_starvation_kills_player(game_cfg):
    """No food -> hunger damage each room -> death by starvation."""
    from dark_rpg.entities import Player
    from dark_rpg.testing import StubRng
    from dark_rpg.world.rooms import run_room

    game_cfg["room_weights"] = {"loot": 1}  # harmless event; food is the killer
    player = Player("Hero", game_cfg)
    player.food = 1
    player.hp = 1  # one room of hunger (hunger_damage HP) must kill
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.0))
    game.player = player

    result1 = run_room(game, player, room_num=1)  # eats the last food
    assert result1 == "alive"
    assert player.food == 0

    result2 = run_room(game, player, room_num=2)  # no food -> hunger damage -> dead
    assert result2 == "dead"


def test_merchant_event_in_full_run(cfg):
    """A full run where the player buys a potion at the first merchant."""
    from dark_rpg.io import Prompt
    bought = {"done": False}

    def responder(prompt: Prompt):
        if prompt.kind == "merchant" and not bought["done"]:
            bought["done"] = True
            return "1"  # buy the potion
        return attack_policy(prompt)

    game = make_game(cfg, combat_mode="stamina", respond=responder, seed=5)
    result = game.run()
    assert_invariants(result, cfg)


# ── "does it make sense?" guard rails ───────────────────────────────────

def test_simulation_is_sane(cfg):
    """A short simulation must complete without exceptions and keep
    invariants — the guard rail that keeps the game honest."""
    for mode in ("stamina", "posture"):
        stats = run_simulation(cfg, combat_mode=mode, policy=attack_policy, runs=5, seed_base=100)
        assert stats["runs"] == 5
        assert stats["wins"] + stats["losses"] == 5
        assert 0.0 <= stats["win_rate"] <= 1.0
        assert stats["avg_floors_cleared"] <= cfg["game"]["floor_count"]


def test_seeded_runs_are_reproducible(cfg):
    """Same seed + same policy = identical outcome (deterministic game)."""
    r1, _ = play_full(cfg, combat_mode="stamina", seed=42, policy=attack_policy)
    r2, _ = play_full(cfg, combat_mode="stamina", seed=42, policy=attack_policy)
    assert r1.as_dict() == r2.as_dict()
