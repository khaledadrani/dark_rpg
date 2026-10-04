"""IO abstraction.

Every piece of user interaction (printing, typing, sleeping, clearing the
screen, turn timers) goes through :class:`GameIO`.  The real game uses
:class:`DefaultIO`; tests and headless simulations inject fakes (see
:mod:`dark_rpg.testing`), which makes the whole game deterministic and
scriptable.
"""
from __future__ import annotations

import builtins
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

#: A prompt sent to the player. ``kind`` identifies *what* is being asked so
#: that scripts/policies can respond sensibly; ``state`` carries game context
#: (hp, floor, enemy intent, ...) for decision-making policies.
@dataclass(frozen=True)
class Prompt:
    kind: str
    text: str
    state: Dict[str, Any] = field(default_factory=dict)


def _default_clear() -> None:
    """Clear the screen without spawning a subprocess (ANSI escapes).
    On Windows cmd, fall back to ``cls``."""
    if os.name == "nt":
        os.system("cls")
    else:
        builtins.print("\033[2J\033[H", end="", flush=True)


class GameIO:
    """Wraps all terminal interaction.  Every method can be overridden."""

    def __init__(
        self,
        cfg: Optional[dict] = None,
        *,
        input_fn: Optional[Callable[[Prompt], str]] = None,
        print_fn: Optional[Callable[..., None]] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
        clear_fn: Optional[Callable[[], None]] = None,
        slow_print_delay: Optional[float] = None,
        turn_timer_enabled: Optional[bool] = None,
        turn_timer_seconds: Optional[float] = None,
        ascii_art: Optional[bool] = None,
        art_frame_delay: Optional[float] = None,
    ) -> None:
        cfg = cfg or {}
        ui = cfg.get("ui", {})
        turn_timer = cfg.get("game", {}).get("turn_timer", {})

        # The typewriter effect only makes sense on an interactive terminal;
        # when stdout is a pipe/file (scripts, CI, simulations) it would make
        # the game glacially slow, so it auto-disables.  An explicit
        # slow_print_delay (e.g. tests) always wins.
        if slow_print_delay is not None:
            self.slow_print_delay = slow_print_delay
        elif sys.stdout.isatty():
            self.slow_print_delay = ui.get("slow_print_delay", 0.03)
        else:
            self.slow_print_delay = 0.0

        # ASCII art toggle + animation speed (see dark_rpg.art).
        # Animation only runs when slow_print_delay > 0 (interactive).
        self.ascii_art = ascii_art if ascii_art is not None else ui.get("ascii_art", True)
        self.art_frame_delay = (
            art_frame_delay if art_frame_delay is not None
            else ui.get("art_frame_delay", 0.15)
        )
        # ANSI colour: on by default, but only active on a real terminal so
        # piped output (logs, CI, simulations) stays clean.
        self.ansi_color = ui.get("ansi_color", True) and sys.stdout.isatty()

        self.turn_timer_enabled = (
            turn_timer_enabled if turn_timer_enabled is not None
            else turn_timer.get("enabled", True)
        )
        self.turn_timer_seconds = (
            turn_timer_seconds if turn_timer_seconds is not None
            else turn_timer.get("seconds", 60)
        )

        self._input_fn = input_fn or (lambda prompt: builtins.input(prompt.text))
        self._print_fn = print_fn or builtins.print
        self._sleep_fn = sleep_fn or time.sleep
        self._clear_fn = clear_fn or _default_clear

    # ── output ──────────────────────────────────────────────────────────
    def out(self, text: str = "") -> None:
        """Print a plain line."""
        self._print_fn(text)

    def slow_out(self, text: str = "", delay: Optional[float] = None) -> None:
        """Print with a typewriter effect; instant when delay <= 0."""
        delay = self.slow_print_delay if delay is None else delay
        if delay <= 0:
            self._print_fn(text)
            return
        for ch in text:
            self._print_fn(ch, end="", flush=True)
            self._sleep_fn(delay)
        self._print_fn()

    def clear(self) -> None:
        self._clear_fn()

    def sleep(self, seconds: float) -> None:
        """Pause (used by art animation)."""
        self._sleep_fn(seconds)

    # ── input ───────────────────────────────────────────────────────────
    def ask(self, prompt: Prompt) -> str:
        """Block for a line of input.

        Closed stdin (EOF) degrades to an empty string instead of crashing,
        so piping ``</dev/null`` is safe.
        """
        try:
            return self._input_fn(prompt)
        except EOFError:
            return ""

    def pause(self, msg: str = "Press Enter to continue...") -> str:
        return self.ask(Prompt("pause", f"\n{msg}"))

    def timed_input(self, prompt: Prompt, seconds: Optional[float] = None) -> Optional[str]:
        """Ask with a countdown; returns None if the time runs out.

        If ``turn_timer_enabled`` is False this behaves like :meth:`ask`
        (used by tests and simulations).
        """
        seconds = self.turn_timer_seconds if seconds is None else seconds
        if not self.turn_timer_enabled:
            return self.ask(prompt)

        result: list[Optional[str]] = [None]
        stop = threading.Event()
        answered = threading.Event()

        def read_input() -> None:
            try:
                result[0] = self.ask(prompt)
            except EOFError:
                pass
            answered.set()
            stop.set()

        def countdown() -> None:
            for remaining in range(int(seconds), 0, -1):
                if stop.is_set():
                    return
                self._print_fn(f"\r{prompt.text}  [{remaining:2d}s] ", end="", flush=True)
                self._sleep_fn(1)
            if not stop.is_set():
                self._print_fn(f"\r{prompt.text}  [ 0s] ")
                stop.set()

        self._print_fn(f"{prompt.text}  [{seconds:2d}s] ", end="", flush=True)
        t_input = threading.Thread(target=read_input, daemon=True)
        t_countdown = threading.Thread(target=countdown, daemon=True)
        t_input.start()
        t_countdown.start()
        stop.wait(timeout=seconds + 0.5)

        if answered.is_set():
            self._print_fn()
            return result[0]
        self._print_fn("\n  ⏱  Time's up! You hesitate.")
        return None
