"""Tests for the expansion: gear, status effects, enemy abilities, consumables.

These lock in the new systems added for the publish pass so they keep working
as the game evolves.
"""
from __future__ import annotations

import pytest

from dark_rpg.entities import Player, crit_amplify
from dark_rpg.status import StatusEffect, apply_status, tick_statuses
from dark_rpg.testing import FakeIO, StubRng, make_game


# ── gear system ──────────────────────────────────────────────────────────

def test_equipment_replaces_slot_not_stacks(game_cfg):
    player = Player("Hero", game_cfg)
    base = player.atk
    # equip a weapon then a *different* weapon: it should replace, not stack
    item1 = game_cfg["loot_table"][0]  # first weapon slot item
    item2 = next(i for i in game_cfg["loot_table"] if i.get("slot") == "weapon" and i is not item1)
    player.equip(item1)
    after1 = player.effective_atk
    player.equip(item2)
    after2 = player.effective_atk
    # equipping a second weapon replaces the first: after2 reflects only item2
    assert player.gear["weapon"]["name"] == item2["name"]
    assert after2 == base + item2["bonus"]
    assert after1 == base + item1["bonus"]


def test_flat_item_goes_to_accessories(game_cfg):
    player = Player("Hero", game_cfg)
    base = player.effective_defense
    flat = next(i for i in game_cfg["loot_table"] if i.get("slot") is None and i.get("stat") == "defense")
    player.equip(flat)
    assert player.effective_defense == base + flat["bonus"]


# ── status effects ───────────────────────────────────────────────────────

def test_poison_ticks_each_turn(game_cfg):
    e = Player("Hero", game_cfg)
    e.statuses = [StatusEffect("poison", 2, 3)]
    hp = e.hp
    msgs = tick_statuses(e, game_cfg, StubRng())
    # poison deals its power each tick
    assert e.hp < hp
    assert len(e.statuses) == 1 and e.statuses[0].duration == 1
    # next tick expires
    tick_statuses(e, game_cfg, StubRng())
    assert e.statuses == []


def test_apply_status_does_not_stack_stronger(game_cfg):
    e = Player("Hero", game_cfg)
    apply_status(e, "poison", 3, 2)
    apply_status(e, "poison", 4, 3)  # stronger duration+power wins
    assert e.statuses[0].duration == 4
    assert e.statuses[0].power == 3


# ── enemy special abilities ──────────────────────────────────────────────

def test_crit_amplify_no_ability(game_cfg):
    from dark_rpg.entities import Entity
    a = Entity("A", 10, 5, 0)
    assert crit_amplify(a, 7, {}, StubRng()) == 7


def test_lifesteal_heals_attacker(game_cfg):
    from dark_rpg.entities import Entity
    from dark_rpg.entities import apply_post_hit
    attacker = Entity("Vampire", 10, 10, 0)
    attacker.hp = 5
    defender = Entity("Hero", 30, 3, 1)
    template = {"ability": {"type": "lifesteal", "chance": 1.0, "fraction": 0.5}}
    apply_post_hit(attacker, defender, 10, template, game_cfg, StubRng())
    # healed 50% of 10 damage = 5, capped at max 10
    assert attacker.hp == 10


def test_drain_steals_stamina(game_cfg):
    from dark_rpg.entities import Entity
    from dark_rpg.entities import apply_post_hit
    attacker = Entity("Wraith", 20, 8, 0)
    attacker.set_stamina_pool(24)
    defender = Entity("Hero", 30, 3, 1)
    defender.set_stamina_pool(24)
    template = {"ability": {"type": "drain", "amount": 3}}
    apply_post_hit(attacker, defender, 5, template, game_cfg, StubRng())
    assert defender.stamina == 24 - 3
    assert attacker.stamina == 24


def test_revive_once(game_cfg):
    from dark_rpg.entities import Entity
    from dark_rpg.entities import apply_post_hit
    attacker = Entity("Lich", 30, 12, 0)
    defender = Entity("Hero", 30, 3, 1)
    template = {"ability": {"type": "revive", "once": True, "fraction": 0.4}}
    defender.hp = 0
    apply_post_hit(attacker, defender, 50, template, game_cfg, StubRng())
    assert defender.hp == int(defender.max_hp * 0.4)
    assert defender._revived is True
    # second death: no second revive
    defender.hp = 0
    apply_post_hit(attacker, defender, 50, template, game_cfg, StubRng())
    assert defender.hp == 0


def test_status_on_hit_applies(game_cfg):
    from dark_rpg.entities import Entity
    from dark_rpg.entities import apply_post_hit
    attacker = Entity("Cave Spider", 12, 4, 1)
    defender = Entity("Hero", 30, 3, 1)
    template = {"status_on_hit": {"poison": 2}}
    apply_post_hit(attacker, defender, 4, template, game_cfg, StubRng())
    assert any(s.kind == "poison" for s in defender.statuses)


# ── consumables in combat ────────────────────────────────────────────────

def test_use_potion_heals_in_combat(game_cfg):
    from dark_rpg.combat.stamina import StaminaCombatMode
    mode = StaminaCombatMode(game_cfg)
    player = Player("Hero", game_cfg)
    player.hp = 5
    player.add_consumable("potion")
    from dark_rpg.entities import Entity
    enemy = Entity("Foe", 20, 3, 1)
    enemy.set_stamina_pool(game_cfg["stamina"]["max"])
    player.set_stamina_pool(game_cfg["stamina"]["max"])
    msgs = mode.resolve(player, enemy, "use", "defend", StubRng(roll=20))
    assert player.hp == 5 + 20  # potion heals 20 (capped at max 32)
    assert player.consumables["potion"] == 0


def test_use_oil_burns_enemy(game_cfg):
    from dark_rpg.combat.stamina import StaminaCombatMode
    mode = StaminaCombatMode(game_cfg)
    player = Player("Hero", game_cfg)
    player.hp = player.max_hp  # full so potion is skipped
    player.add_consumable("oil")
    from dark_rpg.entities import Entity
    enemy = Entity("Foe", 20, 3, 1)
    enemy.set_stamina_pool(game_cfg["stamina"]["max"])
    player.set_stamina_pool(game_cfg["stamina"]["max"])
    mode.resolve(player, enemy, "use", "defend", StubRng(roll=20))
    assert any(s.kind == "burn" for s in enemy.statuses)
    assert player.consumables["oil"] == 0


# ── new room events exist and don't crash ────────────────────────────────

def test_new_events_registered(game_cfg):
    from dark_rpg.world.events import event_ids
    for eid in ("vault", "curse", "ambush", "gamble", "secret"):
        assert eid in event_ids(), f"{eid} not registered"


def test_gamble_walk_away_no_crash(game_cfg):
    from dark_rpg.world.events import get_event
    player = Player("Hero", game_cfg)
    player.gold = 50
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.0))
    get_event("gamble").run(game, player, 1)  # default "2" = walk away
    assert player.gold == 50
