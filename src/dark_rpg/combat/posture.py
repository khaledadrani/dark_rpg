"""Posture combat mode — the read-the-enemy mode (ported from ``duel.py``).

The enemy's intent is revealed **before** the player commits, turning each
turn into a small mind game: deflect an attack, dodge a heavy, punish a
defender.

Design rules (see ``docs/COMBAT.md``):

* Posture (PST) is drained by **hits received**, not just actions taken.
* Hitting 0 posture sets ``broken``.  While broken, incoming damage is
  amplified by ``broken_dmg_mult`` (1.75x).
* A broken combatant's next turn is a forced recovery turn: posture
  partially restores (``broken_restore``), but they stay vulnerable for the
  whole turn and the amplified hit still lands if the enemy attacks.
  Recovery completes at the end of the turn (broken cleared once PST > 0).
* Defending halves incoming damage *and* posture drain; it regenerates
  posture if the enemy does not attack.
* The enemy's ``defend`` likewise halves the player's incoming damage —
  defending is never flavor text.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from dark_rpg.combat import register_combat_mode
from dark_rpg.combat.base import CombatMode
from dark_rpg.entities import Entity, apply_post_hit, crit_amplify
from dark_rpg.status import tick_statuses
from dark_rpg.ui import bar


@register_combat_mode
class PostureCombatMode(CombatMode):
    key = "posture"
    name = "Posture combat (read-the-enemy)"
    config_key = "posture"

    MENU: List[Tuple[str, str]] = [
        ("1", "Attack (−2 PST | drains enemy PST on hit)"),
        ("2", "Heavy Strike (−4 PST | big dmg+drain, harder to land)"),
        ("3", "Deflect (−1 PST on success | failure = −6 PST)"),
        ("4", "Dodge (−3 PST | 60% evade, −5 if mistimed)"),
        ("5", "Defend (half damage+drain | regen PST if idle)"),
        ("u", "Use item (potion heal / oil burn / poison)"),
    ]
    ACTION_KEYS = {"1": "attack", "2": "heavy", "3": "deflect", "4": "dodge", "5": "defend", "u": "use"}

    INTENT_LABELS = {
        "attack": "winds up a normal strike",
        "heavy": "charges a HEAVY blow",
        "defend": "braces defensively",
    }

    # ── setup ───────────────────────────────────────────────────────────
    def max_stamina(self) -> int:
        return self.cfg["posture"]["max"]

    def start_combat(self, combatant: Entity) -> None:
        combatant.set_stamina_pool(self.max_stamina())
        combatant.broken = False
        combatant.exhausted = False

    # ── menu / hooks ────────────────────────────────────────────────────
    def action_menu(self) -> List[Tuple[str, str]]:
        return list(self.MENU)

    def forced_action(self, combatant: Entity) -> Optional[Tuple[str, str]]:
        if combatant.broken:
            return ("weak_block", "  💀 You are BROKEN! You scramble to recover posture this turn.")
        return None

    def pick_enemy_action(self, enemy: Entity, weights: Dict[str, float], rng: random.Random) -> str:
        return rng.choices(list(weights.keys()), list(weights.values()), k=1)[0]

    def reveal_intent(self, enemy: Entity, action: str) -> Optional[str]:
        # The read-the-enemy mechanic: posture mode shows the enemy's intent.
        if enemy.broken:
            return f"  💀 {enemy.name} is staggered and helpless!"
        label = self.INTENT_LABELS.get(action, action)
        return f"  ⚔  {enemy.name} {label}..."

    def flee_fail(self, combatant: Entity) -> List[str]:
        cost = self.cfg["posture"]["flee_fail_cost"]
        combatant.spend_sta(cost)
        if combatant.stamina == 0 and not combatant.broken:
            combatant.broken = True
            return [f"  Escape blocked! −{cost} PST — and you're BROKEN!"]
        return [f"  Escape blocked! −{cost} PST."]

    # ── internals ───────────────────────────────────────────────────────
    def _drain_posture(self, combatant: Entity, amount: int) -> bool:
        """Drain posture; returns True if this hit *breaks* the combatant."""
        combatant.spend_sta(amount)
        if combatant.stamina == 0 and not combatant.broken:
            combatant.broken = True
            return True
        return False

    def _deal_hit(self, target: Entity, raw_dmg: int, drain: int) -> Tuple[int, bool]:
        """Apply damage + posture drain to *target*; broken targets take
        amplified damage.  Returns (final damage, broke)."""
        if target.broken:
            raw_dmg = int(raw_dmg * self.cfg["posture"]["broken_dmg_mult"])
        target.take_damage(raw_dmg)
        broke = self._drain_posture(target, drain)
        return raw_dmg, broke

    # ── resolution ──────────────────────────────────────────────────────
    def resolve(
        self,
        player: Entity,
        enemy: Entity,
        p_action: str,
        e_action: Optional[str],  # set to None mid-turn once the enemy has already acted
        rng: random.Random,
    ) -> List[str]:
        SC = self.cfg["posture"]
        msgs: List[str] = []

        # ── status effects tick at the start of the turn (DoT damage) ────
        msgs.extend(tick_statuses(player, self.cfg, rng))
        msgs.extend(tick_statuses(enemy, self.cfg, rng))

        # ── broken recovery at the start of the turn ────────────────────
        # Posture partially restores, but the combatant stays vulnerable for
        # the whole turn (broken is only cleared at the END of the turn).
        player_broken = player.broken
        enemy_broken = enemy.broken
        if player_broken:
            player.stamina = int(player.max_sta * SC["broken_restore"])
            p_action = "weak_block"
            msgs.append(f"  You scramble back — posture partially restored (+{player.stamina} PST), but you're still vulnerable!")
        if enemy_broken:
            enemy.stamina = int(enemy.max_sta * SC["broken_restore"])
            e_action = "weak_block"
            msgs.append(f"  {enemy.name} staggers back — posture partially restored (+{enemy.stamina} PST), still vulnerable!")

        # ── player action ──
        if p_action == "attack":
            player.spend_sta(SC["cost_attack"])
            if rng.randint(1, 20) + player.effective_atk > 10:
                raw = max(1, player.effective_atk - enemy.effective_defense)
                drain = SC["hit_drain"]
                if e_action == "defend":  # enemy defend blunts the blow
                    raw = max(1, raw // 2)
                    drain = drain // 2
                raw = crit_amplify(player, raw, player.template, rng)
                dmg, broke = self._deal_hit(enemy, raw, drain)
                msgs.append(f"  You strike! {dmg} dmg | −{drain} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
                msgs.extend(apply_post_hit(player, enemy, dmg, player.template, self.cfg, rng))
            else:
                msgs.append("  Your attack whiffs.")

        elif p_action == "heavy":
            player.spend_sta(SC["cost_heavy"])
            if rng.randint(1, 20) + player.effective_atk > 13:
                raw = max(1, int(player.effective_atk * 1.8) - enemy.effective_defense)
                drain = SC["heavy_drain"]
                if e_action == "defend":
                    raw = max(1, raw // 2)
                    drain = drain // 2
                raw = crit_amplify(player, raw, player.template, rng)
                dmg, broke = self._deal_hit(enemy, raw, drain)
                msgs.append(f"  HEAVY blow connects! {dmg} dmg | −{drain} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
                msgs.extend(apply_post_hit(player, enemy, dmg, player.template, self.cfg, rng))
            else:
                msgs.append("  Heavy swing misses — you're open!")
                if e_action == "attack":  # punishing counterattack
                    dmg, broke = self._deal_hit(player, max(1, enemy.effective_atk - player.effective_defense), SC["hit_drain"])
                    msgs.append(f"  {enemy.name} counters! {dmg} damage{' → YOU BROKE!' if broke else ''}.")
                    e_action = None  # enemy already acted

        elif p_action == "deflect":
            if e_action in ("attack", "heavy"):
                drain_key = "heavy_drain" if e_action == "heavy" else "hit_drain"
                player.spend_sta(SC["cost_deflect"])
                broke = self._drain_posture(enemy, SC[drain_key])
                msgs.append(f"  DEFLECT! Enemy posture broken down −{SC[drain_key]} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
                msgs.append(f"  (You spent only {SC['cost_deflect']} PST)")
                e_action = None  # no enemy attack lands
            else:
                player.spend_sta(SC["cost_deflect_fail"])
                msgs.append(f"  Deflect whiff — enemy wasn't attacking. −{SC['cost_deflect_fail']} PST wasted.")

        elif p_action == "dodge":
            if e_action in ("attack", "heavy"):
                if rng.randint(1, 20) > 8:  # 60% success
                    player.spend_sta(SC["cost_dodge"])
                    msgs.append("  You sidestep cleanly. Attack dodged!")
                    e_action = None
                else:
                    player.spend_sta(SC["cost_dodge_fail"])
                    drain_key = "heavy_drain" if e_action == "heavy" else "hit_drain"
                    dmg, broke = self._deal_hit(player, max(1, enemy.effective_atk - player.effective_defense), SC[drain_key])
                    msgs.append(f"  Dodge mistimed! {dmg} damage{' → YOU BROKE!' if broke else ''}. −{SC['cost_dodge_fail']} PST.")
                    e_action = None
            else:
                player.spend_sta(SC["cost_dodge"])
                msgs.append("  You dodge... into nothing. PST spent for no gain.")

        elif p_action == "defend":
            pass  # no upfront cost; benefit applied in the enemy phase

        elif p_action == "weak_block":
            msgs.append("  You're scrambling — no offense, no defense.")

        elif p_action == "use":
            msgs.extend(self._use_item(player, enemy, rng))

        # ── enemy acts (unless already handled above) ───────────────────
        if e_action in ("attack", "heavy"):
            drain_key = "heavy_drain" if e_action == "heavy" else "hit_drain"
            if p_action == "defend":
                raw = max(1, enemy.effective_atk - player.effective_defense * 2)
                if player.broken:
                    raw = int(raw * SC["broken_dmg_mult"])
                raw = crit_amplify(enemy, raw, enemy.template, rng)
                player.take_damage(raw)
                drain = SC[drain_key] // 2
                broke = self._drain_posture(player, drain)
                msgs.append(f"  {enemy.name} strikes. Guarded: {raw} dmg | −{drain} PST{' → YOU BROKE!' if broke else ''}")
                msgs.extend(apply_post_hit(enemy, player, raw, enemy.template, self.cfg, rng))
            else:
                raw = max(1, enemy.effective_atk - player.effective_defense)
                raw = crit_amplify(enemy, raw, enemy.template, rng)
                dmg, broke = self._deal_hit(player, raw, SC[drain_key])
                label = "HEAVY " if e_action == "heavy" else ""
                msgs.append(f"  {enemy.name} {label}hits you for {dmg} damage{' → YOU BROKE!' if broke else ''}.")
                msgs.extend(apply_post_hit(enemy, player, dmg, enemy.template, self.cfg, rng))
        elif e_action == "defend":
            if p_action == "defend":
                player.regen_sta(SC["defend_regen"])
                msgs.append(f"  Standoff. Both brace. You recover {SC['defend_regen']} PST.")
            elif p_action in ("attack", "heavy"):
                msgs.append(f"  {enemy.name} defends — your blow is blunted.")
            else:
                msgs.append(f"  {enemy.name} defends and waits.")

        # ── recovery completes at the end of the turn ───────────────────
        if player_broken and player.stamina > 0 and player.hp > 0:
            player.broken = False
        if enemy_broken and enemy.stamina > 0 and enemy.hp > 0:
            enemy.broken = False

        return msgs

    # ── display ─────────────────────────────────────────────────────────
    def hud(self, player: Entity, enemy: Entity) -> List[str]:
        from dark_rpg.ui import ANSI
        c = self.color_on
        hp_c = ANSI["green"] if c else ""
        sta_c = ANSI["cyan"] if c else ""
        rst = ANSI["reset"] if c else ""
        p_broken = f"  {ANSI['red'] if c else ''}💀 BROKEN{rst}" if player.broken else "  💀 BROKEN"
        e_broken = f"  {ANSI['red'] if c else ''}💀 BROKEN{rst}" if enemy.broken else "  💀 BROKEN"
        p_eff = f"  [{', '.join(s.kind for s in player.statuses)}]" if player.statuses else ""
        e_eff = f"  [{', '.join(s.kind for s in enemy.statuses)}]" if enemy.statuses else ""
        return [
            f"\n  ── COMBAT ── {player.name} vs {enemy.name} ──",
            f"  {'You':<6} {bar(player.hp, player.max_hp, color=hp_c, reset=rst)}  ATK {player.effective_atk}  DEF {player.effective_defense}{p_eff}",
            f"  {'':6} {bar(player.stamina, player.max_sta, width=10, fill='▒', empty='░', color=sta_c, reset=rst)}  PST{p_broken}",
            f"  {'Foe':<6} {bar(enemy.hp, enemy.max_hp, color=hp_c, reset=rst)}  ATK {enemy.effective_atk}  DEF {enemy.effective_defense}{e_eff}",
            f"  {'':6} {bar(enemy.stamina, enemy.max_sta, width=10, fill='▒', empty='░', color=sta_c, reset=rst)}  PST{e_broken}",
        ]
