"""Animated ASCII art for scenery and enemies.

Every piece of art is a *list of frames* (each frame a multi-line string).
On an interactive terminal the frames cycle in place (ANSI cursor-up
escapes) for a flicker/pulse/flap effect; when stdout is a pipe/file or
animation is off, the first frame is printed once as a static picture.

Toggle the whole feature with ``config.json -> ui.ascii_art``
(``false`` prints no art at all).  See :func:`play_art`.

Registries:

* :data:`SCENERY_ART` — keyed by room-event id (loot, rest, trap, ...)
* :data:`ENEMY_ART` — keyed by enemy name (fallback for unknown names)

Everything is plain ASCII so it renders on any terminal.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# ────────────────────────────────────────────────────────────────────────
#  Scenery (keyed by room event id, plus "stairs" for floor transitions)
# ────────────────────────────────────────────────────────────────────────

SCENERY_ART: Dict[str, List[str]] = {
    # ── enemy room: torch-lit corridor with eyes in the dark ──
    "enemy": [
        r"""
      .--.          .--.
     /    \        /    \
    |  ~~  |      |  ~~  |
     \    /        \    /
      '--'          '--'
   ...damp stone... eyes glint...""",
        r"""
      .--.          .--.
     /    \        /    \
    |  ~~  |      |  ~~  |
     \    /        \    /
      '--'          '--'
   ...damp stone... *eyes GLARE*""",
    ],
    # ── loot: treasure chest, lid opens with a glow ──
    "loot": [
        r"""
    ___________
   /          /|
  /  ______  / |
 /  /    /  /  |
