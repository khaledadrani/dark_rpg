import random
import time
import os

# ─────────────────────────────────────────
#  CONFIG  (tweak freely)
# ─────────────────────────────────────────
PLAYER = {
    "name":    "You",
    "hp":      40,
    "atk":     8,
    "defense": 3,
    "stamina": 24,
}

ENEMIES = [
    {
        "name":    "Bandit",
        "hp":      30,
        "atk":     6,
        "defense": 2,
        "stamina": 24,
        "ai": {"attack": 55, "heavy": 25, "defend": 20},
        "flavor": "A scruffy outlaw with hungry eyes.",
    },
    {
        "name":    "Knight",
        "hp":      45,
        "atk":     9,
        "defense": 5,
        "stamina": 24,
        "ai": {"attack": 35, "heavy": 30, "defend": 35},
        "flavor": "Plate armor, cold visor. No words.",
    },
    {
        "name":    "Berserker",
        "hp":      55,
        "atk":     13,
        "defense": 1,
        "stamina": 24,
        "ai": {"attack": 40, "heavy": 55, "defend": 5},
        "flavor": "Foaming at the mouth. All offense, no sense.",
    },
    {
        "name":    "Duelist",
        "hp":      38,
        "atk":     10,
        "defense": 4,
        "stamina": 24,
        "ai": {"attack": 45, "heavy": 20, "defend": 35},
        "flavor": "Precise, patient. Waiting for your mistake.",
    },
]

STAMINA = {
    "max":              24,
    "cost_attack":       2,
    "cost_heavy":        4,
    "cost_deflect":      1,   # cheap on success
    "cost_deflect_fail": 6,   # punishing on failure
    "cost_dodge":        3,
    "cost_dodge_fail":   5,
    "hit_drain":         4,   # stamina lost when a normal hit lands on you
    "heavy_drain":       7,   # stamina lost when a heavy hit lands on you
    "broken_dmg_mult":  1.75, # damage multiplier while broken
    "broken_restore":   0.5,  # fraction of stamina restored after broken turn
    "defend_regen":      4,   # stamina regen when defending and enemy doesn't attack
}

# ─────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def slow_print(text, delay=0.025):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def pause():
    input("\n  [Enter] ")

def roll(sides=20):
    return random.randint(1, sides)

def bar(cur, mx, width=20, fill="█", empty="░"):
    cur    = max(0, cur)
    filled = int(width * cur / max(mx, 1))
    return f"[{fill*filled}{empty*(width-filled)}] {cur}/{mx}"

def sta_bar(cur, mx, width=16):
    cur    = max(0, cur)
    filled = int(width * cur / max(mx, 1))
    color_fill  = "▓" if cur > mx * 0.3 else "▒"   # visual warning near 0
    return f"[{color_fill*filled}{'░'*(width-filled)}] {cur}/{mx}"

def pick_action(weights: dict) -> str:
    return random.choices(list(weights.keys()), list(weights.values()))[0]

# ─────────────────────────────────────────
#  COMBATANT
# ─────────────────────────────────────────
class Combatant:
    def __init__(self, template):
        self.name    = template["name"]
        self.hp      = template["hp"]
        self.max_hp  = template["hp"]
        self.atk     = template["atk"]
        self.defense = template["defense"]
        self.stamina = STAMINA["max"]
        self.broken  = False

    def is_alive(self):
        return self.hp > 0

    def drain_stamina(self, amount):
        self.stamina = max(0, self.stamina - amount)
        if self.stamina == 0 and not self.broken:
            self.broken = True
            return True   # just broke
        return False

    def restore_stamina(self, amount):
        self.stamina = min(STAMINA["max"], self.stamina + amount)
        if self.stamina > 0:
            self.broken = False

    def take_damage(self, raw_atk, drain_key="hit_drain"):
        dmg = max(1, raw_atk - self.defense)
        if self.broken:
            dmg = int(dmg * STAMINA["broken_dmg_mult"])
        self.hp = max(0, self.hp - dmg)
        broke = self.drain_stamina(STAMINA[drain_key])
        return dmg, broke

# ─────────────────────────────────────────
#  DISPLAY
# ─────────────────────────────────────────
def draw_hud(player, enemy):
    print()
    p_broken = "  💀 BROKEN" if player.broken else ""
    e_broken = "  💀 BROKEN" if enemy.broken  else ""

    print(f"  {player.name:<12}  HP  {bar(player.hp, player.max_hp)}")
    print(f"  {'':12}  PST {sta_bar(player.stamina, STAMINA['max'])}{p_broken}")
    print()
    print(f"  {enemy.name:<12}  HP  {bar(enemy.hp, enemy.max_hp)}")
    print(f"  {'':12}  PST {sta_bar(enemy.stamina, STAMINA['max'])}{e_broken}")
    print()

