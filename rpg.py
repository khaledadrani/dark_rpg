import random
import os
import time
import json
import select
import sys
import threading

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
def load_config(path="config.json"):
    with open(path) as f:
        cfg = json.load(f)
    # convert gold lists to tuples so existing code works unchanged
    for e in cfg["enemies"]:
        e["gold"] = tuple(e["gold"])
    cfg["boss"]["gold"] = tuple(cfg["boss"]["gold"])
    return cfg

CFG             = load_config()
FLOOR_COUNT     = CFG["game"]["floor_count"]
ROOMS_PER_FLOOR = CFG["game"]["rooms_per_floor"]
ENEMIES         = CFG["enemies"]
BOSS            = CFG["boss"]
LOOT_TABLE      = CFG["loot_table"]
ROOM_FLAVORS    = CFG["room_flavors"]

SAVE_FILE = "save.json"

def save_game(player):
    data = {k: v for k, v in player.__dict__.items()}
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)

def load_game():
    with open(SAVE_FILE) as f:
        data = json.load(f)
    player = Player(data["name"])
    player.__dict__.update(data)
    return player

def delete_save():
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)

# ─────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def pause(msg="Press Enter to continue..."):
    input(f"\n{msg}")

def roll(sides=20):
    return random.randint(1, sides)

def slow_print(text, delay=0.03):
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def bar(current, maximum, width=20, fill="█", empty="░"):
    filled = int(width * current / max(maximum, 1))
    return f"[{fill*filled}{empty*(width-filled)}] {current}/{maximum}"

def timed_input(prompt, seconds):
    result    = [None]
    stop_flag = threading.Event()

    def countdown():
        for remaining in range(seconds, 0, -1):
            if stop_flag.is_set():
                return
            print(f"\r{prompt}  [{remaining:2d}s] ", end="", flush=True)
            time.sleep(1)
        if not stop_flag.is_set():
            print(f"\r{prompt}  [ 0s] ")

    t = threading.Thread(target=countdown, daemon=True)
    t.start()
    ready, _, _ = select.select([sys.stdin], [], [], seconds)
    stop_flag.set()
    if ready:
        val = sys.stdin.readline().strip()
        print()
        return val
    print(f"\n  ⏱  Time's up! You hesitate.")
    return None

# ─────────────────────────────────────────
#  ENTITY / PLAYER
# ─────────────────────────────────────────
class Entity:
    def __init__(self, name, hp, atk, defense):
        self.name    = name
        self.hp      = hp
        self.max_hp  = hp
        self.atk     = atk
        self.defense = defense

    def is_alive(self):
        return self.hp > 0


class Player(Entity):
    def __init__(self, name):
        p = CFG["player"]
        super().__init__(name, p["hp"], p["atk"], p["defense"])
        self.xp      = 0
        self.level   = 1
        self.gold    = p["gold"]
        self.food    = p["food"]
        self.combo   = 0
        self.scars   = 0
        self.floor   = 1
        self.has_key = False

    def xp_to_next(self):
        return self.level * 40

    def try_level_up(self):
        while self.xp >= self.xp_to_next():
            self.xp     -= self.xp_to_next()
            self.level  += 1
            self.max_hp += 8
            self.hp      = min(self.hp + 8, self.max_hp)
            self.atk    += 2
            slow_print(f"\n  ✦ LEVEL UP! You are now level {self.level}.")
            slow_print(f"    Max HP +8 | ATK +2")

    def status(self):
        print(f"\n  {self.name}  |  Level {self.level}  |  Floor {self.floor}/{FLOOR_COUNT}")
        print(f"  HP  {bar(self.hp, self.max_hp)}")
        print(f"  XP  {bar(self.xp, self.xp_to_next())}")
        print(f"  ATK {self.atk}  DEF {self.defense}  GOLD {self.gold}  FOOD {self.food}")
        if self.scars:
            print(f"  Scars: {'⚔ '*self.scars}  (max HP reduced by {self.scars*5})")

    def eat(self):
        if self.food <= 0:
            slow_print("  You have no food left. Hunger gnaws at you (-2 HP).")
            self.hp -= 2
        else:
            self.food -= 1

# ─────────────────────────────────────────
#  COMBAT
# ─────────────────────────────────────────
def enemy_pick_action(ai_weights):
    actions = list(ai_weights.keys())
    weights = list(ai_weights.values())
    return random.choices(actions, weights)[0]

