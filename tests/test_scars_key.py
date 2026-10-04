"""Scar system and floor-key logic tests.

Scars: losing a combat applies a scar (max HP −5, revive at half HP).
More than 5 scars = permanent game over.

Floor key: chance-based drop before room ``rooms_per_floor``; **guaranteed**
on a combat win at room >= ``rooms_per_floor``.
"""
from __future__ import annotations


from dark_rpg.testing import StubRng, make_game
from dark_rpg.world.enemies import make_combatant
from dark_rpg.world.events import get_event


def make_enemy_event_game(game_cfg, player, roll=20, rand=0.0, answers=None):
    return make_game(game_cfg, answers=answers, rng=StubRng(roll=roll, rand=rand))


def test_death_applies_scar_and_revives(game_cfg):
    """A losing fight -> scar, max HP -penalty, revive at half HP."""
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.hp = 1  # guaranteed to lose the fight
    game = make_game(game_cfg, answers=None, rng=StubRng(roll=20, rand=0.0))
    # enemy roll 20 -> always hits; player at 1 HP dies on first hit
    get_event("enemy").run(game, player, room_num=1)
    penalty = game_cfg["game"]["scar_penalty"]
    assert player.scars == 1
    assert player.max_hp == game_cfg["player"]["hp"] - penalty
    assert player.hp == player.max_hp // 2
    assert player.is_alive()


def test_six_deaths_is_permanent_game_over(game_cfg):
    """Deaths beyond the scar limit -> permanent death."""
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    limit = game_cfg["game"]["scar_limit"]
    for _ in range(limit + 1):
        player.hp = 1
        game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.0))
        get_event("enemy").run(game, player, room_num=1)
    assert player.scars == limit + 1
    assert player.scars > player.scar_limit()


def test_run_room_detects_permanent_death(game_cfg):
    """run_room returns "dead" once scars exceed the scar limit."""
    from dark_rpg.entities import Player
    from dark_rpg.world.rooms import run_room
    player = Player("Hero", game_cfg)
    player.scars = game_cfg["game"]["scar_limit"]  # one more death kills
    player.hp = 1  # this fight will kill

    # Force the room to be an enemy room
    game_cfg["room_weights"] = {"enemy": 1}
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.0))
    result = run_room(game, player, room_num=1)
    assert result == "dead"


# ── floor key ────────────────────────────────────────────────────────────

def test_key_not_guaranteed_early(game_cfg):
    """With bad luck (random() = 0.9 > 0.3) no key drops early."""
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.9))
    result = game.run_combat(player, game_cfg["enemies"][0], floor=1, room_num=1)
    assert result == "win"
    assert not player.has_key


def test_key_guaranteed_at_rooms_per_floor(game_cfg):
    """At room >= rooms_per_floor a combat win always drops the key."""
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.9))  # bad luck
    result = game.run_combat(player, game_cfg["enemies"][0], floor=1, room_num=game_cfg["game"]["rooms_per_floor"])
    assert result == "win"
    assert player.has_key


def test_key_rewards_are_granted(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    game = make_game(game_cfg, rng=StubRng(roll=20, rand=0.0))
    game.run_combat(player, game_cfg["enemies"][0], floor=1, room_num=1)
    assert player.xp > 0
    assert player.gold > game_cfg["player"]["gold"]
    assert player.has_key  # rand=0.0 < 0.3 drop chance


def test_enemy_scaling_by_floor(cfg):
    """Floor scaling makes enemies tougher; boss uses raw stats."""
    class _Mode:
        def max_stamina(self):
            return cfg["stamina"]["max"]

    template = cfg["enemies"][0]
    low = make_combatant(cfg, _Mode(), template, floor=1, enemy_list=cfg["enemies"])
    high = make_combatant(cfg, _Mode(), template, floor=9, enemy_list=cfg["enemies"])
    assert high.hp > low.hp and high.atk > low.atk

    boss = make_combatant(cfg, _Mode(), cfg["boss"], floor=10, scale_override=1.0)
    assert boss.hp == cfg["boss"]["hp"]
