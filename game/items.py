"""Gear: every looted item has a slot, a rarity and real effects that are explained in plain words.

An item is a plain dict: name, slot ('weapon'|'armor'|'charm'), tier (0 Common .. 3 Legendary), desc, cursed, plus effect keys:
  atk (x damage)  hp (x max HP)  dmg_taken (x damage taken)  cd_mult (x skill cooldowns)  speed (x walk speed)
  lifesteal (fraction of damage dealt healed)  crit (chance for a double-damage hit)  thorns (damage reflected to melee attackers)
  block_window (extra seconds of "perfect block" timing).
Effects from the three slots stack (multipliers multiply, the rest add). Player.recompute() folds them into the player's stats."""
import random
from .config import RARITY

SLOTS = ("weapon", "armor", "charm")
SLOT_NAMES = dict(weapon="Weapon", armor="Armor", charm="Charm")
MULT_KEYS = ("atk", "hp", "dmg_taken", "cd_mult", "speed")  # multiplicative effects (default 1.0)
ADD_KEYS = ("lifesteal", "crit", "thorns", "block_window")  # additive effects (default 0)

BASES = dict(
    weapon=["Sword", "Axe", "Mace", "Spear", "Blade", "Hammer"],
    armor=["Vest", "Helm", "Boots", "Cloak", "Gauntlets", "Mail"],
    charm=["Ring", "Amulet", "Charm", "Talisman", "Locket"],
)
ADJ = [["Rusty", "Dull", "Worn"], ["Sturdy", "Keen", "Polished"], ["Runed", "Gleaming", "Blessed"], ["Mythic", "Dragonforged", "Celestial"]]
SUFFIX = {"dice": "of Fortune", "lock": "of the Steady Hand", "slash": "of Swift Cuts", "parry": "of the Perfect Parry", "boss": "of the Fallen King"}

# main effect strength per tier
ATK = [1.06, 1.12, 1.20, 1.32]
HP = [1.08, 1.15, 1.25, 1.40]
TAKEN = [0.98, 0.94, 0.90, 0.84]
CD = [0.95, 0.90, 0.85, 0.78]
PERKS = dict(  # perk: per-tier value (only from Rare up; Epic+ may roll a second one)
    crit=[0, 0.08, 0.12, 0.20], lifesteal=[0, 0.04, 0.06, 0.10], thorns=[0, 4, 7, 12], speed=[1, 1.06, 1.10, 1.16], block_window=[0, 0.05, 0.08, 0.12])
SLOT_PERKS = dict(weapon=["crit", "lifesteal"], armor=["thorns", "speed"], charm=["lifesteal", "speed", "block_window", "crit"])
LEGENDARY = {  # boss-only flavour names for a legendary roll
    "weapon": ["Kingslayer", "Dawnedge", "Grave-Cleaver"], "armor": ["Aegis of Ages", "Bulwark of the Fallen"], "charm": ["Heart of the Castle", "Crown Shard"]}


def pct(x, base=1.0):
    return int(round((x - base) * 100))


def describe(it):
    """One short line listing the item's real effects, e.g. '+12% ATK, 8% crit'. Used by popups, the gear screen and tests."""
    out = []
    if it.get("atk", 1.0) != 1.0: out.append(f"{pct(it['atk']):+d}% ATK")
    if it.get("hp", 1.0) != 1.0: out.append(f"{pct(it['hp']):+d}% HP")
    if it.get("dmg_taken", 1.0) != 1.0: out.append(f"{pct(it['dmg_taken']):+d}% dmg taken")
    if it.get("cd_mult", 1.0) != 1.0: out.append(f"{pct(it['cd_mult']):+d}% skill cooldown")
    if it.get("speed", 1.0) != 1.0: out.append(f"{pct(it['speed']):+d}% speed")
    if it.get("lifesteal"): out.append(f"heal {int(round(it['lifesteal'] * 100))}% of damage dealt")
    if it.get("crit"): out.append(f"{int(round(it['crit'] * 100))}% crit (x2)")
    if it.get("thorns"): out.append(f"reflect {int(it['thorns'])} dmg to attackers")
    if it.get("block_window"): out.append(f"+{int(round(it['block_window'] * 1000))}ms perfect-block window")
    if it.get("curse"): out.append("CURSE: " + it["curse"])
    return ", ".join(out) or "no effect"


def power(it):
    """Single number used to decide whether a new item beats the equipped one (higher is better)."""
    if not it: return -1.0
    return ((it.get("atk", 1.0) - 1) * 100 + (it.get("hp", 1.0) - 1) * 60 + (1 - it.get("dmg_taken", 1.0)) * 100 + (1 - it.get("cd_mult", 1.0)) * 60
            + (it.get("speed", 1.0) - 1) * 80 + it.get("lifesteal", 0) * 200 + it.get("crit", 0) * 100 + it.get("thorns", 0) * 2 + it.get("block_window", 0) * 100)


def mods(items):
    """Fold equipped items (any iterable, None allowed) into one stats dict."""
    m = dict(atk=1.0, hp=1.0, dmg_taken=1.0, cd_mult=1.0, speed=1.0, lifesteal=0.0, crit=0.0, thorns=0.0, block_window=0.0)
    for it in items:
        if not it: continue
        for k in MULT_KEYS: m[k] *= it.get(k, 1.0)
        for k in ADD_KEYS: m[k] += it.get(k, 0.0)
    return m


def roll_item(score, rng=random, boss=False, slot=None, min_tier=0, max_tier=2):
    """Roll one item. The mini-game `score` (0..1) pushes the rarity up. Normal loot tops out at Epic; Legendary is boss-only."""
    r = score * 0.75 + rng.random() * 0.35
    tier = 0 if r < 0.35 else 1 if r < 0.6 else 2 if r < 0.85 else 3
    tier = max(min_tier, min(3 if boss else max_tier, tier))
    slot = slot or rng.choice(SLOTS)
    it = dict(slot=slot, tier=tier, cursed=False)
    if slot == "weapon": it["atk"] = ATK[tier]
    elif slot == "armor": it["hp"], it["dmg_taken"] = HP[tier], TAKEN[tier]
    else: it["cd_mult"] = CD[tier]
    if tier >= 1:
        perks = list(SLOT_PERKS[slot])
        for _ in range(2 if tier >= 2 else 1):
            if not perks: break
            k = perks.pop(rng.randrange(len(perks)))
            v = PERKS[k][tier]
            it[k] = it.get(k, 1.0) * v if k == "speed" else v
    base = rng.choice(BASES[slot])
    it["name"] = f"{rng.choice(LEGENDARY[slot])}" if tier == 3 else f"{rng.choice(ADJ[tier])} {base}" + (f" {rng.choice(list(SUFFIX.values()))}" if tier else "")
    it["desc"] = describe(it)
    return it


def tier_color(it):
    return (190, 100, 240) if it.get("cursed") else RARITY[it.get("tier", 0)][1]


def tier_name(it):
    return "Cursed" if it.get("cursed") else RARITY[it.get("tier", 0)][0]
