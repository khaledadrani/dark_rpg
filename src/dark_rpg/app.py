"""The Game orchestrator: floors, rooms, combat loop, boss, save flow."""
from __future__ import annotations

import os
import random
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from dark_rpg.art import enemy_art, play_art, scenery_art
from dark_rpg.combat import get_combat_mode
from dark_rpg.config import load_config  # noqa: F401  (re-exported convenience)
from dark_rpg.entities import Player
from dark_rpg.io import GameIO, Prompt
from dark_rpg.save import SaveError, delete_save, load_game
from dark_rpg.ui import article
from dark_rpg.world.enemies import make_combatant
from dark_rpg.world.rooms import run_room

TITLE = """
  ╔══════════════════════════════════════╗
  ║         D U N G E O N  R U N        ║
  ║    A text RPG with a feedback loop   ║
  ╚══════════════════════════════════════╝
"""


@dataclass
class RunStats:
    """Metrics collected during a run (used by tests & simulations)."""

    deaths: int = 0      # times the player died in combat (scars applied)
    fights: int = 0      # combats started
    rooms: int = 0       # rooms entered


@dataclass
class GameResult:
    """Summary of a finished run."""

    outcome: str         # "win" | "dead"
    floors_cleared: int
    level: int
    scars: int
    gold: int
    deaths: int
    fights: int
    rooms: int

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Game:
    """Owns config, IO, RNG and the run loop.  Fully headless-testable."""

    def __init__(
        self,
        cfg: Dict[str, Any],
        io: Optional[GameIO] = None,
        rng: Optional[random.Random] = None,
        save_path: Optional[str] = "save.json",
    ) -> None:
        self.cfg = cfg
        self.io = io or GameIO(cfg)
        self.rng = rng or random.Random()
        self.save_path = save_path
        self.combat_mode = get_combat_mode(
            cfg["game"].get("combat_mode", "stamina"), cfg,
            color_on=getattr(self.io, "ansi_color", False),
        )
        self.stats = RunStats()
        self.player: Optional[Player] = None

    # ═══════════════════════════════════════════════════════════════════
    #  COMBAT
    # ═══════════════════════════════════════════════════════════════════
    def run_combat(
        self,
        player: Player,
        template: Dict[str, Any],
        floor: int,
        scale_override: Optional[float] = None,
        room_num: int = 0,
    ) -> str:
        """Fight *template*; returns ``"win"`` | ``"dead"`` | ``"fled"``."""
        mode = self.combat_mode
        enemy = make_combatant(self.cfg, mode, template, floor, scale_override, self.cfg["enemies"])
        ai_weights = template["ai"]

        # animated enemy reveal (bosses included), then the stat line.
        # No extra "Press Enter" here — the player just pressed Enter to
        # enter the room, so we flow straight into the first turn.
        play_art(self.io, enemy_art(enemy.name))
        self.io.slow_out(f"\n  {article(enemy.name)}{enemy.name} appears! ({enemy.hp} HP | ATK {enemy.atk} | DEF {enemy.defense})")

        player.combo = 0
        player.template = {}  # the player has no special abilities
        mode.start_combat(player)
        self.stats.fights += 1

        while enemy.hp > 0 and player.hp > 0:
            self.io.clear()
            for line in mode.hud(player, enemy):
                self.io.out(line)
            if player.combo > 1:
                self.io.out(f"  ⚡ Combo x{player.combo}!")
            self.io.out("")
            for key, label in mode.action_menu():
                self.io.out(f"  [{key}] {label}")
            self.io.out("  [f] Flee (50% chance)")
            self.io.out("")

            # enemy chooses; posture mode reveals the intent before you act
            e_action = mode.pick_enemy_action(enemy, ai_weights, self.rng)
            intent = mode.reveal_intent(enemy, e_action)
            if intent:
                self.io.slow_out(intent)

            forced = mode.forced_action(player)
            if forced:
                action, forced_msg = forced
                self.io.slow_out(forced_msg)
            else:
                prompt = Prompt("combat_action", "  > ", {
                    "mode": mode.key,
                    "player_hp": player.hp,
                    "player_max_hp": player.max_hp,
                    "player_sta": player.stamina,
                    "player_def": player.defense,
                    "enemy_hp": enemy.hp,
                    "enemy_max_hp": enemy.max_hp,
                    "enemy_sta": enemy.stamina,
                    "enemy_atk": enemy.atk,
                    "enemy_def": enemy.defense,
                    "enemy_name": enemy.name,
                    "intent": e_action,
                    "enemy_broken": enemy.broken,
                })
                choice = self.io.timed_input(prompt, self.cfg["game"]["turn_timer"]["seconds"])
                if choice is None:
                    self.io.slow_out("  ⏱  Time's up! You hesitate.")
                    action = mode.idle_action()
                elif choice.strip().lower() == "f":
                    result = self._try_flee(player, enemy)
                    if result == "fled":
                        return "fled"
                    continue
                elif any(key == choice.strip() for key, _ in mode.action_menu()):
                    action = mode.action_for_key(choice.strip())
                else:
                    self.io.slow_out("  Invalid input — you hesitate.")
                    action = mode.idle_action()

            for msg in mode.resolve(player, enemy, action, e_action, self.rng):
                self.io.slow_out(msg)

            if 0 < player.hp <= 4:
                self.io.slow_out("  ⚠  You're barely standing...")
            self.io.pause()

        if player.hp > 0:
            return self._reward(player, enemy, room_num)
        return "dead"

    def _try_flee(self, player: Player, enemy: Any) -> str:
        """Attempt to flee; returns ``"fled"`` or ``"stayed"``.

        Design rule: fleeing never kills outright — the parting blow can
        leave you at 1 HP, but you always escape alive (a final death should
        come from combat or hazards, not from retreating).
        """
        io = self.io
        if self.rng.randint(1, 20) > 10:
            io.slow_out("  You flee! But not before taking a parting blow...")
            dmg = max(1, enemy.atk - player.defense)
            dmg = min(dmg, player.hp - 1)  # can't die from fleeing
            player.take_damage(dmg)
            io.slow_out(f"  {enemy.name} hits you for {dmg} as you run.")
            player.combo = 0
            io.pause()
            return "fled"
        io.slow_out("  Escape blocked! The enemy seizes the opening!")
        for msg in self.combat_mode.flee_fail(player):
            io.slow_out(msg)
        dmg = max(1, enemy.atk - player.defense + 3)
        player.take_damage(dmg)
        io.slow_out(f"  {enemy.name} punishes you for {dmg} damage.")
        io.pause()
        return "stayed"

    def _reward(self, player: Player, enemy: Any, room_num: int) -> str:
        """Apply XP/gold/key rewards after a combat win."""
        cfg, io = self.cfg, self.io
        gold = self.rng.randint(*enemy.gold)
        player.xp += enemy.xp
        player.gold += gold
        io.slow_out(f"\n  {enemy.name} defeated! +{enemy.xp} XP | +{gold} gold")

        if not player.has_key:
            drop_chance = (
                1.0 if room_num >= cfg["game"]["rooms_per_floor"]
                else cfg["game"]["key_drop_chance"]
            )
            if self.rng.random() < drop_chance:
                player.has_key = True
                io.slow_out("  🗝  A floor key drops from the body. You can now descend.")
        for msg in player.try_level_up():
            io.slow_out(msg)
        return "win"

    def run_boss(self, player: Player) -> bool:
        self.io.clear()
        self.io.slow_out("\n  ══════════════════════════════")
        self.io.slow_out("   THE BOSS AWAITS.")
        self.io.slow_out("  ══════════════════════════════")
        self.io.pause()
        result = self.run_combat(player, self.cfg["boss"], player.floor, scale_override=1.0)
        return result == "win"

    # ═══════════════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════
    def _new_player(self) -> Player:
        name = self.io.ask(Prompt("name", "  Enter your name, adventurer: ", {})).strip() or "Hero"
        player = Player(name, self.cfg)
        self.io.slow_out(f"\n  Welcome, {name}. Descend {self.cfg['game']['floor_count']} floors. Survive.")
        self.io.pause()
        return player

    def _load_or_new_player(self) -> Player:
        save_path = self.save_path
        if not save_path or not os.path.exists(save_path):
            return self._new_player()

        self.io.out("  A saved game was found.")
        self.io.out("  [C] Continue   [N] New Game")
        choice = self.io.ask(Prompt("menu", "  > ", {})).strip().lower()
        if choice == "c":
            try:
                player = load_game(save_path, self.cfg)
                self.io.slow_out(f"\n  Welcome back, {player.name}. Floor {player.floor}.")
                self.io.pause()
                return player
            except SaveError as exc:
                self.io.slow_out(f"\n  {exc}")
                self.io.slow_out("  Starting a new game instead.")
                delete_save(self.save_path)
        else:
            delete_save(self.save_path)
        return self._new_player()

    def run(self) -> GameResult:
        """Play a full game (title → floors → boss).  Returns the result."""
        io = self.io
        io.clear()
        io.out(TITLE)

        player = self._load_or_new_player()
        self.player = player
        floor_count = self.cfg["game"]["floor_count"]

        for floor in range(player.floor, floor_count + 1):
            player.floor = floor
            player.has_key = False
            io.clear()
            play_art(io, scenery_art("stairs"))
            io.slow_out(f"\n  ── Floor {floor} of {floor_count} ──")
            io.slow_out("  Find the floor key to descend.")
            io.pause()

            room_num = 0
            while True:
                room_num += 1
                self.stats.rooms += 1
                result = run_room(self, player, room_num)
                if result == "dead":
                    io.slow_out("\n  GAME OVER. The dungeon is undefeated.")
                    self._recap("dead")
                    delete_save(self.save_path)
                    return self._result("dead", floor_count)
                if result == "descend":
                    break

            io.clear()
            io.slow_out(f"  Floor {floor} cleared! You descend deeper...")
            io.pause()

        # boss floor
        player.floor = floor_count
        won = self.run_boss(player)
        io.clear()
        delete_save(self.save_path)

        if won:
            io.slow_out("\n  ══════════════════════════════")
            io.slow_out("   YOU ESCAPED THE DUNGEON!")
            io.slow_out(f"   Floors cleared: {floor_count}")
            io.slow_out(f"   Level reached:  {player.level}")
            io.slow_out(f"   Scars earned:   {player.scars}")
            io.slow_out(f"   Gold carried:   {player.gold}")
            io.slow_out("  ══════════════════════════════")
            self._recap("win")
        else:
            io.slow_out("\n  The Dungeon Tyrant laughs as darkness falls.")
            io.slow_out("  GAME OVER.")
            self._recap("dead")
        return self._result("win" if won else "dead", floor_count)

    def _recap(self, outcome: str) -> None:
        """Print a run-summary recap (deaths, fights, rooms, gold, level)."""
        p = self.player
        assert p is not None, "recap requires a started run"
        self.io.slow_out("")
        self.io.slow_out("  ── RUN RECAP ─────────────────────")
        self.io.slow_out(f"   Outcome:      {'VICTORY' if outcome == 'win' else 'DEFEAT'}")
        self.io.slow_out(f"   Level reached:{p.level}")
        self.io.slow_out(f"   Fights:       {self.stats.fights}")
        self.io.slow_out(f"   Deaths:       {self.stats.deaths}")
        self.io.slow_out(f"   Rooms seen:   {self.stats.rooms}")
        self.io.slow_out(f"   Gold left:    {p.gold}")
        self.io.slow_out("  ─────────────────────────────────")

    def _result(self, outcome: str, floor_count: int) -> GameResult:
        player = self.player
        assert player is not None, "result requires a started run"
        floors_cleared = floor_count if outcome == "win" else max(0, player.floor - 1)
        return GameResult(
            outcome=outcome,
            floors_cleared=floors_cleared,
            level=player.level,
            scars=player.scars,
            gold=player.gold,
            deaths=self.stats.deaths,
            fights=self.stats.fights,
            rooms=self.stats.rooms,
        )