def resolve_combat(player, enemy, p_action, e_action):
    """Resolve one turn. Returns False if combat should end early (flee)."""
    p_def = player.defense * 2 if p_action == "defend" else player.defense
    e_def = enemy.defense  * 2 if e_action == "defend" else enemy.defense

    slow_print(f"  {enemy.name} prepares to {e_action.upper()}!")

    # ── player attacks enemy ──
    if p_action in ("attack", "heavy"):
        hit_threshold = 12 if p_action == "heavy" else 10
        if roll() + player.atk > hit_threshold:
            player.combo += 1
            atk_mult = 2 if p_action == "heavy" else 1
            dmg = max(1, player.atk * atk_mult + (player.combo - 1) - e_def)
            enemy.hp -= dmg
            label = "Heavy blow" if p_action == "heavy" else "You strike"
            slow_print(f"  {label}! {dmg} damage to {enemy.name}. (Combo x{player.combo})")
        else:
            player.combo = 0
            slow_print("  Your attack misses. Combo reset.")
    elif p_action == "defend":
        player.combo = 0
        slow_print("  You brace for impact.")

    # ── enemy attacks player ──
    if e_action in ("attack", "heavy"):
        hit_threshold = 12 if e_action == "heavy" else 10
        if roll() + enemy.atk > hit_threshold:
            atk_mult = 2 if e_action == "heavy" else 1
            dmg = max(1, enemy.atk * atk_mult - p_def)
            player.hp -= dmg
            label = f"{enemy.name} strikes heavily" if e_action == "heavy" else f"{enemy.name} attacks"
            slow_print(f"  {label} for {dmg} damage!")
        else:
            slow_print(f"  {enemy.name} misses!")
    elif e_action == "defend":
        slow_print(f"  {enemy.name} braces for impact.")

def combat(player, enemy_template, floor, scale_override=None, room_num=0):
    tier_scale  = ENEMIES.index(enemy_template) * 0.1 if enemy_template in ENEMIES else 0
    scale       = scale_override if scale_override is not None else max(1, 1 + (floor - 1) * 0.15 - tier_scale)
    ai_weights  = enemy_template["ai"]
    enemy       = Entity(
        name    = enemy_template["name"],
        hp      = int(enemy_template["hp"]      * scale),
        atk     = int(enemy_template["atk"]     * scale),
        defense = int(enemy_template["defense"] * scale),
    )
    enemy.xp   = enemy_template["xp"]
    enemy.gold = enemy_template["gold"]
    max_ehp    = enemy.hp

    slow_print(f"\n  A {enemy.name} appears! ({enemy.hp} HP | ATK {enemy.atk} | DEF {enemy.defense})")
    pause()

    player.combo = 0

    while enemy.hp > 0 and player.is_alive():
        clear()
        print(f"\n  ── COMBAT ── {player.name} vs {enemy.name} ──")
        print(f"  {'You':<6} {bar(player.hp, player.max_hp)}  ATK {player.atk}  DEF {player.defense}")
        print(f"  {'Foe':<6} {bar(enemy.hp, max_ehp)}  ATK {enemy.atk}  DEF {enemy.defense}")
        if player.combo > 1:
            print(f"  ⚡ Combo x{player.combo}!")
        print()
        print("  [1] Attack    [2] Heavy Strike (2x dmg, 60% hit)")
        print("  [3] Defend    [4] Flee (50% chance)")
        timer_cfg = CFG["game"]["turn_timer"]
        if timer_cfg["enabled"]:
            choice = timed_input("  > ", timer_cfg["seconds"])
        else:
            choice = input("  > ").strip()

        if choice not in ("1", "2", "3", "4"):
            slow_print("  Invalid input — you hesitate.")
            e_action = enemy_pick_action(ai_weights)
            slow_print(f"  {enemy.name} prepares to {e_action.upper()}!")
            if e_action in ("attack", "heavy"):
                hit_threshold = 12 if e_action == "heavy" else 10
                if roll() + enemy.atk > hit_threshold:
                    atk_mult = 2 if e_action == "heavy" else 1
                    dmg = max(1, enemy.atk * atk_mult - player.defense)
                    player.hp -= dmg
                    slow_print(f"  {enemy.name} strikes you for {dmg} while you stand frozen!")
                else:
                    slow_print(f"  {enemy.name} misses despite your hesitation!")
            elif e_action == "defend":
                slow_print(f"  {enemy.name} braces, waiting for you to act.")
            pause()
            continue

        # flee resolves immediately, no simultaneous action
        if choice == "4":
            if roll() > 10:
                slow_print("  You flee! But not before taking a parting blow...")
                dmg = max(1, enemy.atk - player.defense)
                player.hp -= dmg
                slow_print(f"  {enemy.name} hits you for {dmg} as you run.")
                player.combo = 0
                pause()
                return "fled"
            else:
                slow_print("  Escape blocked! The enemy seizes the opening!")
                dmg = max(1, enemy.atk - player.defense + 3)
                player.hp -= dmg
                slow_print(f"  {enemy.name} punishes you for {dmg} damage.")
                pause()
                continue

        p_action = {"1": "attack", "2": "heavy", "3": "defend"}[choice]
        e_action = enemy_pick_action(ai_weights)

        resolve_combat(player, enemy, p_action, e_action)

        if player.hp <= 4 and player.is_alive():
            slow_print("  ⚠  You're barely standing...")

        pause()

    if player.is_alive():
        gold = random.randint(*enemy.gold)
        player.xp   += enemy.xp
        player.gold += gold
        slow_print(f"\n  {enemy.name} defeated! +{enemy.xp} XP | +{gold} gold")
        if not player.has_key:
            drop_chance = 1.0 if room_num >= ROOMS_PER_FLOOR else CFG["game"]["key_drop_chance"]
            if random.random() < drop_chance:
                player.has_key = True
                slow_print("  🗝  A floor key drops from the body. You can now descend.")
        player.try_level_up()
        return "win"
    else:
        return "dead"

