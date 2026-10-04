"""Tests: enemy stamina exhaustion in resolve_combat."""
import sys, os, unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from rpg2 import Entity, Player, resolve_combat, CFG

SC = CFG["stamina"]


def make_player():
    p = Player("Tester")
    p.stamina = p.max_sta
    p.exhausted = False
    return p


def make_enemy(stamina=10):
    e = Entity("Dummy", hp=50, atk=5, defense=1, stamina=stamina)
    e.exhausted = False
    return e


class TestEnemyStaminaExhaustion(unittest.TestCase):

    # ── attack drains stamina to exactly 0 → exhausted ──────────────────────
    @patch("rpg2.roll", return_value=20)
    def test_attack_sets_exhausted_when_sta_hits_zero(self, _roll):
        player = make_player()
        enemy  = make_enemy(stamina=SC["cost_attack"])   # 2 STA left
        resolve_combat(player, enemy, "defend", "attack")
        self.assertEqual(enemy.stamina, 0)
        self.assertTrue(enemy.exhausted)

    # ── heavy attack drains stamina to exactly 0 → exhausted ────────────────
    @patch("rpg2.roll", return_value=20)
    def test_heavy_sets_exhausted_when_sta_hits_zero(self, _roll):
        player = make_player()
        enemy  = make_enemy(stamina=SC["cost_heavy"])    # 4 STA left
        resolve_combat(player, enemy, "defend", "heavy")
        self.assertEqual(enemy.stamina, 0)
        self.assertTrue(enemy.exhausted)

    # ── stamina above cost → NOT exhausted ──────────────────────────────────
    @patch("rpg2.roll", return_value=20)
    def test_attack_does_not_exhaust_when_sta_sufficient(self, _roll):
        player = make_player()
        enemy  = make_enemy(stamina=SC["cost_attack"] + 1)   # 3 STA left
        resolve_combat(player, enemy, "defend", "attack")
        self.assertGreater(enemy.stamina, 0)
        self.assertFalse(enemy.exhausted)

    # ── exhausted enemy is forced to weak_block mid-turn ────────────────────
    @patch("rpg2.roll", return_value=20)
    def test_exhausted_enemy_forced_to_weak_block(self, _roll):
        """Enemy picks 'attack' but is already exhausted → action overridden."""
        player = make_player()
        enemy  = make_enemy(stamina=SC["cost_attack"])
        # First turn: drain to 0
        resolve_combat(player, enemy, "defend", "attack")
        self.assertTrue(enemy.exhausted)

        hp_before = player.hp
        # Second turn: enemy picks attack but should be forced to weak_block
        resolve_combat(player, enemy, "attack", "attack")
        self.assertEqual(player.hp, hp_before,
                         "Exhausted enemy should not deal damage (forced weak_block)")

    # ── exhaustion restores stamina at start of next turn ───────────────────
    @patch("rpg2.roll", return_value=20)
    def test_exhaustion_restores_stamina_next_turn(self, _roll):
        player = make_player()
        enemy  = make_enemy(stamina=SC["cost_attack"])
        # Turn 1: drain enemy to 0 → exhausted
        resolve_combat(player, enemy, "defend", "attack")
        self.assertTrue(enemy.exhausted)

        expected = int(enemy.max_sta * SC["exhaustion_restore"])
        # Turn 2: exhaustion restore fires at the top of resolve_combat
        resolve_combat(player, enemy, "defend", "attack")
        self.assertFalse(enemy.exhausted)
        self.assertEqual(enemy.stamina, expected - SC["cost_attack"],
                         "Stamina should be restored amount minus this turn's attack cost")


if __name__ == "__main__":
    unittest.main(verbosity=2)
