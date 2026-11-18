"""Constants, palette, settings / key binds and difficulty rules."""
import json, os
import pygame

W, H, FLOOR, PW = 480, 270, 222, 160

INK, WHITE, GOLD = (20, 16, 30), (240, 240, 245), (240, 200, 70)
STEEL, STEEL_D, RED, RED_D, BLUE = (168, 178, 198), (110, 120, 150), (200, 56, 64), (130, 34, 48), (60, 92, 176)
BROWN, BROWN_D, GREEN, GREY = (120, 76, 50), (84, 52, 36), (90, 200, 110), (80, 76, 96)
SKIN, BONE, CYAN, BLADE = (224, 172, 130), (222, 214, 190), (90, 230, 240), (225, 230, 245)
P_COL = [(110, 200, 255), (255, 170, 90)]
RARITY = [("Common", (180, 180, 190)), ("Rare", (80, 150, 240)), ("Epic", (190, 100, 240)), ("Legendary", (250, 170, 40))]


# ================================================================ settings / key binds
SAVE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rogue_settings.json")
ACTIONS = ["left", "right", "jump", "down", "dash", "slash", "block", "cast", "cast2", "interact", "gear"]
LABEL = dict(
    left="Move left", right="Move right", jump="Jump / double / wall jump", down="Drop / fast-fall",
    dash="Dash (ground & air)", slash="Slash (attack)", block="Block (hold)",
    cast="Cast Skill 1", cast2="Cast Skill 2", interact="Loot / open chest (hold)", gear="Gear screen"
)
DEFAULT_KEYS = [
    dict(left=pygame.K_a, right=pygame.K_d, jump=pygame.K_w, down=pygame.K_s, dash=pygame.K_LSHIFT,
         slash=pygame.K_j, block=pygame.K_k, cast=pygame.K_l, cast2=pygame.K_u, interact=pygame.K_e, gear=pygame.K_i),
    dict(left=pygame.K_LEFT, right=pygame.K_RIGHT, jump=pygame.K_UP, down=pygame.K_DOWN, dash=pygame.K_RSHIFT,
         slash=pygame.K_COMMA, block=pygame.K_PERIOD, cast=pygame.K_SLASH, cast2=pygame.K_m, interact=pygame.K_RETURN, gear=pygame.K_o)
]


def load_settings():
    d = {"keys": [dict(k) for k in DEFAULT_KEYS], "tutorial_done": False, "solo": False}
    try:
        with open(SAVE) as f:
            s = json.load(f)
    except Exception:
        return d
    if not isinstance(s, dict):
        return d
    d["solo"] = s.get("solo") is True  # last chosen player count (True = 1 player + CPU ally)
    d["tutorial_done"] = s.get("tutorial_done") is True  # independent of key data so a partial file still counts
    try:
        for p in range(2):
            for a in ACTIONS:
                v = s["keys"][p].get(a)
                if isinstance(v, int):
                    d["keys"][p][a] = v
    except Exception:
        pass
    return d


SET = load_settings()


def save_settings():
    try:
        with open(SAVE, "w") as f:
            json.dump(SET, f)
    except Exception:
        pass


def kn(p, a):
    return pygame.key.name(SET["keys"][p][a]).upper()


# ================================================================ difficulty / dev flags
DMG_TAKEN_STEP, DMG_DEAL_STEP = 0.75, 1.25  # per level: enemies take 25% less damage, deal 25% more (compounding)
ALIEN_NAME = "Elon Musk"  # display name of the alien tycoon boss - change here to rename everywhere
DEV = False  # set by main.py (--dev / ROGUE_DEV=1); never saved to settings


def difficulty(level):
    """(damage enemies TAKE multiplier, damage enemies DEAL multiplier) for a 0-based level / tier."""
    level = max(0, int(level))
    return DMG_TAKEN_STEP ** level, DMG_DEAL_STEP ** level
