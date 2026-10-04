"""Stamina combat mode tests.

These encode the **fixed** exhaustion semantics (see ``docs/COMBAT.md``):

* Hitting 0 stamina sets ``exhausted``.
* An exhausted combatant's next turn is a forced ``weak_block`` recovery
  turn — they cannot attack.
* Stamina restores at the **end** of the recovery turn.
* The enemy follows the exact same rules as the player.
"""
from __future__ import annotations

from dark_rpg.combat.stamina import StaminaCombatMode
from dark_rpg.entities import Entity, Player
from dark_rpg.testing import StubRng


def make_mode(cfg):
    return StaminaCombatMode(cfg)


def make_player(cfg):
    p = Player("Tester", cfg)
    p.stamina = p.max_sta
    p.exhausted = False
    return p


def make_enemy(stamina=10, atk=5, defense=1, hp=50):
    e = Entity("Dummy", hp=hp, atk=atk, defense=defense, stamina=stamina)
    e.exhausted = False
    return e


# ── exhaustion bookkeeping ──────────────────────────────────────────────

def test_attack_sets_exhausted_when_sta_hits_zero(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=cfg["stamina"]["cost_attack"])
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))
    assert enemy.stamina == 0
    assert enemy.exhausted


def test_heavy_sets_exhausted_when_sta_hits_zero(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=cfg["stamina"]["cost_heavy"])
    mode.resolve(player, enemy, "defend", "heavy", StubRng(roll=20))
    assert enemy.stamina == 0
    assert enemy.exhausted


def test_attack_does_not_exhaust_when_sta_sufficient(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=cfg["stamina"]["cost_attack"] + 1)
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))
    assert enemy.stamina == 1
    assert not enemy.exhausted


# ── forced recovery turn (the fixed logical gap) ────────────────────────

def test_exhausted_enemy_is_forced_to_weak_block_next_turn(cfg):
    """An enemy that exhausted itself must waste its next turn recovering —
    it cannot attack for free.  (This is the design fix; the old code let
    the enemy restore stamina and attack immediately.)"""
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=cfg["stamina"]["cost_attack"])

    # turn 1: drain the enemy to 0
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))
    assert enemy.exhausted

    hp_before = player.hp
    # turn 2: enemy "picks" attack but must be forced to weak_block
    mode.resolve(player, enemy, "attack", "attack", StubRng(roll=20))
    assert player.hp == hp_before, "exhausted enemy must not deal damage (forced weak_block)"


def test_exhaustion_restores_stamina_at_end_of_recovery_turn(cfg):
    """Stamina restores when the recovery turn completes."""
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=cfg["stamina"]["cost_attack"])
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))  # turn 1: break enemy
    assert enemy.exhausted

    expected = int(enemy.max_sta * cfg["stamina"]["exhaustion_restore"])
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))  # turn 2: recovery turn
    assert not enemy.exhausted
    assert enemy.stamina == expected
    assert player.hp > 0  # enemy spent the turn recovering, no damage taken


def test_exhausted_player_is_forced_to_weak_block(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, atk=10, defense=0)
    # exactly enough attacks to hit 0 stamina (no recovery yet)
    attacks_to_exhaust = player.max_sta // cfg["stamina"]["cost_attack"]
    for _ in range(attacks_to_exhaust):
        mode.resolve(player, enemy, "attack", "defend", StubRng(roll=1))
    assert player.exhausted

    forced = mode.forced_action(player)
    assert forced is not None
    action, _msg = forced
    assert action == "weak_block"

    hp_before = player.hp
    mode.resolve(player, enemy, action, "attack", StubRng(roll=20))
    assert player.exhausted is False
    assert player.stamina == int(player.max_sta * cfg["stamina"]["exhaustion_restore"])
    # the enemy's attack landed on the recovery turn (weak guard: half damage)
    assert player.hp <= hp_before


# ── combo ───────────────────────────────────────────────────────────────

def test_combo_builds_on_hits_and_resets_on_miss(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, defense=0, hp=999)

    mode.resolve(player, enemy, "attack", "defend", StubRng(roll=20))  # hit
    assert player.combo == 1
    hp1 = enemy.hp
    mode.resolve(player, enemy, "attack", "defend", StubRng(roll=20))  # hit again
    assert player.combo == 2
    assert enemy.hp < hp1  # combo damage grew

    mode.resolve(player, enemy, "attack", "defend", StubRng(roll=1))  # miss
    assert player.combo == 0


# ── defend ──────────────────────────────────────────────────────────────

def test_defend_halves_incoming_damage_and_costs_stamina(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, atk=20, defense=0)
    hp_before = player.hp
    sta_before = player.stamina
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))
    dmg = hp_before - player.hp
    assert dmg == max(1, (20 - player.defense) // 2)
    assert player.stamina == sta_before - cfg["stamina"]["cost_defend_block"]


def test_defend_idle_regen_when_enemy_misses(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, atk=0, defense=0)  # cannot beat the hit threshold
    player.stamina = 4
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=10))  # 10 + 0 <= 10 -> miss
    assert player.stamina == 4 + cfg["stamina"]["regen_defend_idle"]


def test_reveal_intent_shows_enemy_action(cfg):
    """Stamina mode is read-the-enemy too: intent is shown before the turn."""
    mode = make_mode(cfg)
    enemy = make_enemy()
    text = mode.reveal_intent(enemy, "heavy")
    assert "HEAVY" in text


def test_heavy_costs_more_stamina(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, defense=0)
    mode.resolve(player, enemy, "heavy", "defend", StubRng(roll=20))
    assert player.stamina == player.max_sta - cfg["stamina"]["cost_heavy"]


def test_defend_halves_heavy_damage(cfg):
    """Defending a telegraphed heavy halves the big hit."""
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, atk=20, defense=0)
    hp_before = player.hp
    mode.resolve(player, enemy, "defend", "heavy", StubRng(roll=20))
    dmg = hp_before - player.hp
    assert dmg == max(1, (2 * 20 - player.defense) // 2)


def test_enemy_defend_halves_player_damage(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(stamina=50, defense=0, hp=999)
    hp_before = enemy.hp
    mode.resolve(player, enemy, "attack", "defend", StubRng(roll=20))
    dmg = hp_before - enemy.hp
    assert dmg == max(1, (player.atk - 0) // 2)
