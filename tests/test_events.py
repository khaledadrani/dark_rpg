"""Room event plugin tests (loot, rest, trap, merchant, shrine)."""
from __future__ import annotations


from dark_rpg.testing import StubRng, make_game


def run_event(game_cfg, event_id, player, answers=None, defaults=None):
    """Build a game and run a single event directly."""
    game = make_game(game_cfg, answers=answers, defaults=defaults, rng=StubRng(roll=20, rand=0.0))
    from dark_rpg.world.events import get_event
    get_event(event_id).run(game, player, room_num=1)
    return game


# ── loot ─────────────────────────────────────────────────────────────────

def test_loot_applies_bonus(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    item = game_cfg["loot_table"][0]  # StubRng picks the first loot item
    if item.get("slot"):
        run_event(game_cfg, "loot", player)
        assert player.gear[item["slot"]] is item
    else:
        old = getattr(player, item["stat"])
        run_event(game_cfg, "loot", player)
        assert getattr(player, item["stat"]) == old + item["bonus"]


# ── trap / rest ──────────────────────────────────────────────────────────

def test_trap_damages(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    hp = player.hp
    run_event(game_cfg, "trap", player)
    assert player.hp < hp


def test_rest_heals_and_gives_food(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.hp = 5
    player.food = 0
    run_event(game_cfg, "rest", player)
    assert player.hp > 5
    assert player.food > 0


# ── merchant ─────────────────────────────────────────────────────────────

def test_merchant_buys_potion(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.gold = 50
    player.hp = 5
    run_event(game_cfg, "merchant", player, answers=["1"])
    assert player.gold == 40
    assert player.consumables.get("potion", 0) >= 1  # potion added to pouch


def test_merchant_blocks_purchase_at_full_hp(game_cfg):
    """Quality-of-life fix: no wasting gold on a potion at full HP."""
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.gold = 50
    hp = player.hp
    game = run_event(game_cfg, "merchant", player, answers=["1"])
    assert player.gold == 50  # not charged
    assert player.hp == hp
    assert "already at full health" in game.io.text().lower()


def test_merchant_insufficient_gold(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.gold = 0
    player.hp = 5
    game = run_event(game_cfg, "merchant", player, answers=["1"])
    assert player.gold == 0
    assert player.hp == 5
    assert "Not enough gold" in game.io.text()


def test_merchant_leaves_on_invalid_choice(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.gold = 50
    run_event(game_cfg, "merchant", player, answers=["99"])
    assert player.gold == 50


# ── shrine ───────────────────────────────────────────────────────────────

def test_shrine_pray_good_blessing(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    player.hp = 10
    run_event(game_cfg, "shrine", player, answers=["1"])  # StubRng roll=20 -> blessing
    assert player.hp == 20


def test_shrine_pray_bad_blessing(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    hp = player.hp
    game = make_game(game_cfg, answers=["1"], rng=StubRng(roll=1))
    from dark_rpg.world.events import get_event
    get_event("shrine").run(game, player, room_num=1)
    assert player.hp == hp - 5


def test_shrine_ignore(game_cfg):
    from dark_rpg.entities import Player
    player = Player("Hero", game_cfg)
    hp = player.hp
    run_event(game_cfg, "shrine", player, answers=["2"])
    assert player.hp == hp
