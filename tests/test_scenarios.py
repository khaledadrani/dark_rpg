"""Scenario tests: whole mechanics played through the real Game/combat modes.

Written after the 2026-10-04 typing cleanup (Entity gained xp/gold/_revived,
casts in combat modes, None-guards in app.py) to prove those edits kept
behavior: each test plays a small story headlessly and asserts what a player
would see, not an internal detail.
"""
from __future__ import annotations

import os

import pytest

from dark_rpg.combat.posture import PostureCombatMode
from dark_rpg.combat.stamina import StaminaCombatMode
from dark_rpg.entities import Entity, Player, apply_post_hit
from dark_rpg.gear import describe, gear_power, slot_label
from dark_rpg.testing import StubRng, attack_policy, make_game
from dark_rpg.world.enemies import make_combatant


def template(cfg, name):
    return next(e for e in cfg["enemies"] if e["name"] == name)


# ── enemy construction: rewards live on Entity ──────────────────────────

def test_enemy_carries_rewards_and_ability_template(cfg):
    lich = template(cfg, "Lich")
    enemy = make_combatant(cfg, StaminaCombatMode(cfg), lich, floor=3)
    assert enemy.xp == lich["xp"]
    lo, hi = enemy.gold
    assert lo <= hi == lich["gold"][1]
    assert enemy.template["ability"]["type"] == "revive"
    assert enemy._revived is False


# ── Lich revive: exactly once ───────────────────────────────────────────

def test_lich_revives_once_then_stays_dead(cfg):
    lich = template(cfg, "Lich")
    enemy = make_combatant(cfg, StaminaCombatMode(cfg), lich, floor=1)
    hero = Player("Hero", cfg)
    rng = StubRng()

    enemy.hp = 0
    msgs = apply_post_hit(hero, enemy, 5, hero.template, cfg, rng)  # hero has no ability
    assert enemy.hp == 0 and msgs == []  # revive is the *defender's* template ability

    msgs = apply_post_hit(enemy, enemy, 5, lich, cfg, rng)  # lich as defender of its own template
    assert enemy.hp == max(1, int(enemy.max_hp * lich["ability"]["fraction"]))
    assert enemy._revived is True and any("reconstitutes" in m for m in msgs)

    enemy.hp = 0
    msgs = apply_post_hit(enemy, enemy, 5, lich, cfg, rng)
    assert enemy.hp == 0 and not any("reconstitutes" in m for m in msgs)


# ── stamina mode: combo builds on hits, resets on a miss ────────────────

def test_stamina_combo_builds_then_resets_on_miss(cfg):
    mode, hero = StaminaCombatMode(cfg), Player("Hero", cfg)
    foe = Entity("Dummy", hp=500, atk=1, defense=0, stamina=mode.max_stamina())
    mode.start_combat(hero)
    mode.start_combat(foe)
    for expected in (1, 2, 3):
        mode.resolve(hero, foe, "attack", "defend", StubRng(roll=20))
        assert hero.combo == expected
    mode.resolve(hero, foe, "attack", "defend", StubRng(roll=1))
    assert hero.combo == 0


# ── posture mode: missed heavy gets punished, enemy acts only once ──────

def test_posture_missed_heavy_is_countered_once(cfg):
    mode, hero = PostureCombatMode(cfg), Player("Hero", cfg)
    hero.set_stamina_pool(cfg["posture"]["max"])
    foe = Entity("Dummy", hp=100, atk=9, defense=0, stamina=cfg["posture"]["max"])
    before = hero.hp
    msgs = mode.resolve(hero, foe, "heavy", "attack", StubRng(roll=1))
    text = "\n".join(msgs)
    assert "misses" in text and "counters" in text
    assert text.count("counters") == 1  # enemy's own attack did not also land
    assert hero.hp < before


# ── consumables via the shared _use_item path ───────────────────────────

@pytest.mark.parametrize("mode_cls", [StaminaCombatMode, PostureCombatMode])
def test_use_item_scenarios(cfg, mode_cls):
    mode, hero = mode_cls(cfg), Player("Hero", cfg)
    foe = Entity("Dummy", hp=50, atk=1, defense=0, stamina=10)

    hero.consumables.clear()
    assert "empty" in mode._use_item(hero, foe, StubRng())[0]

    hero.consumables["oil"] = 1
    assert "flames" in mode._use_item(hero, foe, StubRng())[0]
    assert [s.kind for s in foe.statuses] == ["burn"]

    hero.consumables["rations"] = 1
    food = hero.food
    mode._use_item(hero, foe, StubRng())
    assert hero.food == food + 4

    hero.consumables["potion"] = 1
    hero.hp = 1
    assert "potion" in mode._use_item(hero, foe, StubRng())[0]
    assert hero.hp > 1


# ── Game: save-path handling and recap ──────────────────────────────────

def test_game_without_save_path_never_writes_a_save(cfg, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    game = make_game(cfg, combat_mode="posture", respond=attack_policy, seed=2, save_path=None)
    result = game.run()
    assert result.outcome in {"win", "dead"}
    assert os.listdir(tmp_path) == []


def test_missing_save_file_starts_fresh_game(cfg, tmp_path):
    game = make_game(cfg, respond=attack_policy, seed=1, save_path=str(tmp_path / "nope.json"))
    assert game._load_or_new_player().floor == 1


def test_corrupt_save_falls_back_to_new_game_and_is_deleted(cfg, tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{not json")
    game = make_game(cfg, answers=["c"], defaults={}, seed=1, save_path=str(path))
    player = game._load_or_new_player()
    assert player.floor == 1
    assert "new game" in game.io.text().lower()
    assert not path.exists()


def test_declining_continue_deletes_old_save(cfg, tmp_path):
    from dark_rpg.save import save_game
    path = tmp_path / "save.json"
    save_game(Player("Old", cfg), str(path))
    game = make_game(cfg, answers=["n"], seed=1, save_path=str(path))
    game._load_or_new_player()
    assert not path.exists()


@pytest.mark.parametrize("mode", ["stamina", "posture"])
def test_full_run_prints_recap_and_result_matches(cfg, mode):
    game = make_game(cfg, combat_mode=mode, respond=attack_policy, seed=4)
    result = game.run()
    text = game.io.text()
    assert "RUN RECAP" in text
    assert ("VICTORY" if result.outcome == "win" else "DEFEAT") in text


def test_recap_and_result_require_a_started_run(cfg):
    game = make_game(cfg, seed=1)
    with pytest.raises(AssertionError):
        game._recap("dead")
    with pytest.raises(AssertionError):
        game._result("dead", 10)


# ── gear helpers (previously untested) ──────────────────────────────────

def test_gear_helpers():
    epic = {"name": "Blade", "slot": "weapon", "rarity": "epic", "bonus": 4}
    common = {**epic, "rarity": "common"}
    flat = {"name": "Charm", "slot": None, "stat": "defense", "bonus": 2}
    assert gear_power(epic, 0) > gear_power(common, 0)
    assert gear_power({"bonus": 0}, 0) == 1  # never scores below 1
    assert slot_label("weapon") == "Weapon" and slot_label(None) == "Flat"
    assert "[epic weapon] +4" in describe(epic)
    assert "DEFENSE (flat)" in describe(flat)
