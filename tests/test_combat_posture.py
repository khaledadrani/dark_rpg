"""Posture combat mode tests (the read-the-enemy system from ``duel.py``).

Key fixed semantics (see ``docs/COMBAT.md``):

* Posture drains on hits **received**; 0 posture = ``broken``.
* Broken combatants take ``broken_dmg_mult`` (1.75x) damage **while broken** —
  including during their forced recovery turn.  (In the old ``duel.py`` the
  multiplier was dead code because broken was cleared before the hit.)
* Recovery: at the start of the turn posture restores to ``broken_restore``
  fraction, the combatant is forced to ``weak_block`` (scramble), and broken
  is only cleared at the end of the turn.
* ``defend`` halves damage and posture drain on both sides; the enemy's
  defend actually blunts the player's attacks (old flavor-text bug).
"""
from __future__ import annotations

from dark_rpg.combat.posture import PostureCombatMode
from dark_rpg.entities import Entity, Player
from dark_rpg.testing import StubRng


def make_mode(cfg):
    return PostureCombatMode(cfg)


def make_player(cfg):
    p = Player("Tester", cfg)
    p.set_stamina_pool(cfg["posture"]["max"])
    return p


def make_enemy(hp=60, atk=8, defense=2, posture=None, cfg=None):
    posture = posture if posture is not None else cfg["posture"]["max"]
    e = Entity("Dummy", hp=hp, atk=atk, defense=defense, stamina=posture)
    return e


# ── deflect / dodge ─────────────────────────────────────────────────────

def test_deflect_beats_attack(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    psta, esta = player.stamina, enemy.stamina
    hp_before = player.hp
    mode.resolve(player, enemy, "deflect", "attack", StubRng(roll=20))
    assert player.hp == hp_before  # no damage taken
    assert player.stamina == psta - cfg["posture"]["cost_deflect"]
    assert enemy.stamina == esta - cfg["posture"]["hit_drain"]


def test_deflect_whiffs_against_defend(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    psta = player.stamina
    mode.resolve(player, enemy, "deflect", "defend", StubRng(roll=20))
    assert player.stamina == psta - cfg["posture"]["cost_deflect_fail"]


def test_dodge_success_evades(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    hp_before = player.hp
    mode.resolve(player, enemy, "dodge", "attack", StubRng(roll=10))  # > 8 succeeds
    assert player.hp == hp_before
    assert player.stamina == player.max_sta - cfg["posture"]["cost_dodge"]


def test_dodge_failure_takes_hit_and_loses_more_posture(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    hp_before = player.hp
    mode.resolve(player, enemy, "dodge", "attack", StubRng(roll=5))
    assert player.hp < hp_before
    assert player.stamina == player.max_sta - cfg["posture"]["cost_dodge_fail"] - cfg["posture"]["hit_drain"]


def test_heavy_miss_is_counterattacked(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    hp_before = player.hp
    mode.resolve(player, enemy, "heavy", "attack", StubRng(roll=1))  # heavy misses (needs > 13)
    assert player.hp < hp_before


# ── defend ──────────────────────────────────────────────────────────────

def test_defend_halves_damage_and_posture_drain(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(atk=20, cfg=cfg)
    hp_before, psta = player.hp, player.stamina
    mode.resolve(player, enemy, "defend", "attack", StubRng(roll=20))
    dmg = hp_before - player.hp
    assert dmg == max(1, 20 - player.defense * 2)
    assert player.stamina == psta - cfg["posture"]["hit_drain"] // 2


def test_defend_standoff_recovers_posture(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    player.stamina = 10
    mode.resolve(player, enemy, "defend", "defend", StubRng(roll=20))
    assert player.stamina == 10 + cfg["posture"]["defend_regen"]


def test_enemy_defend_blunts_player_attack(cfg):
    """Fixed gap: in the old duel.py, the enemy's defend was flavor text
    (the player's full damage was already applied).  Now it halves it."""
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(hp=100, defense=0, cfg=cfg)
    hp_before = enemy.hp
    mode.resolve(player, enemy, "attack", "defend", StubRng(roll=20))
    dmg = hp_before - enemy.hp
    assert dmg == max(1, (player.atk - 0) // 2)


# ── broken state (the fixed dead-code multiplier) ───────────────────────

def test_broken_combatant_takes_amplified_damage(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(atk=8, cfg=cfg)
    player.broken = True
    player.stamina = 0
    hp_before = player.hp

    mode.resolve(player, enemy, "attack", "attack", StubRng(roll=20))
    # player was broken -> forced weak_block -> enemy hits at 1.75x
    expected = int((8 - player.defense) * cfg["posture"]["broken_dmg_mult"])
    assert player.hp == hp_before - expected


def test_broken_recovery_restores_posture_and_clears_at_end_of_turn(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(atk=8, cfg=cfg)
    player.broken = True
    player.stamina = 0

    mode.resolve(player, enemy, "defend", "defend", StubRng(roll=20))
    assert player.stamina == int(player.max_sta * cfg["posture"]["broken_restore"])
    assert player.broken is False  # cleared at end of the recovery turn
    assert player.hp == player.max_hp  # enemy defended too; no damage


def test_deflect_breaks_enemy_posture(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(posture=cfg["posture"]["hit_drain"], cfg=cfg)
    assert not enemy.broken
    mode.resolve(player, enemy, "deflect", "attack", StubRng(roll=20))
    assert enemy.broken


def test_both_broken_is_a_standoff(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    enemy = make_enemy(cfg=cfg)
    player.broken = True
    player.stamina = 0
    enemy.broken = True
    enemy.stamina = 0
    hp_before = player.hp

    mode.resolve(player, enemy, "deflect", "attack", StubRng(roll=20))
    assert player.hp == hp_before  # neither side lands a blow
    assert not player.broken and not enemy.broken


def test_broken_player_forced_action(cfg):
    mode, player = make_mode(cfg), make_player(cfg)
    player.broken = True
    forced = mode.forced_action(player)
    assert forced is not None
    action, _msg = forced
    assert action == "weak_block"


def test_reveal_intent_shows_enemy_actions(cfg):
    mode = make_mode(cfg)
    enemy = make_enemy(cfg=cfg)
    assert "charges a HEAVY blow" in mode.reveal_intent(enemy, "heavy")
    assert "winds up a normal strike" in mode.reveal_intent(enemy, "attack")
    assert "braces defensively" in mode.reveal_intent(enemy, "defend")


def test_reveal_intent_shows_broken_enemy(cfg):
    mode = make_mode(cfg)
    enemy = make_enemy(cfg=cfg)
    enemy.broken = True
    assert "staggered" in mode.reveal_intent(enemy, "attack")