def show_intent(intent):
    labels = {
        "attack": "winds up a normal strike",
        "heavy":  "charges a HEAVY blow",
        "defend": "braces defensively",
    }
    slow_print(f"  ⚔  Enemy {labels.get(intent, intent)}...")

# ─────────────────────────────────────────
#  RESOLVE ONE TURN
# ─────────────────────────────────────────
def resolve(player, enemy, p_action, e_intent):
    SC   = STAMINA
    msgs = []

    # ── Broken player: forced weak block, stamina partially restores ──
    if player.broken:
        restore = int(SC["max"] * SC["broken_restore"])
        player.restore_stamina(restore)
        msgs.append(f"  You scramble back — posture partially restored (+{restore} PST).")
        # still eat the hit
        if e_intent in ("attack", "heavy"):
            drain_key = "heavy_drain" if e_intent == "heavy" else "hit_drain"
            dmg, _ = enemy_hits(enemy, player, drain_key)
            msgs.append(f"  {enemy.name} punishes your broken state for {dmg} damage!")
        return msgs

    # ── Normal turn ──

    # 1. Player acts
    if p_action == "attack":
        player.drain_stamina(SC["cost_attack"])
        if roll() + player.atk > 10:
            dmg = max(1, player.atk - enemy.defense)
            enemy.hp = max(0, enemy.hp - dmg)
            broke = enemy.drain_stamina(SC["hit_drain"])
            msgs.append(f"  You strike! {dmg} dmg  |  −{SC['hit_drain']} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
        else:
            msgs.append("  Your attack whiffs.")

    elif p_action == "heavy":
        player.drain_stamina(SC["cost_heavy"])
        if roll() + player.atk > 13:   # harder to land
            dmg = max(1, int(player.atk * 1.8) - enemy.defense)
            enemy.hp = max(0, enemy.hp - dmg)
            broke = enemy.drain_stamina(SC["heavy_drain"])
            msgs.append(f"  HEAVY blow connects! {dmg} dmg  |  −{SC['heavy_drain']} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
        else:
            msgs.append("  Heavy swing misses — you're open!")
            # punish miss: enemy gets a free counter if they were attacking
            if e_intent == "attack":
                dmg, broke = enemy_hits(enemy, player, "hit_drain")
                msgs.append(f"  {enemy.name} counters! {dmg} damage{' → YOU BROKE!' if broke else ''}.")
                return msgs

    elif p_action == "deflect":
        # Success if enemy attacks; failure if enemy defends (wasted)
        if e_intent in ("attack", "heavy"):
            drain_key = "heavy_drain" if e_intent == "heavy" else "hit_drain"
            player.drain_stamina(SC["cost_deflect"])
            enemy.drain_stamina(SC[drain_key])   # deflect drains ENEMY posture
            broke = enemy.stamina == 0 and enemy.broken
            msgs.append(f"  DEFLECT! Enemy posture broken down  −{SC[drain_key]} enemy PST{' → ENEMY BROKEN!' if broke else ''}")
            msgs.append(f"  (You spent only {SC['cost_deflect']} PST)")
            return msgs   # no enemy attack lands
        else:
            # enemy was defending — deflect wastes your stamina into the void
            player.drain_stamina(SC["cost_deflect_fail"])
            msgs.append(f"  Deflect whiff — enemy wasn't attacking. −{SC['cost_deflect_fail']} PST wasted.")
            return msgs

    elif p_action == "dodge":
        if e_intent in ("attack", "heavy"):
            if roll() > 8:   # 60% success
                player.drain_stamina(SC["cost_dodge"])
                msgs.append("  You sidestep cleanly. Attack dodged!")
                return msgs
            else:
                player.drain_stamina(SC["cost_dodge_fail"])
                drain_key = "heavy_drain" if e_intent == "heavy" else "hit_drain"
                dmg, broke = enemy_hits(enemy, player, drain_key)
                msgs.append(f"  Dodge mistimed! {dmg} damage{' → YOU BROKE!' if broke else ''}. −{SC['cost_dodge_fail']} PST.")
                return msgs
        else:
            player.drain_stamina(SC["cost_dodge"])
            msgs.append("  You dodge... into nothing. PST spent for no gain.")
            return msgs

    elif p_action == "defend":
        # no stamina cost upfront; regen if enemy doesn't attack
        pass

    # 2. Enemy acts (unless already resolved above)
    if e_intent in ("attack", "heavy"):
        drain_key = "heavy_drain" if e_intent == "heavy" else "hit_drain"
        if p_action == "defend":
            # defend halves damage and halves posture drain
            raw_dmg  = max(1, enemy.atk - player.defense * 2)
            if player.broken:
                raw_dmg = int(raw_dmg * SC["broken_dmg_mult"])
            player.hp = max(0, player.hp - raw_dmg)
            drain_amt = STAMINA[drain_key] // 2
            broke = player.drain_stamina(drain_amt)
            msgs.append(f"  {enemy.name} strikes. Guarded: {raw_dmg} dmg  −{drain_amt} PST{' → YOU BROKE!' if broke else ''}")
        else:
            dmg, broke = enemy_hits(enemy, player, drain_key)
            label = "HEAVY " if e_intent == "heavy" else ""
            msgs.append(f"  {enemy.name} {label}hits you for {dmg} damage{' → YOU BROKE!' if broke else ''}.")
    elif e_intent == "defend":
        if p_action == "defend":
            # both defend: stamina regen for player
            player.restore_stamina(SC["defend_regen"])
            msgs.append(f"  Standoff. Both brace. You recover {SC['defend_regen']} PST.")
        else:
            msgs.append(f"  {enemy.name} defends. Your attack lands but enemy posture holds.")

    return msgs


def enemy_hits(enemy, target, drain_key):
    dmg = max(1, enemy.atk - target.defense)
    if target.broken:
        dmg = int(dmg * STAMINA["broken_dmg_mult"])
    target.hp = max(0, target.hp - dmg)
    broke = target.drain_stamina(STAMINA[drain_key])
    return dmg, broke

# ─────────────────────────────────────────
#  DUEL LOOP
# ─────────────────────────────────────────
ACTIONS = {
    "1": ("attack",  "Attack        (−2 PST | drains enemy PST on hit)"),
    "2": ("heavy",   "Heavy Strike  (−4 PST | big dmg+drain, harder to land)"),
    "3": ("deflect", "Deflect       (−1 PST on success | failure = −6 PST)"),
    "4": ("dodge",   "Dodge         (−3 PST | 60% evade, −5 if mistimed)"),
    "5": ("defend",  "Defend        (half damage+drain | regen PST if idle)"),
}

def duel(player_tmpl, enemy_tmpl):
    player = Combatant(player_tmpl)
    enemy  = Combatant(enemy_tmpl)

    clear()
    slow_print(f"\n  ── DUEL ──  {player.name}  vs  {enemy.name}")
    slow_print(f"  {enemy_tmpl['flavor']}")
    pause()

    turn = 0
    while player.is_alive() and enemy.is_alive():
        turn += 1
        clear()
        print(f"\n  ── Turn {turn} ──")
        draw_hud(player, enemy)

        # enemy picks intent (shown to player — the read-the-enemy game)
        e_intent = pick_action(enemy_tmpl["ai"])
        show_intent(e_intent)
        print()

        # player chooses
        if player.broken:
            slow_print("  💀 You are BROKEN — posture restoring, incoming damage amplified.")
            print()
            for k, (_, desc) in ACTIONS.items():
                print(f"  [{k}] {desc}")
            choice = input("\n  > ").strip()
            p_action = ACTIONS.get(choice, ("defend",))[0]
        else:
            for k, (_, desc) in ACTIONS.items():
                print(f"  [{k}] {desc}")
            choice = input("\n  > ").strip()
            if choice not in ACTIONS:
                slow_print("  Invalid — you freeze. Enemy acts.")
                p_action = "defend"
            else:
                p_action = ACTIONS[choice][0]

        print()
        msgs = resolve(player, enemy, p_action, e_intent)
        for m in msgs:
            slow_print(m)

        pause()

    return player.is_alive()

# ─────────────────────────────────────────
#  ENEMY SELECT + MAIN
# ─────────────────────────────────────────
def select_enemy():
    clear()
    print("\n  Choose your opponent:\n")
    for i, e in enumerate(ENEMIES, 1):
        print(f"  [{i}] {e['name']:<14}  HP {e['hp']}  ATK {e['atk']}  DEF {e['defense']}")
        print(f"       {e['flavor']}")
        print()
    choice = input("  > ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(ENEMIES):
        return ENEMIES[int(choice) - 1]
    return ENEMIES[0]

def main():
    clear()
    print("""
  ╔══════════════════════════════════════╗
  ║              D U E L                ║
  ║     posture · deflect · survive     ║
  ╚══════════════════════════════════════╝
    """)
    input("  Press Enter to begin...\n")

    while True:
        enemy = select_enemy()
        won   = duel(PLAYER, enemy)

        clear()
        if won:
            slow_print("\n  ══════════════════════════════")
            slow_print("   VICTORY. Your opponent falls.")
            slow_print("  ══════════════════════════════")
        else:
            slow_print("\n  ══════════════════════════════")
            slow_print("   DEFEATED. The dust settles.")
            slow_print("  ══════════════════════════════")

        print("\n  [R] Rematch   [N] New opponent   [Q] Quit")
        again = input("  > ").strip().lower()
        if again == "q":
            break
        if again == "n":
            continue
        # rematch same enemy
        won = duel(PLAYER, enemy)

if __name__ == "__main__":
    main()