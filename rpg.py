import random
import os
import time
import json

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

# ─────────────────────────────────────────
#  PLAYER
# ─────────────────────────────────────────
class Player:
    def __init__(self, name):
        p = CFG["player"]
        self.name   = name
        self.hp     = p["hp"]
        self.max_hp = p["hp"]
        self.atk    = p["atk"]
        self.defense= p["defense"]
        self.xp     = 0
        self.level  = 1
        self.gold   = p["gold"]
        self.food   = p["food"]
        self.combo  = 0          # momentum system
        self.scars  = 0          # scar system: each "death" reduces max_hp
        self.floor  = 1

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

    def is_alive(self):
        return self.hp > 0

    def eat(self):
        if self.food <= 0:
            slow_print("  You have no food left. Hunger gnaws at you (-2 HP).")
            self.hp -= 2
        else:
            self.food -= 1

# ─────────────────────────────────────────
#  COMBAT
# ─────────────────────────────────────────
def combat(player, enemy_template, floor, scale_override=None):
    tier_scale = ENEMIES.index(enemy_template) * 0.1 if enemy_template in ENEMIES else 0
    scale      = scale_override if scale_override is not None else max(1, 1 + (floor - 1) * 0.15 - tier_scale)
    enemy      = {
        "name": enemy_template["name"],
        "hp":   int(enemy_template["hp"]  * scale),
        "atk":  int(enemy_template["atk"] * scale),
        "xp":   enemy_template["xp"],
        "gold": enemy_template["gold"],
    }
    max_ehp = enemy["hp"]

    slow_print(f"\n  A {enemy['name']} appears! ({enemy['hp']} HP | ATK {enemy['atk']})")
    pause()

    player.combo = 0

    while enemy["hp"] > 0 and player.is_alive():
        clear()
        print(f"\n  ── COMBAT ── {player.name} vs {enemy['name']} ──")
        print(f"  You  {bar(player.hp, player.max_hp)}")
        print(f"  Foe  {bar(enemy['hp'], max_ehp)}")
        if player.combo > 1:
            print(f"  ⚡ Combo x{player.combo}!")
        print()
        print("  [1] Attack    [2] Heavy Strike (2x dmg, 60% hit)")
        print("  [3] Defend    [4] Flee (50% chance)")
        choice = input("  > ").strip()

        if choice == "1":
            hit = roll() + player.atk > 10
            if hit:
                player.combo += 1
                dmg = max(1, player.atk + (player.combo - 1) - player.defense // 2)
                enemy["hp"] -= dmg
                slow_print(f"  You strike! {dmg} damage. (Combo x{player.combo})")
            else:
                player.combo = 0
                slow_print("  Your attack misses. Combo reset.")

        elif choice == "2":
            if roll() <= 12:   # 60% hit (1-12 on d20)
                player.combo += 1
                dmg = max(1, player.atk * 2 + (player.combo - 1) - player.defense // 2)
                enemy["hp"] -= dmg
                slow_print(f"  Heavy blow! {dmg} damage. (Combo x{player.combo})")
            else:
                player.combo = 0
                slow_print("  You overswing and miss. Combo reset.")

        elif choice == "3":
            player.combo = 0
            slow_print("  You brace for impact. Defense doubled this turn. Combo reset.")
            guard = player.defense * 2
            dmg   = max(0, enemy["atk"] - guard)
            player.hp -= dmg
            slow_print(f"  {enemy['name']} hits for {dmg} (blocked most of it).")
            pause()
            continue  # skip enemy normal attack below

        elif choice == "4":
            if roll() > 10:
                slow_print("  You flee successfully!")
                player.combo = 0
                return "fled"
            else:
                slow_print("  Escape blocked!")
        else:
            slow_print("  Invalid input — you hesitate.")

        # enemy attacks
        if enemy["hp"] > 0:
            dmg = max(0, enemy["atk"] - player.defense + random.randint(-2, 2))
            player.hp -= dmg
            slow_print(f"  {enemy['name']} retaliates for {dmg} damage.")

        if player.hp <= 4 and player.is_alive():
            slow_print("  ⚠  You're barely standing...")

        pause()

    if player.is_alive():
        gold = random.randint(*enemy["gold"])
        player.xp   += enemy["xp"]
        player.gold += gold
        slow_print(f"\n  {enemy['name']} defeated! +{enemy['xp']} XP | +{gold} gold")
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

def run_room(player, room=None):
    clear()
    flavor = random.choice(ROOM_FLAVORS)
    slow_print(f"\n  Room {room} — {flavor}")
    pause("Enter room...")

    # weighted room type
    weights = CFG["room_weights"]
    event   = random.choices(list(weights.keys()), list(weights.values()))[0]

    player.eat()   # food consumption each room

    if event == "enemy":
        result = combat(player, get_enemy_for_floor(player.floor), player.floor)
        if result == "dead":
            # scar system: don't die, but get scarred and lose max HP
            penalty        = 5
            player.max_hp  = max(10, player.max_hp - penalty)
            player.hp      = player.max_hp // 2
            slow_print(f"\n  You fall... but drag yourself back up.")
            slow_print(f"  A scar remains. Max HP -{penalty}. You wake with {player.hp} HP.")
            player.scars  += 1
            if player.scars > 5:
                slow_print("  You are too broken to continue. The dungeon claims you.")
                return False

    elif event == "loot":     event_loot(player)
    elif event == "rest":     event_rest(player)
    elif event == "trap":     event_trap(player)
    elif event == "merchant": event_merchant(player)
    elif event == "shrine":   event_shrine(player)

    player.status()
    pause()
    return True

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
    name   = input("  Enter your name, adventurer: ").strip() or "Hero"
    player = Player(name)
    slow_print(f"\n  Welcome, {name}. Descend 10 floors. Survive.")
    pause()

    for floor in range(1, FLOOR_COUNT + 1):
        player.floor = floor
        clear()
        slow_print(f"\n  ── Floor {floor} of {FLOOR_COUNT} ──")
        pause()

        for room in range(ROOMS_PER_FLOOR):
            alive = run_room(player, room + 1)
            if not alive:
                slow_print("\n  GAME OVER. The dungeon is undefeated.")
                return

        # floor cleared
        clear()
        slow_print(f"  Floor {floor} cleared!")
        if floor < FLOOR_COUNT:
            slow_print("  You descend deeper...")
        pause()

    # boss floor
    player.floor = FLOOR_COUNT
    won = run_boss(player)

    clear()
    if won:
        slow_print("\n  ══════════════════════════════")
        slow_print("   YOU ESCAPED THE DUNGEON!")
        slow_print(f"   Floors cleared: {FLOOR_COUNT}")
        slow_print(f"   Level reached:  {player.level}")
        slow_print(f"   Scars earned:   {player.scars}")
        slow_print(f"   Gold carried:   {player.gold}")
        slow_print("  ══════════════════════════════")
    else:
        slow_print("\n  The Dungeon Tyrant laughs as darkness falls.")
        slow_print("  GAME OVER.")

if __name__ == "__main__":
    main()