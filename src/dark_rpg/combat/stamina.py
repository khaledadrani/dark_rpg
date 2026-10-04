"""Stamina combat mode — the classic mode.

Design rules (see ``docs/COMBAT.md`` for the full rationale):

* Actions cost stamina; hitting 0 mid-turn sets ``exhausted``.
* An *exhausted* combatant is forced to ``weak_block`` on their **next**
  turn (a recovery turn) and stamina is restored to
  ``int(max_sta * exhaustion_restore)`` at the **end** of that turn.
* The enemy obeys exactly the same rules as the player (no free passes).
* Resolution is simultaneous: both sides commit an action, then outcomes
  are applied.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple, cast

from dark_rpg.combat import register_combat_mode
from dark_rpg.combat.base import CombatMode
from dark_rpg.entities import Entity, Player, apply_post_hit, crit_amplify
from dark_rpg.status import tick_statuses
from dark_rpg.ui import bar


@register_combat_mode
class StaminaCombatMode(CombatMode):
    key = "stamina"
    name = "Classic stamina combat"
    config_key = "stamina"

    MENU: List[Tuple[str, str]] = [
        ("1", "Attack"),
        ("2", "Heavy Strike (2x dmg, 60% hit)"),
        ("3", "Defend"),
        ("u", "Use item (potion heal / oil burn / poison)"),
    ]
    ACTION_KEYS = {"1": "attack", "2": "heavy", "3": "defend", "u": "use"}

    # ── setup ───────────────────────────────────────────────────────────
    def max_stamina(self) -> int:
        return self.cfg["stamina"]["max"]

    def start_combat(self, combatant: Entity) -> None:
        combatant.set_stamina_pool(self.max_stamina())
        combatant.exhausted = False
        combatant.broken = False

    # ── menu / hooks ────────────────────────────────────────────────────
    def action_menu(self) -> List[Tuple[str, str]]:
        return list(self.MENU)

    def forced_action(self, combatant: Entity) -> Optional[Tuple[str, str]]:
        if combatant.exhausted:
            return ("weak_block", "  ⚠  You are exhausted! You can only weakly block this turn.")
        return None

    def pick_enemy_action(self, enemy: Entity, weights: Dict[str, float], rng: random.Random) -> str:
        return rng.choices(list(weights.keys()), list(weights.values()), k=1)[0]

    def reveal_intent(self, enemy: Entity, action: str) -> Optional[str]:
        # Read-the-enemy: the enemy's intent is shown before the player
        # commits (same as posture mode).  This turns every turn into a
        # decision: defend the heavy, punish the defender, etc.
        return f"  {enemy.name} prepares to {action.upper()}!"

    def flee_fail(self, combatant: Entity) -> List[str]:
        cost = self.cfg["stamina"]["cost_flee_fail"]
        combatant.spend_sta(cost)
        if combatant.stamina == 0:
            combatant.exhausted = True
            return [f"  Escape blocked! −{cost} STA — and you're exhausted!"]
        return [f"  Escape blocked! −{cost} STA."]

    # ── resolution ──────────────────────────────────────────────────────
    def resolve(
        self,
        player: Entity,
        enemy: Entity,
        p_action: str,
        e_action: str,
        rng: random.Random,
    ) -> List[str]:
        SC = self.cfg["stamina"]
        player = cast(Player, player)  # combo is player-only state
        msgs: List[str] = []

        # ── status effects tick at the start of the turn (DoT damage) ────
        msgs.extend(tick_statuses(player, self.cfg, rng))
        msgs.extend(tick_statuses(enemy, self.cfg, rng))

        # ── exhaustion: forced recovery turn (restore happens at END) ────
        player_recovering = player.exhausted
        enemy_recovering = enemy.exhausted
        if player_recovering:
            p_action = "weak_block"
        if enemy_recovering:
            e_action = "weak_block"

        # defend halves incoming damage (the old "2x defense" barely did
        # anything against heavy hits — fixed gap)
        p_def = player.effective_defense
        e_def = enemy.effective_defense

        # ── player action ──
        if p_action in ("attack", "heavy"):
            cost = SC["cost_heavy"] if p_action == "heavy" else SC["cost_attack"]
            player.spend_sta(cost)
            if player.stamina == 0:
                player.exhausted = True
            hit_threshold = 12 if p_action == "heavy" else 10
            if rng.randint(1, 20) + player.effective_atk > hit_threshold:
                player.combo += 1
                atk_mult = 2 if p_action == "heavy" else 1
                dmg = max(1, player.effective_atk * atk_mult + (player.combo - 1) - e_def)
                if e_action == "defend":
                    dmg = max(1, dmg // 2)
                dmg = crit_amplify(player, dmg, player.template, rng)
                enemy.take_damage(dmg)
                label = "Heavy blow" if p_action == "heavy" else "You strike"
                crit = " 💥 CRIT!" if dmg > max(1, player.effective_atk * atk_mult) else ""
                msgs.append(f"  {label}! {dmg} damage to {enemy.name}. (Combo x{player.combo}){crit}")
                msgs.extend(apply_post_hit(player, enemy, dmg, player.template, self.cfg, rng))
            else:
                player.combo = 0
                msgs.append("  Your attack misses. Combo reset.")
        elif p_action == "defend":
            # defending doesn't reset your combo — only a miss does
            msgs.append("  You brace for impact.")
        elif p_action == "weak_block":
            player.combo = 0
            msgs.append("  You weakly raise your guard.")
        elif p_action == "use":
            msgs.extend(self._use_item(player, enemy, rng))

        # ── enemy action ──
        enemy_hit = False
        if e_action in ("attack", "heavy"):
            cost = SC["cost_heavy"] if e_action == "heavy" else SC["cost_attack"]
            enemy.spend_sta(cost)
            if enemy.stamina == 0:
                enemy.exhausted = True
            hit_threshold = 12 if e_action == "heavy" else 10
            if rng.randint(1, 20) + enemy.effective_atk > hit_threshold:
                enemy_hit = True
                atk_mult = 2 if e_action == "heavy" else 1
                dmg = max(1, enemy.effective_atk * atk_mult - p_def)
                if p_action in ("defend", "weak_block"):
                    # weak_block = "weakly raise your guard": still half damage
                    dmg = max(1, dmg // 2)
                dmg = crit_amplify(enemy, dmg, enemy.template, rng)
                player.take_damage(dmg)
                label = f"{enemy.name} strikes heavily" if e_action == "heavy" else f"{enemy.name} attacks"
                msgs.append(f"  {label} for {dmg} damage!")
                msgs.extend(apply_post_hit(enemy, player, dmg, enemy.template, self.cfg, rng))
                if p_action == "defend":
                    player.spend_sta(SC["cost_defend_block"])
                    if player.stamina == 0:
                        player.exhausted = True
            else:
                msgs.append(f"  {enemy.name} misses!")
        elif e_action in ("defend", "weak_block"):
            msgs.append(f"  {enemy.name} braces for impact.")

        # defend idle regen: enemy missed or didn't attack
        if p_action == "defend" and not enemy_hit:
            player.regen_sta(SC["regen_defend_idle"])
            msgs.append("  You held your ground. Stamina recovers.")

        # ── end of recovery turn: restore stamina, clear exhaustion ──────
        if player_recovering:
            player.stamina = int(player.max_sta * SC["exhaustion_restore"])
            player.exhausted = False
            msgs.append(f"  You catch your breath. STA restored to {player.stamina}.")
        if enemy_recovering:
            enemy.stamina = int(enemy.max_sta * SC["exhaustion_restore"])
            enemy.exhausted = False
            msgs.append(f"  {enemy.name} catches its breath. STA restored to {enemy.stamina}.")

        return msgs

    # ── display ─────────────────────────────────────────────────────────
    def hud(self, player: Entity, enemy: Entity) -> List[str]:
        from dark_rpg.ui import ANSI
        c = self.color_on
        hp_c = ANSI["green"] if c else ""
        sta_c = ANSI["cyan"] if c else ""
        rst = ANSI["reset"] if c else ""
        p_eff = ", ".join(s.kind for s in player.statuses)
        e_eff = ", ".join(s.kind for s in enemy.statuses)
        p_line = f"  {'You':<6} {bar(player.hp, player.max_hp, color=hp_c, reset=rst)}  ATK {player.effective_atk}  DEF {player.effective_defense}"
        e_line = f"  {'Foe':<6} {bar(enemy.hp, enemy.max_hp, color=hp_c, reset=rst)}  ATK {enemy.effective_atk}  DEF {enemy.effective_defense}"
        if p_eff:
            p_line += f"  [{p_eff}]"
        if e_eff:
            e_line += f"  [{e_eff}]"
        return [
            f"\n  ── COMBAT ── {player.name} vs {enemy.name} ──",
            p_line,
            f"  {'':6} {bar(player.stamina, player.max_sta, width=10, fill='▒', empty='░', color=sta_c, reset=rst)}  STA",
            e_line,
            f"  {'':6} {bar(enemy.stamina, enemy.max_sta, width=10, fill='▒', empty='░', color=sta_c, reset=rst)}  STA",
        ]