/  /____/  /  /
|  |####|  | /
|__|####|__|/
  * locked...""",
        r"""
    ___________
   /   ___    /|
  /  (###)   / |
 /   (###)  /  |
/    (###) /  /
|  .-'''-.  | /
|_/ GOLD! \_|/
   * open! *""",
    ],
    # ── rest: campfire, flame flickers ──
    "rest": [
        r"""
        (  )
       (    )
      (      )
       \    /
        \  /
     --------
    /  \  /  \
   /    \/    \
   __  _  __  _
   \ \/ \/ / /
    \______/""",
        r"""
        (  )
       (    )
      (  __  )
       (    )
        \  /
     --------
    /  \  /  \
   /    \/    \
   __  _  __  _
   \ \/ \/ / /
    \______/""",
    ],
    # ── trap: spiked pit ──
    "trap": [
        r"""
   . . . . . . . .
  .  .  .  .  .  .
   . . . . . . . .
   __ __ __ __ __
  |  |  |  |  |  |
  |  |  |  |  |  |
  |__|__|__|__|__|
    * stone floor *""",
        r"""
   . . . . . . . .
  .  .  .  .  .  .
   . . . . . . . .
   ^^ ^^ ^^ ^^ ^^
  || || || || || ||
  || || || || || ||
  |^||^||^||^||^||
    * SPIKES! *""",
    ],
    # ── merchant: stall with a hooded figure ──
    "merchant": [
        r"""
     ___________
    /  _     _  \
   |  (_)   (_) |
   |    \___/   |
   |  .-'''-.   |
   | /  '~'  \  |
   | \  ___  /  |
   |  '-----'   |
   |  [wares]   |
   |___________|""",
        r"""
     ___________
    /  _     _  \
   |  (-)   (-) |
   |    \___/   |
   |  .-'''-.   |
   | /  '~'  \  |
   | \  ___  /  |
   |  '-----'   |
   |  [wares]   |
   |___________|""",
    ],
    # ── shrine: altar with a pulsing glow ──
    "shrine": [
        r"""
         /\
        /  \
       /    \
      /      \
     /  ____  \
    |  |    |  |
    |  | /\ |  |
    |__|/  \|__|
       |    |
       |____|
     * silent... *""",
        r"""
         /\
        /  \
       /    \
      /      \
     /  ____  \
    |  | *  |  |
    |  |/ \ |  |
    |__|   |__|
       | *  |
       |____|
     * it hums... *""",
    ],
    # ── vault: a big gilded chest, lock glints ──
    "vault": [
        r"""
      ____________
     |  ________  |
     | | $$$$$$ | |
     | |______| | |
     |__________|
      |________|
       * glints... *""",
        r"""
      ____________
     |  ________  |
     | | $$$$$$ | |
     | |______| | |
     |__________|
      |________|
      * GLINTS! *""",
    ],
    # ── curse: a cracked obsidian altar, purple smoke ──
    "curse": [
        r"""
        /\
       /  \
      / ?  \
     /______\
    /  ~~~~  \
   /__________\
      * hums *""",
        r"""
        /\
       /  \
      / ?  \
     /______\
    /  ~~~~  \
   /__________\
    * PURPLE SMOKE *""",
    ],
    # ── ambush: a shadowy figure lunges from a dark arch ──
    "ambush": [
        r"""
       ___________
      /           \
     /     ()()    \
    |      ____     |
    |     |    |    |
    |     |    |    |
    |_____|____|____|
      * something moves *""",
        r"""
       ___________
      /           \
     /     ()()    \
    |      ____     |
    |     |    |    |
    |     |    |    |
    |_____|____|____|
     * SOMETHING LUNGES! *""",
    ],
    # ── gamble: a masked figure holds out a coin ──
    "gamble": [
        r"""
        .-.
       /   \
      |  -- |
      |     |
      |_____|
      | O  O |
       \___/
      [ coin ]
       * winks *""",
        r"""
        .-.
       /   \
      |  -- |
      |     |
      |_____|
      | o  o |
       \___/
      [ coin ]
      * winks back *""",
    ],
    # ── secret: a half-hidden stone alcove with a glimmer ──
    "secret": [
        r"""
      __________
     /          \
    |   .    .   |
    |   .  *  .   |
    |__________|
    |          |
      * a glimmer *""",
        r"""
      __________
     /          \
    |   .    .   |
    |   .  *  .   |
    |__________|
    |          |
     * A GLIMMER! *""",
    ],
    # ── stairs down (floor transitions) ──
    "stairs": [
        r"""
      ________
     /       /|
    /_______/ |
   |  ____  | |
   | |____| | |
   |  ____  | |
   | |____| |/
   |________|
   ~~~~~~~~~~~~
   * descending... *""",
    ],
}

# ────────────────────────────────────────────────────────────────────────
#  Enemies (keyed by exact enemy name; fallback for unknowns)
# ────────────────────────────────────────────────────────────────────────

ENEMY_ART: Dict[str, List[str]] = {
    # ── Goblin: small, sneaky, eyes glow ──
    "Goblin": [
        r"""
    __,-~~~-.__
   /           \
  |  (o)   (o)  |
  |    \___/    |
   \  '-----'  /
    '-,     ,-'
       \___/
    short & sneaky""",
        r"""
    __,-~~~-.__
   /           \
  |  (O)   (O)  |
  |    \___/    |
   \  '-----'  /
    '-,     ,-'
       \___/
    short & *grinning*""",
    ],
    # ── Skeleton: rattles, jaw drops ──
    "Skeleton": [
        r"""
      .-----.
     /  _   _ \
    |  (o)_(o) |
     \  _____  /
    --'  |  '--
   /  /\ | /\  \
  /  /  \|/  \  \
  \  \  /|\  /  /
   \  \/ | \/  /
    '----'----'
    * rattles *""",
        r"""
      .-----.
     /  _   _ \
    |  ( )_( ) |
     \  _____  /
    --'  vvv  '--
   /  /\ | /\  \
  /  /  \|/  \  \
  \  \  /|\  /  /
   \  \/ | \/  /
    '----'----'
    * JAW CHATTERS *""",
    ],
    # ── Orc: big, brutish, snarls ──
    "Orc": [
        r"""
     ___________
    /           \
   |  ( , ) ( , )|
   |    \___/    |
   |   _/   \_   |
   |  |vvvvvvv|  |
   |  |_______|  |
   |    |   |    |
   |    |   |    |
   |____|___|____|
    * hulking *""",
        r"""
     ___________
    /           \
   |  ( > ) ( < )|
   |    \___/    |
   |   _/   \_   |
   |  |^^^^^^^|  |
   |  |_______|  |
   |    |   |    |
   |    |   |    |
   |____|___|____|
    * SNARLING *""",
    ],
    # ── Dark Knight: armoured, visor glows ──
    "Dark Knight": [
        r"""
      _________
     /         \
    |  _______  |
    | |       | |
    | |  ___  | |
    | | |   | | |
    | | |___| | |
    | |_______| |
    |  |  |  |  |
    |  |  |  |  |
    |__|__|__|__|
    * cold steel *""",
        r"""
      _________
     /         \
    |  _______  |
    | |       | |
    | |  _O_  | |
    | | |   | | |
    | | |___| | |
    | |_______| |
    |  |  |  |  |
    |  |  |  |  |
    |__|__|__|__|
    * visor GLOWS *""",
    ],
    # ── Dragon: wings rise, embers glow ──
    "Dragon": [
        r"""
      \        /
       \  __  /
        \(  )/
        / /\ \
       / /  \ \
      / /    \ \
     | |  __  | |
     | | |  | | |
     | | |__| | |
      \ |____| /
       \______/
      ~~ embers ~~""",
        r"""
      \        /
       \  /\  /
        \( o)/
        / /\ \
       / /  \ \
      / /    \ \
     | |  __  | |
     | | |**| | |
     | | |__| | |
      \ |____| /
       \______/
      ~~ EMBERS FLARE ~~""",
    ],
    # ── Giant Rat: small, scurrying, red eyes ──
    "Giant Rat": [
        r"""
         ___
        /o o\
       (  >  )~
        \___/
       ~~~~~~~
        * squeaks *""",
        r"""
         ___
        /O O\
       (  >  )~
        \___/
       ~~~~~~~
        * SCURRIES *""",
    ],
    # ── Cave Spider: many legs, flicker ──
    "Cave Spider": [
        r"""
       /  |\  /
      / \ | / \
     (   (o)   )
      \ / | \ /
       \  |  /
        \|/|
       * skitters *""",
        r"""
       /  |\  /
      / \ | / \
     (   (O)   )
      \ / | \ /
       \  |  /
        \|/|
       * skitters faster *""",
    ],
    # ── Cultist: hooded, robed, staff ──
    "Cultist": [
        r"""
         .-.
        /   \
       | o o |
       |  ^  |
      _|___|_
      / | | \
     (  | |  )
        | |
        |_|
       * chants *""",
        r"""
         .-.
        /   \
       | O O |
       |  o  |
      _|___|_
      / | | \
     (  | |  )
        | |
        |_|
       * chants louder *""",
    ],
    # ── Wraith: ghostly, translucent, dripping ──
    "Wraith": [
        r"""
        .-"""
        r""".-
       /     \
      |  o o  |
      |   ~   |
       \  ~  /
        ~~~~~
       * drifts *""",
        r"""
        .-"""
        r""".-
       /     \
      |  O O  |
      |   ~   |
       \  ~  /
        ~~~~~
       * DRIFTS *""",
    ],
    # ── Assassin: masked, dual daggers ──
    "Assassin": [
        r"""
       ___
      /~~~\
      \___/
     /|^^|\
    / |__| \
      |  |
     /|  |\
     |_|_|
       * silent *""",
        r"""
       ___
      /~~~\
      \___/
     /|##|\
    / |__| \
      |  |
     /|  |\
     |_|_|
       * silent... *""",
    ],
    # ── Vampire: pale, fangs, cape ──
    "Vampire": [
        r"""
        .-.
       /v v\
      | o o |
      | \v/ |
      |__\_/|
     \ |   | /
      \|___|/
       * fangs out *""",
        r"""
        .-.
       /v v\
      | O O |
      | \v/ |
      |__\_/|
     \ |   | /
      \|___|/
       * FANGS SNAP *""",
    ],
    # ── Lich: skeletal mage, glowing eyes, staff ──
    "Lich": [
        r"""
      .-"""
        r"""-.
     / x x \
    |  \_/  |
    |  ___  |
     \ | | /
     -.| |.-
        |_|
       * bone chimes *""",
        r"""
      .-"""
        r"""-.
     / X X \
    |  \_/  |
    |  ___  |
     \ | | /
     -.| |.-
        |_|
       * BONE CHIMES *""",
    ],
    # ── The Dungeon Tyrant (boss): crown, glowing eyes ──
    "The Dungeon Tyrant": [
        r"""
        _.-""-._
      .'  _____  '.
     /   /     \   \
    |   |  _ _  |   |
    |   | (o o) |   |
    |   |  \_/  |   |
     \   \_____/   /
      '.  _   _  .'
        '-(_)-'
       /  | |  \
      /   |_|   \
     /    | |    \
    /_____|_|_____\
    * THE DUNGEON TYRANT *""",
        r"""
        _.-""-._
      .'  _____  '.
     /   /     \   \
    |   |  _ _  |   |
    |   | (O O) |   |
    |   |  \_/  |   |
     \   \_____/   /
      '.  _   _  .'
        '-(_)-'
       /  | |  \
      /   |_|   \
     /    | |    \
    /_____|_|_____\
    * THE TYRANT AWAKENS *""",
    ],
}

#: fallback used for any enemy without its own art
DEFAULT_ENEMY_ART: List[str] = [
    r"""
      _______
     /       \
    |  (o o)  |
    |   \_/   |
    |  _____  |
     \_______/
    * a menacing foe *""",
    r"""
      _______
     /       \
    |  (O O)  |
    |   \_/   |
    |  _____  |
     \_______/
    * a MENACING foe *""",
]

DEFAULT_SCENERY_ART: List[str] = [
    r"""
      _______
     /       \
    |  ? ? ?  |
     \_______/
    * something is here *""",
]


# ────────────────────────────────────────────────────────────────────────
#  Lookup helpers
# ────────────────────────────────────────────────────────────────────────

def scenery_art(event_id: str) -> List[str]:
    """Frames for a room event's scenery; graceful fallback."""
    return SCENERY_ART.get(event_id, DEFAULT_SCENERY_ART)


def enemy_art(name: str) -> List[str]:
    """Frames for an enemy by name; graceful fallback."""
    return ENEMY_ART.get(name, DEFAULT_ENEMY_ART)


def art_coverage() -> Dict[str, List[str]]:
    """All registered art keys (used by tests to guarantee coverage)."""
    return {"scenery": sorted(SCENERY_ART), "enemies": sorted(ENEMY_ART)}


# ────────────────────────────────────────────────────────────────────────
#  Playback
# ────────────────────────────────────────────────────────────────────────

def play_art(io, frames: List[str], loops: int = 2, delay: Optional[float] = None) -> None:
    """Print *frames* through *io*.

    * ``io.ascii_art`` is False  -> nothing is printed (feature off).
    * stdout is not interactive (``slow_print_delay <= 0``) or one frame
      -> the first frame prints once (static; keeps logs/CI clean).
    * interactive terminal -> frames cycle in place (flicker/pulse/flap).
    """
    if not getattr(io, "ascii_art", True):
        return
    frames = list(frames) or [""]
    if getattr(io, "slow_print_delay", 0) <= 0 or len(frames) == 1:
        io.out(frames[0])
        return

    delay = io.art_frame_delay if delay is None else delay
    height = frames[0].count("\n") + 1
    cursor_up = f"\033[{height}A"
    for _ in range(loops):
        for frame in frames:
            io.out(frame)
            io.sleep(delay)
            io.out(cursor_up)
    # settle on the idle frame so the art rests in its base state
    io.out(frames[0])
    io.out("")