# ─────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────
def event_loot(player):
    item = random.choice(LOOT_TABLE)
    old  = getattr(player, item["stat"])
    setattr(player, item["stat"], old + item["bonus"])
    slow_print(f"  You find a {item['name']}! {item['stat'].upper()} +{item['bonus']} ({old} → {old+item['bonus']})")

def event_trap(player):
    dmg = random.randint(3, 10)
    player.hp -= dmg
    slow_print(f"  You trigger a trap! -{dmg} HP.")

def event_rest(player):
    heal  = random.randint(8, 18)
    food  = random.randint(1, 3)
    player.hp   = min(player.max_hp, player.hp + heal)
    player.food += food
    slow_print(f"  A quiet alcove. You rest. +{heal} HP | +{food} food.")

def event_merchant(player):
    shop = CFG["shop"]
    slow_print("  A hooded merchant grins at you.")
    print(f"  Your gold: {player.gold}")
    print()
    for i, item in enumerate(shop, 1):
        print(f"  [{i}] {item['label']}  ({item['cost']}g) — {item['desc']}")
    print(f"  [{len(shop)+1}] Leave")
    choice = input("  > ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(shop)):
        slow_print("  You walk away.")
        return
    item = shop[int(choice) - 1]
    if player.gold < item["cost"]:
        slow_print(f"  Not enough gold. You need {item['cost']}g.")
        return
    player.gold -= item["cost"]
    if item["stat"] == "hp":
        player.hp = min(player.max_hp, player.hp + item["bonus"])
    else:
        setattr(player, item["stat"], getattr(player, item["stat"]) + item["bonus"])
    slow_print(f"  {item['label']} acquired. {item['stat'].upper()} +{item['bonus']}. ({item['desc']})")

def event_shrine(player):
    slow_print("  You find an ancient shrine.")
    print("  [1] Pray (50% chance: +10 HP or -5 HP)")
    print("  [2] Ignore")
    if input("  > ").strip() == "1":
        if roll() > 10:
            player.hp = min(player.max_hp, player.hp + 10)
            slow_print("  The gods smile. +10 HP.")
        else:
            player.hp -= 5
            slow_print("  The gods are displeased. -5 HP.")

# ─────────────────────────────────────────
#  ROOM GENERATION
# ─────────────────────────────────────────
def get_enemy_for_floor(floor):
    # bias toward harder enemies on deeper floors
    max_idx = min((floor + 1) // 2, len(ENEMIES) - 1)
    idx     = random.randint(max(0, max_idx - 1), max_idx)
    return ENEMIES[idx]

def run_room(player, room_num):
    clear()
    flavor = random.choice(ROOM_FLAVORS)
    key_indicator = "  🗝  [KEY HELD]" if player.has_key else ""
    slow_print(f"\n  Room {room_num} — {flavor}{key_indicator}")
    pause("Enter room...")

    weights = CFG["room_weights"]
    event   = random.choices(list(weights.keys()), list(weights.values()))[0]

    player.eat()

    if event == "enemy":
        result = combat(player, get_enemy_for_floor(player.floor), player.floor, room_num=room_num)
        if result == "dead":
            penalty        = 5
            player.max_hp  = max(10, player.max_hp - penalty)
            player.hp      = player.max_hp // 2
            slow_print(f"\n  You fall... but drag yourself back up.")
            slow_print(f"  A scar remains. Max HP -{penalty}. You wake with {player.hp} HP.")
            player.scars  += 1
            if player.scars > 5:
                slow_print("  You are too broken to continue. The dungeon claims you.")
                return "dead"

    elif event == "loot":     event_loot(player)
    elif event == "rest":     event_rest(player)
    elif event == "trap":     event_trap(player)
    elif event == "merchant": event_merchant(player)
    elif event == "shrine":   event_shrine(player)

    player.status()

    if player.has_key:
        print("\n  🗝  You hold the floor key.")
        print("  [D] Descend to next floor   [S] Stay and explore")
        if input("  > ").strip().lower() == "d":
            save_game(player)
            return "descend"

    save_game(player)
    pause()
    return "alive"

# ─────────────────────────────────────────
#  BOSS
# ─────────────────────────────────────────
def run_boss(player):
    clear()
    slow_print("\n  ══════════════════════════════")
    slow_print("   THE BOSS AWAITS.")
    slow_print("  ══════════════════════════════")
    pause()
    result = combat(player, BOSS, player.floor, scale_override=1.0)
    return result == "win"

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def title_screen():
    clear()
    print("""
  ╔══════════════════════════════════════╗
  ║         D U N G E O N  R U N        ║
  ║    A text RPG with a feedback loop   ║
  ╚══════════════════════════════════════╝
    """)

def main():
    title_screen()

    if os.path.exists(SAVE_FILE):
        print("  A saved game was found.")
        print("  [C] Continue   [N] New Game")
        choice = input("  > ").strip().lower()
        if choice == "c":
            player = load_game()
            slow_print(f"\n  Welcome back, {player.name}. Floor {player.floor}.")
            pause()
        else:
            delete_save()
            name   = input("  Enter your name, adventurer: ").strip() or "Hero"
            player = Player(name)
            slow_print(f"\n  Welcome, {name}. Descend 10 floors. Survive.")
            pause()
    else:
        name   = input("  Enter your name, adventurer: ").strip() or "Hero"
        player = Player(name)
        slow_print(f"\n  Welcome, {name}. Descend 10 floors. Survive.")
        pause()

    for floor in range(player.floor, FLOOR_COUNT + 1):
        player.floor   = floor
        player.has_key = False
        clear()
        slow_print(f"\n  ── Floor {floor} of {FLOOR_COUNT} ──")
        slow_print("  Find the floor key to descend.")
        pause()

        room_num = 0
        while True:
            room_num += 1
            result = run_room(player, room_num)
            if result == "dead":
                slow_print("\n  GAME OVER. The dungeon is undefeated.")
                delete_save()
                return
            if result == "descend":
                break

        clear()
        slow_print(f"  Floor {floor} cleared! You descend deeper...")
        pause()

    # boss floor
    player.floor = FLOOR_COUNT
    won = run_boss(player)

    clear()
    if won:
        delete_save()
        slow_print("\n  ══════════════════════════════")
        slow_print("   YOU ESCAPED THE DUNGEON!")
        slow_print(f"   Floors cleared: {FLOOR_COUNT}")
        slow_print(f"   Level reached:  {player.level}")
        slow_print(f"   Scars earned:   {player.scars}")
        slow_print(f"   Gold carried:   {player.gold}")
        slow_print("  ══════════════════════════════")
    else:
        delete_save()
        slow_print("\n  The Dungeon Tyrant laughs as darkness falls.")
        slow_print("  GAME OVER.")

if __name__ == "__main__":
    main()