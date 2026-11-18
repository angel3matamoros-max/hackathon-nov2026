"""
ROGUE LOOT v4 - 2-player co-op pixel-art action game.
Install:  pip install pygame-ce        Run:  python rogue_loot_v4.py

Menu: Start / Tutorial / Settings (rebind keys) / Exit. First launch plays the tutorial.
Menus: W/S or Up/Down, Enter or Space to select, Esc to go back.
Default keys (all rebindable in Settings, saved to rogue_settings.json):
  P1: A/D move, W jump (x2 / wall-jump), S drop / fast-fall, LShift dash, J slash, K block (hold), L skill 1, U skill 2, E loot (hold)
  P2: Left/Right move, Up jump (x2 / wall-jump), Down drop / fast-fall, RShift dash, , slash, . block (hold), / skill 1, M skill 2, Enter loot (hold)

Controller plan: each player has a Motion object - subclass it for the GY-521 and fill the same fields.
"""
import json, math, os, random, sys
import pygame

W, H, FLOOR, PW = 480, 270, 222, 160
pygame.init()
try:
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    FAST = True
except Exception:
    screen = pygame.display.set_mode((W * 3, H * 3))
    FAST = False
pygame.display.set_caption("Rogue Loot")
main_cv = pygame.Surface((W, H))
world = pygame.Surface((W, H))
canvas = main_cv
clock = pygame.time.Clock()
font, mid, big = pygame.font.Font(None, 17), pygame.font.Font(None, 23), pygame.font.Font(None, 34)

INK, WHITE, GOLD = (20, 16, 30), (240, 240, 245), (240, 200, 70)
STEEL, STEEL_D, RED, RED_D, BLUE = (168, 178, 198), (110, 120, 150), (200, 56, 64), (130, 34, 48), (60, 92, 176)
BROWN, BROWN_D, GREEN, GREY = (120, 76, 50), (84, 52, 36), (90, 200, 110), (80, 76, 96)
SKIN, BONE, CYAN, BLADE = (224, 172, 130), (222, 214, 190), (90, 230, 240), (225, 230, 245)
P_COL = [(110, 200, 255), (255, 170, 90)]
RARITY = [("Common", (180, 180, 190)), ("Rare", (80, 150, 240)), ("Epic", (190, 100, 240)), ("Legendary", (250, 170, 40))]


# ================================================================ settings / key binds
SAVE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rogue_settings.json")
ACTIONS = ["left", "right", "jump", "down", "dash", "slash", "block", "cast", "cast2", "interact"]
LABEL = dict(
    left="Move left", right="Move right", jump="Jump / double / wall jump", down="Drop / fast-fall",
    dash="Dash (ground & air)", slash="Slash (attack)", block="Block (hold)",
    cast="Cast Skill 1", cast2="Cast Skill 2", interact="Loot corpse (hold)"
)
DEFAULT_KEYS = [
    dict(left=pygame.K_a, right=pygame.K_d, jump=pygame.K_w, down=pygame.K_s, dash=pygame.K_LSHIFT,
         slash=pygame.K_j, block=pygame.K_k, cast=pygame.K_l, cast2=pygame.K_u, interact=pygame.K_e),
    dict(left=pygame.K_LEFT, right=pygame.K_RIGHT, jump=pygame.K_UP, down=pygame.K_DOWN, dash=pygame.K_RSHIFT,
         slash=pygame.K_COMMA, block=pygame.K_PERIOD, cast=pygame.K_SLASH, cast2=pygame.K_m, interact=pygame.K_RETURN)
]


def load_settings():
    d = {"keys": [dict(k) for k in DEFAULT_KEYS], "tutorial_done": False}
    try:
        with open(SAVE) as f:
            s = json.load(f)
        for p in range(2):
            for a in ACTIONS:
                v = s["keys"][p].get(a)
                if isinstance(v, int):
                    d["keys"][p][a] = v
        d["tutorial_done"] = bool(s.get("tutorial_done"))
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


# ================================================================ drawing helpers
def use(surf):
    global canvas
    canvas = surf


def lerp(a, b, t):
    return tuple(int(x + (y - x) * max(0, min(1, t))) for x, y in zip(a, b))


def lit(c): return tuple(min(255, int(v * 1.25) + 12) for v in c)
def dim(c): return tuple(int(v * 0.68) for v in c)


def box(s, c, x, y, w, h):
    pygame.draw.rect(s, c, (x, y, w, h))
    if h >= 3 and w >= 2:
        pygame.draw.rect(s, lit(c), (x, y, w, 1))
        pygame.draw.rect(s, dim(c), (x, y + h - 1, w, 1))


def outlined(s):
    sil = pygame.mask.from_surface(s).to_surface(setcolor=INK + (255,), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((s.get_width() + 2, s.get_height() + 2), pygame.SRCALPHA)
    for d in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(sil, d)
    out.blit(s, (1, 1))
    return out


def text(s, x, y, color=WHITE, f=font, center=False, right=False):
    img, sh = f.render(s, False, color), f.render(s, False, INK)
    x -= img.get_width() // 2 if center else (img.get_width() if right else 0)
    canvas.blit(sh, (x + 1, y + 1))
    canvas.blit(img, (x, y))


def title_text(s, cx, y, color, scale=3):
    img, sh = mid.render(s, False, color), mid.render(s, False, INK)
    sz = (img.get_width() * scale, img.get_height() * scale)
    canvas.blit(pygame.transform.scale(sh, sz), (cx - sz[0] // 2 + scale, y + scale))
    canvas.blit(pygame.transform.scale(img, sz), (cx - sz[0] // 2, y))


def wrap(s, n=26):
    lines, cur = [], ""
    for w in s.split():
        if cur and len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + [cur]


def bar(x, y, w, h, frac, color):
    pygame.draw.rect(canvas, INK, (x - 1, y - 1, w + 2, h + 2))
    pygame.draw.rect(canvas, GREY, (x, y, w, h))
    pygame.draw.rect(canvas, color, (x, y, int(w * max(0, min(1, frac))), h))


def gem(x, y, color, r=7):
    pts = [(x, y - r), (x + r - 1, y), (x, y + r), (x - r + 1, y)]
    pygame.draw.polygon(canvas, color, pts)
    pygame.draw.polygon(canvas, lit(color), [pts[0], pts[1], (x, y)])
    pygame.draw.polygon(canvas, INK, pts, 1)


GLOWS = {}


def glow(x, y, r, color):
    key = (r, color)
    if key not in GLOWS:
        g = pygame.Surface((2 * r, 2 * r))
        for k in range(r, 0, -2):
            pygame.draw.circle(g, tuple(int(v * (1 - k / r) ** 2) for v in color), (r, r), k)
        GLOWS[key] = g
    canvas.blit(GLOWS[key], (int(x - r), int(y - r)), special_flags=pygame.BLEND_RGB_ADD)


def blit_ent(fr, x, y, flip=False, tint=None):
    if flip:
        fr = pygame.transform.flip(fr, True, False)
    if tint:
        fr = fr.copy()
        fr.fill(tint + (0,), special_flags=pygame.BLEND_RGB_ADD)
    canvas.blit(fr, (int(x - fr.get_width() / 2), int(y - fr.get_height() + 1)))


# ================================================================ classes (stats, 2 skills, clear descriptions)
CLASSES = {
    "Knight": dict(
        spec=None, bonus=.08, hp=8, atk=6, df=7, cd=6, cd2=10,
        role="Vanguard / Support",
        skill="Holy Charge",
        sdesc="Dash forward slashing foes. Invulnerable while charging.",
        skill2="Aegis Banner",
        s2desc="Plant a radiant banner: heals nearby allies (+25 HP) and knocks back foes.",
        pdesc="Passive: +8% score in every loot mini-game."
    ),
    "Tank": dict(
        spec="parry", bonus=.15, hp=10, atk=4, df=10, cd=8, cd2=9,
        role="Juggernaut / Crowd Control",
        skill="Earthquake Slam",
        sdesc="Smash the ground: heavy AoE damage and STUNS nearby foes for 1.5s.",
        skill2="Iron Taunt",
        s2desc="Roar to pull enemies toward you and gain a 30 HP barrier for 4s.",
        pdesc="Passive: +15% score in the Parry mini-game."
    ),
    "Fighter": dict(
        spec="slash", bonus=.15, hp=7, atk=9, df=4, cd=7, cd2=5,
        role="Relentless Bruiser",
        skill="Whirlwind",
        sdesc="Spin for 0.7s, rapidly slicing everything around you while moving.",
        skill2="Blade Wave",
        s2desc="Launch a piercing crescent wave that cuts through every enemy in a line.",
        pdesc="Passive: +15% score in the Slash mini-game."
    ),
    "Mage": dict(
        spec="dice", bonus=.15, hp=4, atk=10, df=2, cd=5, cd2=8,
        role="Arcane Artillery",
        skill="Fireball",
        sdesc="Hurl an explosive firebolt that detonates on impact for huge AoE damage.",
        skill2="Frost Nova",
        s2desc="Blast an icy ring around you: damages and FREEZES nearby foes for 2.0s.",
        pdesc="Passive: +15% score in the Dice Roll mini-game."
    ),
    "Rogue": dict(
        spec="lock", bonus=.15, hp=5, atk=8, df=3, cd=6, cd2=5,
        role="Mobile Assassin",
        skill="Shadow Step",
        sdesc="Blink behind the nearest enemy and deliver a 2.4x backstab.",
        skill2="Fan of Knives",
        s2desc="Leap back slightly and throw 3 fast daggers in a wide spread.",
        pdesc="Passive: +15% score in the Lock Pick mini-game."
    ),
}
CLASS_NAMES = list(CLASSES)


def bonus_for(cls, kind):
    d = CLASSES[cls]
    return d["bonus"] if d["spec"] in (None, kind) else 0.0


# ================================================================ sprites
def hero_frame(cls, i=None, n=8):
    s = pygame.Surface((28, 28), pygame.SRCALPHA)
    ph = 0 if i is None else i / n * 2 * math.pi
    sw, cs = (0, 0) if i is None else (math.sin(ph), math.cos(ph))
    bob = 1 if (i is not None and i % 4 == 2) else 0
    lx, ax = round(sw * 4), round(-sw * 3)
    lb, lf = int(cs < -0.5), int(cs > 0.5)

    def B(c, x, y, w, h):
        box(s, c, x, y, w, h)

    def leg(x, lift, col):
        top, bot = 20 + bob, 28 - lift
        B(col, x, top, 4, bot - top)
        B(BROWN_D, x, bot - 3, 6, 3)

    if cls == "Mage":
        B(BROWN_D, 6 - lx, 26 - lb, 5, 2)
        B(BROWN_D, 13 + lx, 26 - lf, 5, 2)
    else:
        col = {"Knight": STEEL_D, "Tank": (70, 78, 100), "Fighter": (120, 90, 60), "Rogue": (40, 70, 50)}[cls]
        leg(7 - lx, lb, col)
        leg(13 + lx, lf, col)

    if cls == "Knight":
        B(RED_D, 4 - abs(lx) // 2, 12 + bob, 4, 13)
        B(BLUE, 3, 13 + bob, 5, 9); B(GOLD, 3, 13 + bob, 5, 1); B(GOLD, 5, 16 + bob, 1, 3)
        B(STEEL, 7, 11 + bob, 11, 10); B(RED, 11, 11 + bob, 3, 10); B(GOLD, 7, 19 + bob, 11, 2)
        B(STEEL, 8, 3 + bob, 9, 8); B(INK, 12, 6 + bob, 5, 2); B(STEEL_D, 8, 9 + bob, 9, 2)
        B(RED, 11, 0 + bob, 3, 3); B(RED, 9, 2 + bob, 3, 2)
        B(STEEL_D, 16 + ax, 13 + bob, 3, 6)
        B(BLADE, 19 + ax, 5 + bob, 2, 14); B(GOLD, 17 + ax, 18 + bob, 6, 2); B(BROWN, 19 + ax, 20 + bob, 2, 3)
    elif cls == "Tank":
        dk, org = (70, 78, 100), (220, 120, 40)
        B((150, 90, 50), 2, 12 + bob, 7, 14); B(GOLD, 4, 17 + bob, 3, 4)
        B(dk, 6, 11 + bob, 13, 10); B(org, 6, 19 + bob, 13, 2); B(org, 11, 11 + bob, 3, 7)
        B(dk, 8, 3 + bob, 10, 8); B(INK, 13, 6 + bob, 5, 2)
        B(BONE, 6, 1 + bob, 2, 6); B(BONE, 18, 1 + bob, 2, 6)
        B(dk, 17 + ax, 13 + bob, 3, 6)
        B(BROWN, 20 + ax, 7 + bob, 2, 17); B(STEEL, 18 + ax, 3 + bob, 7, 6)
    elif cls == "Fighter":
        B(SKIN, 5 - ax, 13 + bob, 3, 6)
        B((130, 90, 60), 7, 11 + bob, 11, 10); B(BROWN_D, 9, 11 + bob, 2, 9); B((200, 160, 60), 7, 19 + bob, 11, 2)
        B(SKIN, 9, 4 + bob, 8, 7); B((100, 60, 30), 9, 2 + bob, 8, 3); B((100, 60, 30), 8, 4 + bob, 2, 5)
        B(RED, 9, 6 + bob, 8, 1); B(RED, 6, 6 + bob, 3, 2); B(INK, 14, 8 + bob, 1, 1)
        B(SKIN, 16 + ax, 13 + bob, 3, 6)
        B(BROWN, 19 + ax, 5 + bob, 2, 17); B(STEEL, 20 + ax, 5 + bob, 5, 8); B(WHITE, 24 + ax, 5 + bob, 1, 8)
    elif cls == "Mage":
        robe = (110, 70, 170)
        B(robe, 7, 11 + bob, 12, 15); B(GOLD, 7, 24, 12, 2); B(GOLD, 7, 18 + bob, 12, 2)
        B(SKIN, 10, 6 + bob, 8, 5); B(INK, 14, 8 + bob, 1, 1); B(WHITE, 11, 11 + bob, 6, 3)
        B(dim(robe), 6, 5 + bob, 14, 2); B(robe, 9, 2 + bob, 8, 3); B(robe, 11, 0 + bob, 4, 2); B(GOLD, 9, 4 + bob, 8, 1)
        B(robe, 16 + ax, 13 + bob, 3, 6)
        B(BROWN, 20 + ax, 7 + bob, 2, 20); B(CYAN, 18 + ax, 2 + bob, 6, 6); B(WHITE, 20 + ax, 4 + bob, 2, 2)
    else:
        grn, grd = (50, 120, 70), (34, 80, 50)
        B(grd, 4 - abs(lx) // 2, 12 + bob, 5, 13)
        B(grd, 8, 11 + bob, 10, 10); B(BROWN, 8, 19 + bob, 10, 2); B(BROWN_D, 10, 11 + bob, 2, 9)
        B(grn, 8, 3 + bob, 10, 8); B(grn, 7, 5 + bob, 2, 6); B(SKIN, 13, 6 + bob, 5, 4); B(INK, 15, 7 + bob, 1, 1)
        B(grd, 16 + ax, 13 + bob, 3, 6)
        B(BLADE, 19 + ax, 11 + bob, 2, 8); B(GOLD, 18 + ax, 19 + bob, 4, 1); B(BROWN, 19 + ax, 20 + bob, 2, 3)
    return outlined(s)


def skeleton_frame(i):
    s = pygame.Surface((26, 28), pygame.SRCALPHA)
    sw = math.sin(i / 4 * 2 * math.pi)
    bob, lx, ax = i % 2, round(sw * 3), round(-sw * 2)
    for x in (8 - lx, 14 + lx):
        box(s, BONE, x, 20 + bob, 3, 8 - bob); box(s, dim(BONE), x, 25, 5, 3)
    box(s, BONE, 8, 11 + bob, 9, 9)
    for y in (13, 15, 17):
        pygame.draw.rect(s, INK, (9, y + bob, 7, 1))
    box(s, dim(BONE), 12, 10 + bob, 2, 10)
    box(s, BONE, 8, 2 + bob, 10, 9); box(s, dim(BONE), 9, 10 + bob, 8, 2)
    box(s, INK, 10, 5 + bob, 3, 3); box(s, INK, 14, 5 + bob, 3, 3)
    pygame.draw.rect(s, RED, (11, 6 + bob, 1, 1)); pygame.draw.rect(s, RED, (15, 6 + bob, 1, 1))
    box(s, BONE, 17 + ax, 12 + bob, 2, 7)
    box(s, (150, 130, 110), 19 + ax, 6 + bob, 2, 13); box(s, BROWN, 18 + ax, 18 + bob, 4, 2)
    return outlined(s)


def slime_frame(i, col):
    s = pygame.Surface((24, 14), pygame.SRCALPHA)
    h, w = (12, 18) if i == 0 else (9, 22)
    pygame.draw.ellipse(s, col, (12 - w // 2, 14 - h, w, h))
    pygame.draw.ellipse(s, lit(col), (15 - w // 2, 16 - h, 6, 3))
    pygame.draw.rect(s, INK, (8, 18 - h, 2, 3)); pygame.draw.rect(s, INK, (14, 18 - h, 2, 3))
    return outlined(s)


def bat_frame(i):
    s = pygame.Surface((28, 18), pygame.SRCALPHA)
    wy, pu = (1 if i == 0 else 11), (100, 64, 140)
    pygame.draw.polygon(s, pu, [(14, 9), (1, wy), (6, 8), (8, 13)])
    pygame.draw.polygon(s, pu, [(14, 9), (27, wy), (22, 8), (20, 13)])
    pygame.draw.ellipse(s, (64, 42, 94), (9, 5, 10, 11))
    box(s, (64, 42, 94), 10, 3, 2, 3); box(s, (64, 42, 94), 16, 3, 2, 3)
    pygame.draw.rect(s, RED, (11, 8, 2, 2)); pygame.draw.rect(s, RED, (15, 8, 2, 2)); pygame.draw.rect(s, WHITE, (12, 13, 1, 2))
    return outlined(s)


def brute_frame(i):
    s = pygame.Surface((36, 38), pygame.SRCALPHA)
    sw = math.sin(i / 4 * 2 * math.pi)
    bob, lx, ax = i % 2, round(sw * 4), round(-sw * 3)
    g, gd = (96, 128, 72), (62, 88, 50)
    for x in (8 - lx, 20 + lx):
        box(s, gd, x, 28 + bob, 7, 10 - bob); box(s, BROWN_D, x, 35, 9, 3)
    box(s, g, 7, 12 + bob, 22, 17); box(s, BROWN, 7, 25 + bob, 22, 3)
    box(s, g, 12, 3 + bob, 13, 11); box(s, gd, 12, 5 + bob, 13, 2)
    pygame.draw.rect(s, RED, (19, 8 + bob, 3, 2)); box(s, BONE, 14, 12 + bob, 2, 3); box(s, BONE, 22, 12 + bob, 2, 3)
    box(s, gd, 25 + ax, 14 + bob, 5, 10)
    box(s, BROWN, 29 + ax, 4 + bob, 3, 24); box(s, (90, 70, 60), 27 + ax, 2 + bob, 7, 9)
    return outlined(s)


def dummy_frame():
    s = pygame.Surface((20, 32), pygame.SRCALPHA)
    box(s, BROWN, 9, 10, 3, 20); box(s, BROWN, 3, 12, 15, 3); box(s, BROWN_D, 4, 28, 13, 4)
    box(s, (210, 180, 100), 6, 14, 9, 9); box(s, (200, 170, 110), 6, 2, 9, 9); pygame.draw.rect(s, RED, (8, 5, 2, 2)); pygame.draw.rect(s, RED, (12, 5, 2, 2))
    return outlined(s)


SLIME_COL = [(110, 200, 120), (150, 220, 70), (240, 110, 50), (110, 200, 255), (80, 220, 210), (210, 120, 250)]
HERO = {c: (hero_frame(c), [hero_frame(c, i) for i in range(8)]) for c in CLASSES}
ENEMY = {("skeleton", 0): [skeleton_frame(i) for i in range(4)], ("brute", 0): [brute_frame(i) for i in range(4)],
         ("bat", 0): [bat_frame(i) for i in range(2)], ("dummy", 0): [dummy_frame()]}
for _a, _c in enumerate(SLIME_COL):
    ENEMY[("slime", _a)] = [slime_frame(i, _c) for i in range(2)]
CORPSE = {k: pygame.transform.rotate(v[0], 90) for k, v in ENEMY.items()}

MIMIC = pygame.Surface((16, 14), pygame.SRCALPHA)
box(MIMIC, BROWN, 0, 6, 16, 8); box(MIMIC, BROWN, 0, 0, 16, 4); pygame.draw.rect(MIMIC, INK, (1, 4, 14, 3))
for _x in (2, 6, 10):
    pygame.draw.rect(MIMIC, WHITE, (_x, 4, 2, 3))
pygame.draw.rect(MIMIC, RED, (3, 1, 2, 2)); pygame.draw.rect(MIMIC, RED, (11, 1, 2, 2))
MIMIC = outlined(MIMIC)


# ================================================================ 6 areas / rich pixel-art backgrounds
AREAS = [
    dict(name="Crypt Dungeon", sky=((18, 14, 30), (44, 34, 64)), floor=(60, 50, 76), top=(96, 82, 116), plat=(84, 70, 104),
         plats=[(70, 176, 96), (310, 170, 96), (190, 128, 100)], kinds=[("skeleton", 3), ("slime", 2)]),
    dict(name="Mossy Forest", sky=((8, 22, 38), (30, 74, 74)), floor=(50, 80, 46), top=(92, 150, 70), plat=(96, 72, 48),
         plats=[(50, 172, 90), (330, 172, 90), (190, 134, 100)], kinds=[("slime", 3), ("bat", 2), ("skeleton", 2)]),
    dict(name="Sunken Ruin", sky=((6, 24, 48), (18, 76, 98)), floor=(36, 68, 82), top=(74, 148, 152), plat=(54, 102, 114),
         plats=[(40, 176, 86), (354, 176, 86), (150, 142, 74), (256, 142, 74)], kinds=[("slime", 3), ("skeleton", 2), ("bat", 2)]),
    dict(name="Ember Caverns", sky=((26, 8, 12), (92, 30, 20)), floor=(84, 46, 42), top=(140, 76, 54), plat=(110, 60, 50),
         plats=[(110, 170, 90), (280, 150, 90), (30, 140, 70)], kinds=[("skeleton", 2), ("bat", 3), ("brute", 1)]),
    dict(name="Frost Keep", sky=((14, 28, 56), (80, 120, 160)), floor=(112, 142, 172), top=(196, 224, 244), plat=(150, 190, 220),
         plats=[(60, 170, 100), (320, 170, 100), (190, 130, 100)], kinds=[("skeleton", 2), ("bat", 2), ("brute", 2), ("slime", 1)]),
    dict(name="Astral Citadel", sky=((10, 6, 26), (48, 22, 82)), floor=(46, 36, 76), top=(130, 100, 210), plat=(74, 56, 124),
         plats=[(48, 174, 84), (348, 174, 84), (130, 132, 76), (274, 132, 76), (200, 94, 80)],
         kinds=[("skeleton", 2), ("bat", 3), ("brute", 2), ("slime", 2)]),
]
AMB_N = [18, 20, 24, 26, 44, 34]
BGS = {}


def make_bg(i):
    A, rnd, sf = AREAS[i], random.Random(i + 10), pygame.Surface((W, H))
    for y in range(H):
        pygame.draw.line(sf, lerp(A["sky"][0], A["sky"][1], y / FLOOR), (0, y), (W, y))
    if i == 0:  # Crypt Dungeon
        for row in range(0, FLOOR, 16):
            for x in range(-(row // 16 % 2) * 20, W, 40):
                pygame.draw.rect(sf, lerp((40, 32, 60), (58, 46, 82), rnd.random()), (x, row, 39, 15))
                pygame.draw.rect(sf, (74, 62, 100), (x, row, 39, 1))
        for x in (36, 200, 364):
            pygame.draw.rect(sf, (12, 8, 20), (x, 96, 64, FLOOR - 96)); pygame.draw.circle(sf, (12, 8, 20), (x + 32, 96), 32)
            pygame.draw.rect(sf, (96, 80, 124), (x - 4, 92, 72, 4)); pygame.draw.circle(sf, (96, 80, 124), (x + 32, 96), 36, 4)
            # tattered royal banners
            pygame.draw.polygon(sf, RED_D, [(x + 22, 104), (x + 42, 104), (x + 42, 148), (x + 32, 140), (x + 22, 148)])
            pygame.draw.rect(sf, GOLD, (x + 22, 104, 20, 2))
        for x in (130, 300, 440):
            pygame.draw.line(sf, (96, 96, 116), (x, 0), (x, rnd.randint(50, 90)), 2)
    elif i == 1:  # Mossy Forest
        pygame.draw.circle(sf, (60, 110, 100), (380, 48), 34); pygame.draw.circle(sf, (232, 236, 200), (380, 48), 22)
        for _ in range(45):
            pygame.draw.rect(sf, (200, 220, 220), (rnd.randint(0, W), rnd.randint(0, 110), 1, 1))
        for col, base, hh, stp in (((22, 54, 58), 176, 70, 30), ((14, 40, 46), 196, 90, 36), ((8, 28, 34), 216, 110, 44)):
            for x in range(-10, W + 20, stp):
                h = rnd.randint(hh - 18, hh + 18)
                pygame.draw.rect(sf, col, (x - 2, base, 4, FLOOR - base))
                pygame.draw.polygon(sf, col, [(x - 18, base), (x, base - h), (x + 18, base)])
                pygame.draw.polygon(sf, lit(col), [(x - 14, base - h // 3), (x, base - h - 8), (x + 14, base - h // 3)])
    elif i == 2:  # Sunken Ruin
        # water light shafts
        shaft = pygame.Surface((W, FLOOR), pygame.SRCALPHA)
        for sx in (60, 190, 340):
            pygame.draw.polygon(shaft, (120, 220, 230, 22), [(sx, 0), (sx + 44, 0), (sx + 94, FLOOR), (sx + 30, FLOOR)])
        sf.blit(shaft, (0, 0))
        # sunken Greek-style broken columns
        for cx, h in ((78, 120), (235, 86), (402, 134)):
            pygame.draw.rect(sf, (44, 84, 96), (cx, FLOOR - h, 22, h))
            pygame.draw.rect(sf, (66, 116, 126), (cx + 3, FLOOR - h, 4, h))
            pygame.draw.rect(sf, (66, 116, 126), (cx - 4, FLOOR - 8, 30, 8))
            pygame.draw.polygon(sf, (44, 84, 96), [(cx - 4, FLOOR - h), (cx + 26, FLOOR - h), (cx + 18, FLOOR - h - 10), (cx + 2, FLOOR - h - 6)])
        # seaweed & coral silhouettes
        for kx in range(14, W, 28):
            kh = rnd.randint(18, 46)
            for y in range(0, kh, 4):
                ox = int(math.sin(y * 0.25 + kx) * 3)
                pygame.draw.rect(sf, (24, 112, 92), (kx + ox, FLOOR - y - 4, 3, 4))
    elif i == 3:  # Ember Caverns
        for x in range(-20, W + 20, 38):
            pygame.draw.polygon(sf, (54, 20, 22), [(x, 0), (x + 36, 0), (x + 18, rnd.randint(30, 90))])
        for x in range(0, W, 60):
            pygame.draw.polygon(sf, (64, 26, 28), [(x, 176), (x + 30, 176 - rnd.randint(30, 70)), (x + 60, 176)])
        for y in range(176, FLOOR):
            pygame.draw.line(sf, lerp((255, 200, 60), (200, 50, 20), (y - 176) / 46), (0, y), (W, y))
    elif i == 4:  # Frost Keep
        for x in range(-30, W + 30, 90):
            h = rnd.randint(70, 120)
            pygame.draw.polygon(sf, (110, 150, 190), [(x, 190), (x + 45, 190 - h), (x + 90, 190)])
            pygame.draw.polygon(sf, (232, 244, 255), [(x + 33, 190 - h + 22), (x + 45, 190 - h), (x + 57, 190 - h + 22)])
        for x in (60, 220, 400):
            pygame.draw.rect(sf, (140, 184, 220), (x, 90, 18, FLOOR - 90)); pygame.draw.rect(sf, (210, 236, 250), (x + 3, 90, 3, FLOOR - 90))
        for x in range(0, W, 22):
            pygame.draw.polygon(sf, (190, 226, 246), [(x, 0), (x + 20, 0), (x + 10, rnd.randint(14, 44))])
    else:  # Astral Citadel
        for _ in range(70):
            c = rnd.choice([(255, 255, 255), (180, 210, 255), (255, 210, 160)])
            pygame.draw.rect(sf, c, (rnd.randint(0, W), rnd.randint(0, 160), rnd.choice((1, 1, 2)), 1))
        # ringed cosmic planet
        pygame.draw.circle(sf, (92, 54, 150), (110, 56), 24)
        pygame.draw.circle(sf, (132, 82, 200), (105, 51), 16)
        pygame.draw.ellipse(sf, (210, 170, 255), (72, 48, 76, 16), 2)
        # floating crystal obelisks
        for ox, oy, oh in ((64, 140, 46), (240, 126, 54), (416, 142, 44)):
            pygame.draw.polygon(sf, (64, 44, 110), [(ox, oy - oh // 2), (ox + 12, oy), (ox, oy + oh // 2), (ox - 12, oy)])
            pygame.draw.polygon(sf, (150, 110, 230), [(ox, oy - oh // 2), (ox + 12, oy), (ox, oy)])

    # Floor & platforms with surface detail
    pygame.draw.rect(sf, A["floor"], (0, FLOOR, W, H - FLOOR))
    pygame.draw.rect(sf, A["top"], (0, FLOOR, W, 3)); pygame.draw.rect(sf, dim(A["top"]), (0, FLOOR + 3, W, 1))
    for x in range(0, W, 24):
        pygame.draw.rect(sf, dim(A["floor"]), (x, FLOOR + 8 + (x // 24 % 3) * 9, 22, 1))
        pygame.draw.rect(sf, dim(A["floor"]), (x + 11, FLOOR + 4, 1, 30))
        if i in (1, 2):  # grass / kelp tufts
            pygame.draw.rect(sf, lit(A["top"]), (x + 4, FLOOR - 2, 2, 2))
            pygame.draw.rect(sf, A["top"], (x + 15, FLOOR - 1, 3, 1))
    for px, py, pw in A["plats"]:
        box(sf, A["plat"], px, py, pw, 9); pygame.draw.rect(sf, A["top"], (px, py, pw, 2))
        pygame.draw.rect(sf, dim(A["plat"]), (px + 4, py + 9, pw - 8, 3))
        if i == 4:  # icicles under frost platforms
            for ix in range(px + 6, px + pw - 6, 14):
                pygame.draw.polygon(sf, (210, 240, 255), [(ix, py + 9), (ix + 5, py + 9), (ix + 2, py + 15)])
    # subtle wall trim to show wall-jumpable arena borders
    for wx in (0, W - 4):
        pygame.draw.rect(sf, dim(A["plat"]), (wx, 24, 4, FLOOR - 24))
    return sf


def get_bg(i):
    if i not in BGS:
        BGS[i] = make_bg(i)
    return BGS[i]


def draw_torches(t):
    for x, y in ((70, 118), (240, 118), (410, 118)):
        pygame.draw.rect(canvas, BROWN, (x - 1, y, 3, 12)); fl = int(t * 9 + x) % 3
        pygame.draw.rect(canvas, (240, 120, 40), (x - 3, y - 8 - fl, 7, 9 + fl)); pygame.draw.rect(canvas, GOLD, (x - 1, y - 5 - fl, 3, 6 + fl))
        glow(x, y - 4, 56, (130, 76, 24))


def draw_runes(t):
    for x, y in ((120, 110), (360, 110)):
        r = 6 + int(math.sin(t * 3 + x) * 2)
        pygame.draw.circle(canvas, (170, 120, 255), (x, y), r, 1)
        glow(x, y, 36, (80, 40, 130))


def make_vignette():
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    for k in range(24):
        pygame.draw.rect(v, (0, 0, 0, int(90 * (1 - k / 24) ** 2)), (k, k, W - 2 * k, H - 2 * k), 1)
    return v


VIGNETTE, DIM = make_vignette(), pygame.Surface((W, H), pygame.SRCALPHA)
DIM.fill((0, 0, 0, 150))


# ================================================================ input
class Motion:
    """One per player. Keyboard now; for the GY-521 make a subclass that fills these fields:
       axis -1/0/1 (walk) | jump_h, down_h, block_h, interact_h (held)
       jump_p, down_p, dash_p, slash_p, cast_p, cast2_p (one frame)
       tilt -1..1, shake 0..1, swing 'left'/'right'/'up'/'down', flick (used by loot mini-games)."""

    def __init__(s, i):
        s.i, s.axis, s.tilt, s.shake = i, 0, 0.0, 0.0
        s.jump_h = s.down_h = s.block_h = s.interact_h = False
        s.reset()

    def reset(s):
        s.jump_p = s.down_p = s.dash_p = s.slash_p = s.cast_p = s.cast2_p = s.flick = False
        s.swing = None

    def update(s, events, dt):
        k, p = SET["keys"][s.i], pygame.key.get_pressed()
        s.axis = int(p[k["right"]]) - int(p[k["left"]])
        s.tilt += (s.axis - s.tilt) * min(1, dt * 8)
        s.jump_h = bool(p[k["jump"]])
        s.down_h = bool(p[k["down"]])
        s.block_h = bool(p[k["block"]])
        s.interact_h = bool(p[k["interact"]])
        s.reset()
        for e in events:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == k["jump"]: s.jump_p, s.swing = True, "up"
            if e.key == k["down"]: s.down_p, s.swing = True, "down"
            if e.key == k["left"]: s.swing = "left"
            if e.key == k["right"]: s.swing = "right"
            if e.key == k["dash"]: s.dash_p = True
            if e.key == k["slash"]:
                s.slash_p = s.flick = True
                s.shake = min(1, s.shake + 0.15)
            if e.key == k["cast"]: s.cast_p = True
            if e.key == k["cast2"]: s.cast2_p = True
        s.shake = max(0, s.shake - dt * 0.7)


# ================================================================ loot mini-games (160x180 panel)
class Mini:
    over, score, t, bonus, hero = False, 0.0, 0.0, 0.0, "Knight"
    kind = title = hint = ""

    def finish(s, score):
        s.over, s.score = True, max(0, min(1, score * (1 + s.bonus)))

    def bg(s):
        canvas.fill((24, 18, 36))
        pygame.draw.rect(canvas, (70, 60, 100), (2, 2, PW - 4, 176), 1)
        text(s.title, PW // 2, 8, GOLD, mid, True)


PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (2, 0), (0, 2), (2, 2)],
        5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)], 6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]}


class DiceShake(Mini):
    kind, title, hint = "dice", "DICE ROLL", "Shake hard! Bigger shake = better loot."

    def ctrl(s, p): return f"Mash [{kn(p, 'slash')}] as fast as you can!"

    def __init__(s): s.acc, s.face, s.sh = 0.0, 1, 0.0

    def update(s, dt, m):
        s.t += dt
        if s.over: return
        s.sh = m.shake
        s.acc = min(1, s.acc + m.shake * dt * 0.4)
        if random.random() < dt * 18: s.face = random.randint(1, 6)
        if s.t >= 4:
            s.face, s.sh = 1 + round(s.acc * 5), 0
            s.finish(s.acc)

    def draw(s):
        s.bg()
        j = int(s.sh * 4)
        cx, cy = 80 + random.randint(-j, j), 62 + random.randint(-j, j)
        pygame.draw.rect(canvas, INK, (cx - 22, cy - 22, 44, 44)); pygame.draw.rect(canvas, WHITE, (cx - 20, cy - 20, 40, 40))
        pygame.draw.rect(canvas, (200, 200, 215), (cx - 20, cy + 16, 40, 4))
        for gx, gy in PIPS[s.face]:
            pygame.draw.rect(canvas, INK, (cx + (gx - 1) * 11 - 3, cy + (gy - 1) * 11 - 3, 6, 6))
        text("SHAKE POWER", 80, 100, WHITE, font, True)
        bar(30, 113, 100, 8, s.acc, GOLD); bar(30, 130, 100, 3, 1 - s.t / 4, STEEL_D)


class LockPick(Mini):
    kind, title, hint = "lock", "LOCK PICK", "Find the sweet spot and hold steady!"

    def ctrl(s, p): return f"Hold [{kn(p, 'left')}] / [{kn(p, 'right')}] to tilt the pick"

    def __init__(s): s.target, s.pick, s.hold, s.err = random.uniform(-60, 60), 0.0, 0.0, 90

    def update(s, dt, m):
        if s.over: return
        s.t += dt
        s.pick = max(-90, min(90, s.pick + m.tilt * dt * 80))
        s.err = abs(s.pick - s.target)
        if s.err < 8: s.hold += dt
        if s.hold >= 2: s.finish(max(0.35, 1 - s.t / 12))
        elif s.t >= 12: s.finish(min(0.3, s.hold / 2 * 0.3))

    def draw(s):
        s.bg()
        col, cx, cy = lerp(BLUE, GOLD, max(0, 1 - s.err / 60)), 80, 66
        pygame.draw.circle(canvas, INK, (cx, cy), 36); pygame.draw.circle(canvas, col, (cx, cy), 34)
        pygame.draw.circle(canvas, INK, (cx, cy), 27); pygame.draw.circle(canvas, (50, 42, 70), (cx, cy), 25)
        pygame.draw.rect(canvas, INK, (cx - 2, cy, 4, 9))
        a = math.radians(s.pick)
        pygame.draw.line(canvas, STEEL, (cx, cy), (cx + math.sin(a) * 26, cy - math.cos(a) * 26), 2)
        pygame.draw.circle(canvas, INK, (cx, cy), 5)
        text("UNLOCKING", 80, 106, WHITE, font, True)
        bar(30, 118, 100, 6, s.hold / 2, GREEN); bar(30, 132, 100, 3, 1 - s.t / 12, STEEL_D)


class SlashLoot(Mini):
    kind, title, hint = "slash", "SLASH THE LOOT", "Swing the way the arrow points!"
    N = 8
    ARROW = [(-12, -5), (2, -5), (2, -11), (14, 0), (2, 11), (2, 5), (-12, 5)]
    ROT = {"right": lambda x, y: (x, y), "left": lambda x, y: (-x, y), "down": lambda x, y: (-y, x), "up": lambda x, y: (y, -x)}

    def ctrl(s, p): return f"Press [{kn(p, 'left')}] [{kn(p, 'right')}] [{kn(p, 'jump')}] [{kn(p, 'down')}]"

    def __init__(s):
        s.res, s.tt, s.win, s.flash, s.msg = [], 0.0, 1.1, 0.0, ""
        s.cur = random.choice(list(s.ROT))

    def step(s, ok):
        s.res.append(ok)
        s.flash, s.msg = 0.35, "HIT!" if ok else "MISS"
        if len(s.res) >= s.N: s.finish(sum(s.res) / s.N)
        s.cur, s.tt, s.win = random.choice(list(s.ROT)), 0.0, max(0.65, 1.1 - 0.05 * len(s.res))

    def update(s, dt, m):
        if s.over: return
        s.tt += dt
        s.flash = max(0, s.flash - dt)
        if m.swing: s.step(m.swing == s.cur)
        elif s.tt > s.win: s.step(False)

    def draw(s):
        s.bg()
        cx, cy = 80, 64
        if not s.over:
            pygame.draw.circle(canvas, STEEL_D, (cx, cy), 8 + int(36 * (1 - s.tt / s.win)), 1)
            f = s.ROT[s.cur]
            pts = [(cx + f(x, y)[0], cy + f(x, y)[1]) for x, y in s.ARROW]
            pygame.draw.polygon(canvas, INK, pts, 3); pygame.draw.polygon(canvas, GOLD, pts)
        if s.flash: text(s.msg, cx, 116, GREEN if s.msg == "HIT!" else RED, mid, True)
        for i in range(s.N):
            c = GREY if i >= len(s.res) else (GREEN if s.res[i] else RED)
            pygame.draw.rect(canvas, INK, (15 + i * 16, 138, 11, 11)); pygame.draw.rect(canvas, c, (16 + i * 16, 139, 9, 9))


class Parry(Mini):
    kind, title, hint = "parry", "PARRY THE MIMIC", "Strike when it hits the green zone!"
    ZC, HALF, ROUNDS = 98, 12, 3

    def ctrl(s, p): return f"Press [{kn(p, 'slash')}] in the green zone"

    def __init__(s): s.r, s.res, s.mx, s.pause, s.msg = 0, [], 200.0, 0.0, ""

    def resolve(s, q):
        s.res.append(q); s.r += 1
        s.pause, s.msg = 0.8, "PARRY!" if q > 0 else "OUCH!"
        if q > 0: s.mx = s.ZC + 40

    def update(s, dt, m):
        if s.over: return
        if s.pause > 0:
            s.pause -= dt
            if s.pause <= 0:
                if s.r >= s.ROUNDS: s.finish(sum(s.res) / s.ROUNDS)
                else: s.mx, s.msg = 200.0, ""
            return
        s.mx -= (100 + 30 * s.r) * dt
        d = abs(s.mx - s.ZC)
        if m.flick: s.resolve(1 - d / s.HALF if d <= s.HALF else 0)
        elif s.mx < 76: s.resolve(0)

    def draw(s):
        s.bg()
        pygame.draw.rect(canvas, (62, 50, 74), (4, 112, PW - 8, 38))
        pygame.draw.rect(canvas, (40, 110, 60), (s.ZC - s.HALF, 80, 2 * s.HALF, 32)); pygame.draw.rect(canvas, GREEN, (s.ZC - s.HALF, 80, 2 * s.HALF, 32), 1)
        canvas.blit(pygame.transform.scale(HERO[s.hero][0], (60, 60)), (8, 54))
        canvas.blit(pygame.transform.scale(MIMIC, (36, 32)), (int(s.mx) - 18, 80))
        text(f"ROUND {min(s.r + 1, s.ROUNDS)}/{s.ROUNDS}", 80, 30, WHITE, font, True)
        if s.msg: text(s.msg, 80, 44, GREEN if s.msg == "PARRY!" else RED, mid, True)


MINIS = [DiceShake, LockPick, SlashLoot, Parry]
ITEMS = ["Sword", "Shield", "Helm", "Boots", "Ring", "Amulet", "Potion"]
ADJ = [["Rusty", "Dull", "Worn"], ["Sturdy", "Polished", "Keen"], ["Gleaming", "Runed", "Cursed"], ["Mythic", "Dragonforged", "Celestial"]]
SUFFIX = {"dice": "of Fortune", "lock": "of the Steady Hand", "slash": "of Swift Cuts", "parry": "of the Perfect Parry"}


def roll_loot(kind, score):
    r = score * 0.75 + random.random() * 0.35
    tier = 0 if r < 0.35 else 1 if r < 0.6 else 2 if r < 0.85 else 3
    name = f"{random.choice(ADJ[tier])} {random.choice(ITEMS)}" + (" " + SUFFIX[kind] if tier else "")
    return {"name": name, "tier": tier}


# ================================================================ combat entities
def land(o, a):
    o.ground = False
    if o.vy >= 0:
        for px, py, pw in a.plats:
            if (py == FLOOR or o.drop <= 0) and o.py <= py + 0.5 and o.y >= py and px - 4 <= o.x <= px + pw + 4:
                o.y, o.vy, o.ground = float(py), 0.0, True
                return True
    return False


def overlap(x0, x1, y0, y1, e):
    return x0 < e.x + e.d["w"] / 2 and x1 > e.x - e.d["w"] / 2 and y0 < e.y and y1 > e.y - e.d["h"]


class Player:
    def __init__(s, i, cls, x):
        d = CLASSES[cls]
        s.i, s.cls, s.x, s.y, s.py, s.vx, s.vy = i, cls, float(x), float(FLOOR), float(FLOOR), 0.0, 0.0
        s.maxhp = s.hp = d["hp"] * 12 + 12
        s.shield = s.shield_t = 0.0
        s.atk = 8 + d["atk"] * 2
        s.face, s.jumps, s.ground, s.down = 1, 0, True, False
        s.skill, s.block, s.block_t, s.anim = None, False, 9.0, 0.0
        s.slash_t = s.slash_cd = s.cast_cd = s.cast2_cd = 0.0
        s.dash_t = s.dash_cd = s.inv = s.stun = s.drop = s.flash = s.skill_t = s.tick = s.kb = 0.0
        s.coyote = s.jbuf = 0.0
        s.wall = 0  # -1 left wall, +1 right wall, 0 none
        s.hitset = set()
        s.travel = 0.0
        s.djumps = s.dashes = s.blocks = s.perfects = s.casts = s.casts2 = 0

    def update(s, dt, m, a):
        if s.down: return
        for n in ("slash_cd", "cast_cd", "cast2_cd", "dash_cd", "inv", "stun", "drop", "flash", "coyote", "jbuf", "shield_t"):
            setattr(s, n, max(0.0, getattr(s, n) - dt))
        if s.shield_t <= 0:
            s.shield = 0.0
        free = s.stun <= 0 and s.skill != "charge"
        ax = m.axis if free else 0
        was = s.block
        s.block = bool(m.block_h) and free and s.dash_t <= 0 and s.slash_t <= 0
        s.block_t = (s.block_t + dt) if (s.block and was) else (0.0 if s.block else 9.0)

        # smoother acceleration + responsive air control
        max_spd = 128 * (0.38 if s.block else 1.0)
        accel = 1350 if s.ground else 920
        if ax:
            s.face = ax
            s.anim += dt * (11 if not s.block else 4)
            s.travel += abs(s.vx) * dt
            target_vx = ax * max_spd
            if s.vx < target_vx: s.vx = min(target_vx, s.vx + accel * dt)
            elif s.vx > target_vx: s.vx = max(target_vx, s.vx - accel * dt)
        else:
            s.anim = 0.0
            fric = 1400 if s.ground else 420
            if s.vx > 0: s.vx = max(0.0, s.vx - fric * dt)
            elif s.vx < 0: s.vx = min(0.0, s.vx + fric * dt)

        if m.jump_p:
            s.jbuf = 0.12

        if free:
            # jump / coyote jump / wall jump / double jump
            if s.jbuf > 0:
                if s.ground or s.coyote > 0:
                    s.vy, s.ground, s.coyote, s.jbuf, s.jumps = -345, False, 0.0, 0.0, 1
                    a.burst(s.x, s.y, WHITE, 5, 45)
                elif s.wall != 0 and not s.ground:
                    s.vy = -335
                    s.vx = -s.wall * 195
                    s.face = -s.wall
                    s.jbuf, s.jumps = 0.0, 1
                    a.burst(s.x + s.wall * 6, s.y - 12, WHITE, 7, 65)
                elif s.jumps < 2:
                    s.vy, s.ground, s.jbuf = -305, False, 0.0
                    s.jumps = 2
                    s.djumps += 1
                    a.burst(s.x, s.y, WHITE, 8, 70)
            # variable jump cut when releasing jump early
            if not m.jump_h and s.vy < -130:
                s.vy *= 0.65
            # drop through platform or fast-fall in air
            if m.down_p:
                s.drop = 0.25
            if m.down_h and not s.ground and s.vy > 0:
                s.vy = min(560, s.vy + 750 * dt)
            if m.dash_p and s.dash_cd <= 0:
                s.dash_t, s.dash_cd, s.inv, s.dashes = 0.18, 0.72, max(s.inv, 0.24), s.dashes + 1
                if not s.ground:
                    s.vy = min(s.vy, 0.0)
            if m.slash_p and s.slash_cd <= 0 and not s.block:
                s.slash_t, s.slash_cd, s.hitset = 0.16, 0.34, set()
            if m.cast_p and s.cast_cd <= 0 and s.skill is None:
                a.cast(s)
            if m.cast2_p and s.cast2_cd <= 0 and s.skill is None:
                a.cast2(s)

        if s.dash_t > 0:
            s.dash_t -= dt
            s.vx = s.face * 355
            if random.random() < 0.7:
                a.burst(s.x, s.y - 12, (200, 220, 255), 1, 20)
        if s.slash_t > 0:
            s.slash_t -= dt
            s.vx += s.face * 28
            a.slash_hit(s)
        if s.skill:
            s.skill_t -= dt
            if s.skill == "charge":
                s.vx = s.face * 350
                a.slash_hit(s, 30, s.atk * 1.35)
                a.burst(s.x, s.y - 12, GOLD, 1, 30)
            else:
                s.tick -= dt
                if s.tick <= 0:
                    s.tick = 0.16
                    a.hit_radius(s.x, s.y - 14, 38, s.atk * 0.75, 130)
            if s.skill_t <= 0:
                s.skill = None

        s.vx += s.kb
        s.kb *= max(0.0, 1 - dt * 8)

        # wall detection & wall-slide friction
        s.wall = -1 if s.x <= 11 else (1 if s.x >= W - 11 else 0)
        grav = 1000
        if not s.ground and s.wall != 0 and ax == s.wall and s.vy > 0:
            grav = 260
            s.vy = min(s.vy, 95)
            if random.random() < 0.35:
                a.burst(s.x + s.wall * 6, s.y - 10, STEEL, 1, 15)

        s.vy = min(540, s.vy + grav * dt)
        s.x = max(10, min(W - 10, s.x + s.vx * dt))
        s.py = s.y
        s.y += s.vy * dt
        was_ground = s.ground
        if land(s, a):
            if not was_ground:
                a.burst(s.x, s.y, STEEL_D, 4, 35)
            s.jumps, s.coyote = 0, 0.10
        elif was_ground and s.vy >= 0:
            s.coyote = 0.10

    def take(s, dmg, sx, a, src):
        if s.down or s.inv > 0: return
        if s.block and (sx - s.x) * s.face >= 0:
            s.blocks += 1
            if s.block_t < 0.2:
                s.perfects += 1; src.stun, src.state, src.st = 1.4, "rest", 0.4
                a.texts.append([s.x, s.y - 46, "PERFECT BLOCK!", GOLD, 1.0]); a.burst(s.x + s.face * 12, s.y - 16, GOLD, 12, 120); a.shake = 4
                return
            dmg *= 0.2; s.kb = -s.face * 60
            a.texts.append([s.x, s.y - 42, "BLOCKED", CYAN, 0.6])
        else:
            s.kb, s.stun = (1 if s.x >= sx else -1) * 120, 0.22
        dmg = int(round(dmg * (1 - CLASSES[s.cls]["df"] * 0.04)))
        s.inv, s.flash = 0.5, 0.15
        if dmg > 0 and s.shield > 0:
            absorbed = min(s.shield, dmg)
            s.shield -= absorbed
            dmg -= int(absorbed)
            a.texts.append([s.x, s.y - 48, "SHIELDED", CYAN, 0.6])
        if dmg > 0:
            s.hp -= dmg
            a.texts.append([s.x, s.y - 40, f"-{dmg}", (255, 90, 90), 0.8]); a.burst(s.x, s.y - 16, RED, 6, 90); a.shake = 3
        if s.hp <= 0:
            s.hp, s.down = 0, True
            a.burst(s.x, s.y - 14, P_COL[s.i], 22, 130); a.texts.append([s.x, s.y - 40, "DOWN!", RED, 1.5])


ESTATS = {
    "skeleton": dict(hp=40, dmg=10, spd=38, rng=24, wind=.55, w=12, h=28), "slime": dict(hp=28, dmg=8, spd=34, rng=18, wind=.45, w=16, h=12),
    "bat": dict(hp=18, dmg=7, spd=75, rng=18, wind=.35, w=16, h=14), "brute": dict(hp=110, dmg=18, spd=26, rng=34, wind=.8, w=26, h=36),
    "dummy": dict(hp=9999, dmg=0, spd=0, rng=0, wind=9, w=14, h=30)}


class Enemy:
    def __init__(s, kind, x, y, tint, dscale=1.0, hp=None):
        s.kind, s.d, s.tint, s.dscale = kind, ESTATS[kind], tint, dscale
        s.x, s.y, s.py, s.vy, s.drop, s.ground = float(x), float(y), float(y), 0.0, 0.0, False
        s.hp = s.maxhp = hp or s.d["hp"]
        s.face, s.state, s.st, s.flash, s.stun, s.frozen, s.kb, s.anim, s.hop = -1, "walk", 0.0, 0.0, 0.0, 0.0, 0.0, random.random() * 3, 0.0

    def update(s, dt, a):
        d = s.d
        s.flash = max(0, s.flash - dt)
        s.stun = max(0, s.stun - dt)
        s.frozen = max(0, s.frozen - dt)
        if s.frozen <= 0:
            s.anim += dt
        s.x = max(8, min(W - 8, s.x + s.kb * dt)); s.kb *= max(0, 1 - dt * 7)
        if s.kind == "dummy": return
        t = a.nearest(s.x)
        if t is None: return
        dx = t.x - s.x
        if s.stun <= 0 and s.frozen <= 0:
            if s.state == "walk":
                s.face = 1 if dx > 0 else -1
                if abs(dx) <= d["rng"] and abs(t.y - s.y) < (40 if s.kind == "bat" else 30): s.state, s.st = "wind", d["wind"]
                elif s.kind != "slime" or not s.ground: s.x += s.face * d["spd"] * dt
            elif s.state == "wind":
                s.st -= dt
                if s.st <= 0:
                    s.state, s.st = "rest", 0.55
                    if abs(t.x - s.x) <= d["rng"] + 12 and abs(t.y - s.y) < 40 and (t.x - s.x) * s.face >= 0:
                        t.take(d["dmg"] * s.dscale, s.x, a, s)
            else:
                s.st -= dt
                if s.st <= 0: s.state = "walk"
        if s.kind == "bat":
            if s.frozen <= 0:
                s.y += (t.y - 22 + math.sin(s.anim * 3) * 8 - s.y) * min(1, dt * 2.5)
        else:
            if s.ground and s.stun <= 0 and s.frozen <= 0 and s.state == "walk":
                if s.kind == "slime":
                    s.hop -= dt
                    if s.hop <= 0: s.vy, s.hop = -190, random.uniform(0.7, 1.3)
                elif t.y < s.y - 30 and abs(dx) < 50 and random.random() < dt * 2: s.vy = -330
            s.vy = min(520, s.vy + 1000 * dt); s.py = s.y; s.y += s.vy * dt
            land(s, a)


# ================================================================ arena (gameplay scene + tutorial)
class Arena:
    def __init__(s, area, players, tut=False):
        s.area, s.A, s.players, s.tut = area, AREAS[area], players, tut
        s.plats = [(0, FLOOR, W)] + s.A["plats"]
        s.enemies, s.corpses, s.projs, s.parts, s.texts = [], [], [], [], []
        s.queue = [] if tut else sorted([random.uniform(1.0, 11.0), k] for k, n in s.A["kinds"] for _ in range(n))
        s.t, s.shake, s.state, s.result, s.loot, s.fail_t = 0.0, 0.0, "play", None, None, 0.0
        s.pending = [[] for _ in players]
        s.portal, s.kills, s.looted, s.dummy_hits = False, 0, 0, 0
        s.banner = [f"AREA {area + 1}/{len(AREAS)}: {s.A['name'].upper()}", 2.5]
        s.amb = [dict(x=random.random() * W, y=random.random() * FLOOR, p=random.random() * 6.28) for _ in range(AMB_N[area])]
        s.step, s.mark = -1, {}
        if tut: s.goto(0)

    def both(s, a):
        return f"[{kn(0, a)}] (P2: [{kn(1, a)}])"

    def nearest(s, x):
        al = [p for p in s.players if not p.down]
        return min(al, key=lambda p: abs(p.x - x)) if al else None

    def burst(s, x, y, color, n, sp):
        for _ in range(n):
            an, v = random.uniform(0, 6.28), random.uniform(0.3, 1) * sp
            s.parts.append([x, y, math.cos(an) * v, math.sin(an) * v - 30, random.uniform(0.3, 0.7), color, random.choice((1, 2, 2, 3))])

    def spawn(s, kind, x=None, **kw):
        if x is None: x = random.choice((14, W - 14))
        e = Enemy(kind, x, FLOOR - 70 if kind == "bat" else FLOOR, s.area, **kw)
        s.enemies.append(e); s.burst(x, e.y - 10, (200, 150, 255), 8, 60)

    def hurt(s, e, dmg, kb):
        if e.hp <= 0: return
        dmg = int(dmg)
        e.hp -= dmg; e.flash, e.kb = 0.12, kb
        if e.kind != "dummy": e.state, e.st = "rest", 0.3
        s.texts.append([e.x, e.y - e.d["h"] - 6, str(dmg), WHITE, 0.7]); s.burst(e.x, e.y - e.d["h"] / 2, (255, 240, 200), 6, 90)
        s.shake = max(s.shake, 2)
        if e.kind == "dummy": e.hp = 9999; s.dummy_hits += 1

    def kill(s, e):
        s.enemies.remove(e); s.kills += 1
        s.corpses.append(dict(x=e.x, y=FLOOR if e.kind == "bat" else e.y, kind=e.kind, tint=e.tint, hold=0.0, looted=False))
        s.burst(e.x, e.y - 10, (230, 230, 230), 16, 120); s.shake = 5

    def slash_hit(s, p, reach=34, dmg=None):
        x0, x1 = (p.x - 4, p.x + reach) if p.face > 0 else (p.x - reach, p.x + 4)
        for e in list(s.enemies):
            if id(e) not in p.hitset and overlap(x0, x1, p.y - 32, p.y + 2, e):
                p.hitset.add(id(e)); s.hurt(e, dmg or p.atk, p.face * 170)

    def hit_radius(s, x, y, r, dmg, kb=140):
        for e in list(s.enemies):
            if abs(e.x - x) <= r + e.d["w"] / 2 and abs((e.y - e.d["h"] / 2) - y) <= r + e.d["h"] / 2:
                s.hurt(e, dmg, (1 if e.x >= x else -1) * kb)

    # ---- Primary Skill (cast)
    def cast(s, p):
        c = p.cls
        p.cast_cd, p.casts, p.hitset = CLASSES[c]["cd"], p.casts + 1, set()
        if c == "Knight":
            p.skill, p.skill_t, p.inv = "charge", 0.22, max(p.inv, 0.3)
        elif c == "Tank":
            s.hit_radius(p.x, p.y - 10, 58, p.atk * 1.5, 200)
            for e in s.enemies:
                if abs(e.x - p.x) < 62 and e.kind != "dummy": e.stun = 1.5
            s.burst(p.x, p.y, (255, 220, 150), 26, 170); s.shake = 9
        elif c == "Fighter":
            p.skill, p.skill_t, p.tick = "whirl", 0.72, 0.0
        elif c == "Mage":
            s.projs.append(dict(kind="fire", x=p.x + 14 * p.face, y=p.y - 18, vx=255 * p.face, vy=0.0, dmg=p.atk * 1.75, life=1.6, pierce=False, hit=set()))
        else:  # Rogue Shadow Step
            tg = [e for e in s.enemies if abs(e.x - p.x) < 180]
            if not tg:
                p.cast_cd, p.casts = 0.4, p.casts - 1
                return
            e = min(tg, key=lambda e: abs(e.x - p.x))
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90)
            p.x, p.y, p.vy, p.inv = max(10, min(W - 10, e.x - e.face * 20)), e.y, 0.0, 0.4
            p.face = 1 if e.x > p.x else -1
            s.burst(p.x, p.y - 14, (150, 90, 220), 12, 90); s.hurt(e, p.atk * 2.4, p.face * 160)

    # ---- Secondary Skill (cast2)
    def cast2(s, p):
        c = p.cls
        p.cast2_cd, p.casts2 = CLASSES[c]["cd2"], p.casts2 + 1
        if c == "Knight":  # Aegis Banner
            for ally in s.players:
                if not ally.down and abs(ally.x - p.x) < 95:
                    heal = min(ally.maxhp - ally.hp, 25)
                    ally.hp += heal
                    ally.inv = max(ally.inv, 0.6)
                    s.texts.append([ally.x, ally.y - 36, f"+{heal} HP", GREEN, 1.0])
            s.hit_radius(p.x, p.y - 14, 52, p.atk * 0.9, 220)
            s.burst(p.x, p.y - 16, GOLD, 24, 140); s.shake = 4
        elif c == "Tank":  # Iron Taunt
            p.shield, p.shield_t = 30.0, 4.0
            s.texts.append([p.x, p.y - 40, "+30 SHIELD", CYAN, 1.0])
            for e in s.enemies:
                if abs(e.x - p.x) < 140 and e.kind != "dummy":
                    e.kb = (1 if p.x > e.x else -1) * 180
                    e.stun = max(e.stun, 0.6)
            s.burst(p.x, p.y - 14, CYAN, 22, 130); s.shake = 5
        elif c == "Fighter":  # Blade Wave
            s.projs.append(dict(kind="wave", x=p.x + 14 * p.face, y=p.y - 16, vx=290 * p.face, vy=0.0, dmg=p.atk * 1.35, life=1.2, pierce=True, hit=set()))
            s.burst(p.x + 10 * p.face, p.y - 16, (180, 230, 255), 10, 80)
        elif c == "Mage":  # Frost Nova
            s.hit_radius(p.x, p.y - 14, 68, p.atk * 1.15, 90)
            for e in s.enemies:
                if abs(e.x - p.x) < 72 and e.kind != "dummy":
                    e.frozen = 2.0
            s.burst(p.x, p.y - 14, CYAN, 28, 160); s.shake = 5
        else:  # Rogue Fan of Knives
            p.vx = -p.face * 150
            p.vy = min(p.vy, -140)
            for vy in (-70, 0, 70):
                s.projs.append(dict(kind="knife", x=p.x + 10 * p.face, y=p.y - 16, vx=310 * p.face, vy=vy, dmg=p.atk * 0.85, life=0.75, pierce=False, hit=set()))
            s.burst(p.x, p.y - 14, BLADE, 10, 70)

    # ---- tutorial
    def goto(s, n):
        s.step, p = n, s.players[0]
        s.enemies, s.projs, s.corpses = [], [], []
        s.mark = dict(
            travel=p.travel, djumps=p.djumps, dashes=p.dashes, blocks=p.blocks,
            casts=p.casts, casts2=p.casts2, kills=s.kills, hits=s.dummy_hits, looted=s.looted
        )
        if n in (3, 5):
            s.spawn("dummy", 300)
        elif n == 4:
            s.spawn("skeleton", 380, dscale=0.0, hp=9999)
        elif n == 6:
            s.spawn("skeleton", 380, dscale=0.55)
        elif n == 8:
            SET["tutorial_done"] = True
            save_settings()

    def tut_info(s):
        p, m, b, st = s.players[0], s.mark, s.both, s.step
        if st == 0:
            v = p.travel - m["travel"]
            return "MOVE", [f"Left: {b('left')}", f"Right: {b('right')}"], v >= 120, f"{min(120, int(v))}/120"
        if st == 1:
            return "JUMP & WALL-JUMP", [
                f"Jump: {b('jump')} (hold for higher jump)",
                "Press jump AGAIN in mid-air or on a wall for a double / wall jump.",
                f"Drop through a platform: {b('down')}"
            ], p.djumps > m["djumps"], ""
        if st == 2:
            return "DASH", [f"Dash: {b('dash')}", "Works on ground or mid-air with brief invincibility."], p.dashes > m["dashes"], ""
        if st == 3:
            v = s.dummy_hits - m["hits"]
            return "SLASH", [f"Slash: {b('slash')}", "Hit the training dummy 3 times."], v >= 3, f"{min(3, v)}/3"
        if st == 4:
            v = p.blocks - m["blocks"]
            return "BLOCK & PARRY", [
                f"Block: HOLD {b('block')} facing the enemy",
                "Block when the skeleton flashes red and shows '!'",
                "Block at the last instant = PERFECT BLOCK (stuns it)."
            ], v >= 2, f"{min(2, v)}/2"
        if st == 5:
            d = CLASSES[p.cls]
            c1, c2 = p.casts > m["casts"], p.casts2 > m["casts2"]
            return "CAST BOTH SKILLS", [
                f"Skill 1 ({d['skill']}): {b('cast')}",
                f"Skill 2 ({d['skill2']}): {b('cast2')}",
                "Cast BOTH skills once to continue."
            ], c1 and c2, f"{int(c1) + int(c2)}/2"
        if st == 6:
            return "FIGHT!", [
                "Defeat the skeleton! (If you fall, the fight restarts.)",
                f"Slash {b('slash')}   Block {b('block')}   Dash {b('dash')}",
                f"Skill 1 {b('cast')}   Skill 2 {b('cast2')}"
            ], s.kills > m["kills"], ""
        if st == 7:
            return "LOOT THE CORPSE", [
                f"Stand on the corpse and HOLD {b('interact')}",
                "Beat the mini-game (40%+) to claim loot.",
                "If you fail, you get NO loot and must retry!"
            ], s.looted > m["looted"], ""
        return "TUTORIAL COMPLETE", [
            "Clear all enemies in an area, loot corpses, then enter the portal.",
            "If both heroes fall, ALL unbanked loot from that area is lost!",
            f"Press {b('slash')} to continue"
        ], False, ""

    # ---- loot mini-game
    def start_loot(s, p, c):
        m = random.choice(MINIS)()
        m.hero, m.bonus = p.cls, bonus_for(p.cls, m.kind)
        s.loot, s.state = dict(p=p, c=c, m=m, intro=3.0, after=0.0, panel=pygame.Surface((PW, 180))), "loot"

    def update_loot(s, dt, mo):
        L = s.loot
        m = L["m"]
        if L["intro"] > 0:
            L["intro"] -= dt
            return
        m.update(dt, mo[L["p"].i])
        if m.over:
            L["after"] += dt
            if L["after"] > 1.3:
                p, c = L["p"], L["c"]
                if m.score >= 0.4:
                    c["looted"] = True
                    s.looted += 1
                    it = roll_loot(m.kind, m.score)
                    s.pending[p.i].append(it)
                    s.texts.append([c["x"], c["y"] - 34, it["name"], RARITY[it["tier"]][1], 2.5])
                else:
                    c["hold"] = 0.0
                    if not s.tut:
                        c["looted"] = True
                    s.texts.append([c["x"], c["y"] - 34, "Failed - no loot!" + (" Try again!" if s.tut else ""), RED, 2.2])
                s.state, s.loot = "play", None

    # ---- update
    def fx(s, dt):
        for pt in s.parts[:]:
            pt[0] += pt[2] * dt; pt[1] += pt[3] * dt; pt[3] += 300 * dt; pt[4] -= dt
            if pt[4] <= 0: s.parts.remove(pt)
        for tx in s.texts[:]:
            tx[1] -= 18 * dt; tx[4] -= dt
            if tx[4] <= 0: s.texts.remove(tx)
        for m in s.amb:
            i = s.area
            if i == 0: m["y"] -= 4 * dt; m["x"] += math.sin(s.t + m["p"]) * 4 * dt
            elif i == 1: m["x"] += math.sin(s.t * .7 + m["p"]) * 14 * dt; m["y"] += math.cos(s.t * .9 + m["p"]) * 10 * dt
            elif i == 2: m["y"] -= (18 + m["p"] * 3) * dt; m["x"] += math.sin(s.t * 1.4 + m["p"]) * 8 * dt
            elif i == 3: m["y"] -= (25 + m["p"] * 4) * dt; m["x"] += math.sin(s.t + m["p"]) * 10 * dt
            elif i == 4: m["y"] += (20 + m["p"] * 3) * dt; m["x"] += math.sin(s.t + m["p"]) * 10 * dt
            else: m["y"] -= (8 + m["p"] * 2) * dt; m["x"] += math.cos(s.t * .8 + m["p"]) * 12 * dt
            if m["y"] < 0: m["y"] = FLOOR
            if m["y"] > FLOOR: m["y"] = 0
            m["x"] %= W

    def update(s, dt, mo):
        s.t += dt
        s.shake, s.banner[1] = max(0, s.shake - 30 * dt), s.banner[1] - dt
        s.fx(dt)
        if s.state == "loot": s.update_loot(dt, mo); return
        if s.state == "failed":
            s.fail_t += dt
            if s.fail_t > 0.8 and any(m.slash_p for m in mo): s.result = "retry"
            return
        for p in s.players: p.update(dt, mo[p.i], s)
        while s.queue and s.queue[0][0] <= s.t: s.spawn(s.queue.pop(0)[1])
        for e in s.enemies[:]:
            e.update(dt, s)
            if e.hp <= 0: s.kill(e)
        for pr in s.projs[:]:
            pr["x"] += pr["vx"] * dt
            pr["y"] += pr["vy"] * dt
            pr["life"] -= dt
            hits = [e for e in s.enemies if id(e) not in pr["hit"] and overlap(pr["x"] - 6, pr["x"] + 6, pr["y"] - 8, pr["y"] + 8, e)]
            if hits:
                if pr["kind"] == "fire":
                    s.projs.remove(pr)
                    s.hit_radius(pr["x"], pr["y"], 30, pr["dmg"], 160)
                    s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140); s.shake = 4
                    continue
                for e in hits:
                    pr["hit"].add(id(e))
                    s.hurt(e, pr["dmg"], (1 if pr["vx"] >= 0 else -1) * 130)
                if not pr["pierce"]:
                    s.projs.remove(pr)
                    s.burst(pr["x"], pr["y"], BLADE, 6, 70)
                    continue
            if pr["life"] <= 0 or not 0 < pr["x"] < W or not 0 < pr["y"] < FLOOR:
                if pr in s.projs:
                    if pr["kind"] == "fire":
                        s.hit_radius(pr["x"], pr["y"], 28, pr["dmg"], 160)
                        s.burst(pr["x"], pr["y"], (255, 160, 50), 20, 140)
                    s.projs.remove(pr)
        for c in s.corpses:
            if c["looted"]: continue
            who = [p for p in s.players if not p.down and mo[p.i].interact_h and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
            c["hold"] = c["hold"] + dt if who else max(0, c["hold"] - 2 * dt)
            if who and c["hold"] >= 0.5:
                s.start_loot(who[0], c)
                break
        if s.tut:
            for p in s.players:
                if p.down:
                    p.down, p.hp = False, p.maxhp
                    s.texts.append([p.x, p.y - 36, "TRY AGAIN!", RED, 1.2])
                    s.goto(s.step)
                    return
            if s.step == 8:
                if mo[0].slash_p and s.t > 0.5: s.result = "menu"
            elif s.tut_info()[2]:
                s.goto(s.step + 1)
        else:
            if not s.queue and not [e for e in s.enemies if e.kind != "dummy"] and not s.portal:
                s.portal = True; s.banner = ["AREA CLEARED! Loot the corpses, then enter the portal >>", 4.0]
                for p in s.players:
                    if p.down: p.down, p.hp = False, p.maxhp * 0.4
            if s.portal and any(not p.down and p.x > W - 40 for p in s.players): s.result = "next"
            if all(p.down for p in s.players):
                s.state, s.pending = "failed", [[] for _ in s.players]

    # ---- draw
    def draw_hud(s):
        for p in s.players:
            x, d = (8 if p.i == 0 else W - 128), CLASSES[p.cls]
            text(f"P{p.i + 1} {p.cls}", x, 6, P_COL[p.i])
            bar(x, 19, 120, 7, p.hp / p.maxhp, RED if p.hp > p.maxhp * .3 else (255, 120, 40))
            if p.shield > 0:
                bar(x, 19, int(120 * min(1.0, p.shield / 30.0)), 3, 1.0, CYAN)
            cd1 = 1 - p.cast_cd / d["cd"]
            cd2 = 1 - p.cast2_cd / d["cd2"]
            bar(x, 30, 58, 4, cd1, CYAN if cd1 >= 1 else STEEL_D)
            bar(x + 62, 30, 58, 4, cd2, GOLD if cd2 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast')}] {d['skill'][:9]}", x, 37, WHITE if cd1 >= 1 else STEEL_D)
            text(f"[{kn(p.i, 'cast2')}] {d['skill2'][:9]}", x, 48, GOLD if cd2 >= 1 else STEEL_D)
            if not s.tut:
                text(f"Unbanked loot: {len(s.pending[p.i])}", x, 60, GOLD)
        if not s.tut:
            text(f"AREA {s.area + 1}/{len(AREAS)}: {s.A['name']}", W // 2, 6, WHITE, font, True)

    def draw(s):
        use(world)
        world.blit(get_bg(s.area), (0, 0))
        if s.area == 0: draw_torches(s.t)
        elif s.area == 5: draw_runes(s.t)
        for m in s.amb:
            col = [(150, 140, 180), (230, 240, 120), (140, 235, 250), (255, 150, 50), (255, 255, 255), (200, 150, 255)][s.area]
            if s.area == 1 and math.sin(s.t * 3 + m["p"]) > 0:
                glow(m["x"], m["y"], 8, (90, 100, 20))
            if s.area == 2:
                pygame.draw.circle(canvas, col, (int(m["x"]), int(m["y"])), 2, 1)
            else:
                pygame.draw.rect(canvas, col, (int(m["x"]), int(m["y"]), 2 if s.area else 1, 2 if s.area else 1))
        if s.portal:
            x, y = W - 28, FLOOR
            col = lerp((90, 60, 200), (160, 230, 255), 0.5 + 0.5 * math.sin(s.t * 4))
            pygame.draw.rect(canvas, INK, (x - 17, y - 56, 34, 56)); pygame.draw.circle(canvas, INK, (x, y - 56), 17)
            pygame.draw.rect(canvas, col, (x - 13, y - 56, 26, 56)); pygame.draw.circle(canvas, col, (x, y - 56), 13)
            glow(x, y - 40, 50, (60, 50, 120))
            text("NEXT AREA", W - 4, y - 90 + int(math.sin(s.t * 3) * 3), WHITE, font, right=True)
        for c in s.corpses:
            fr = CORPSE[(c["kind"], c["tint"] if c["kind"] == "slime" else 0)]
            blit_ent(fr, c["x"], c["y"], False, (-60, -60, -60) if c["looted"] else None)
            if not c["looted"]:
                gy = c["y"] - 26 + math.sin(s.t * 4 + c["x"]) * 3
                glow(c["x"], gy, 18, (110, 90, 30)); gem(int(c["x"]), int(gy), GOLD, 5)
                near = [p for p in s.players if not p.down and abs(p.x - c["x"]) < 26 and abs(p.y - c["y"]) < 30]
                if near: text(f"HOLD [{kn(near[0].i, 'interact')}]", c["x"], c["y"] - 50, P_COL[near[0].i], font, True)
                if c["hold"] > 0: bar(int(c["x"]) - 12, int(c["y"]) - 42, 24, 4, c["hold"] / 0.5, GOLD)
        ents = [(e.y, e) for e in s.enemies] + [(p.y, p) for p in s.players if not p.down]
        for _, o in sorted(ents, key=lambda z: z[0]):
            if isinstance(o, Enemy):
                fr = ENEMY[(o.kind, o.tint if o.kind == "slime" else 0)]
                sy = FLOOR if o.kind == "bat" else o.y
                pygame.draw.ellipse(canvas, (10, 8, 16), (o.x - 9, sy - 2, 18, 4))
                tint = (0, 90, 130) if o.frozen > 0 else ((110, 0, 0) if (o.state == "wind" and int(s.t * 14) % 2 == 0) else ((110, 110, 110) if o.flash > 0 else None))
                blit_ent(fr[int(o.anim * 6) % len(fr)], o.x, o.y, o.face > 0, tint)
                if o.frozen > 0:
                    pygame.draw.rect(canvas, CYAN, (int(o.x) - 8, int(o.y - o.d["h"]), 16, o.d["h"]), 1)
                elif o.state == "wind":
                    text("!", o.x - 2, o.y - o.d["h"] - 16, RED, mid)
                if o.hp < o.maxhp < 9000: bar(int(o.x) - 10, int(o.y - o.d["h"]) - 8, 20, 3, o.hp / o.maxhp, RED)
            else:
                pygame.draw.ellipse(canvas, (10, 8, 16), (o.x - 9, o.y - 2, 18, 4))
                if o.inv > 0 and o.dash_t <= 0 and int(s.t * 24) % 2: continue
                fr = HERO[o.cls][1][int(o.anim) % 8] if (o.ground and o.anim > 0) else (HERO[o.cls][0] if o.ground else HERO[o.cls][1][2])
                blit_ent(fr, o.x + (o.face * 3 if o.slash_t > 0 else 0), o.y, o.face < 0, (110, 110, 110) if o.flash > 0 else None)
                cx, cy = o.x, o.y - 17
                if o.shield > 0:
                    pygame.draw.circle(canvas, CYAN, (int(cx), int(cy)), 16, 1)
                if o.slash_t > 0:
                    for r, col, w in ((28, WHITE, 3), (22, (180, 220, 255), 2)):
                        pts = [(cx + o.face * math.cos(math.radians(-70 + 140 * k / 6)) * r, cy + math.sin(math.radians(-70 + 140 * k / 6)) * r) for k in range(7)]
                        pygame.draw.lines(canvas, col, False, pts, w)
                if o.block:
                    pts = [(cx + o.face * (6 + math.cos(math.radians(-80 + 160 * k / 6)) * 18), cy + math.sin(math.radians(-80 + 160 * k / 6)) * 18) for k in range(7)]
                    pygame.draw.lines(canvas, GOLD if o.block_t < 0.2 else CYAN, False, pts, 2)
                if o.skill == "whirl":
                    pygame.draw.circle(canvas, WHITE, (int(cx), int(cy)), 32, 1)
                    for k in range(3):
                        an = s.t * 22 + k * 2.1
                        pygame.draw.line(canvas, WHITE, (cx, cy), (cx + math.cos(an) * 32, cy + math.sin(an) * 32), 2)
        for pr in s.projs:
            if pr["kind"] == "fire":
                glow(pr["x"], pr["y"], 22, (200, 90, 20))
                pygame.draw.circle(canvas, (255, 140, 40), (int(pr["x"]), int(pr["y"])), 5); pygame.draw.circle(canvas, GOLD, (int(pr["x"]), int(pr["y"])), 3)
            elif pr["kind"] == "wave":
                d = 1 if pr["vx"] >= 0 else -1
                pts = [(pr["x"] - d * 4, pr["y"] - 12), (pr["x"] + d * 6, pr["y"]), (pr["x"] - d * 4, pr["y"] + 12)]
                pygame.draw.lines(canvas, CYAN, False, pts, 3)
            else:
                d = 1 if pr["vx"] >= 0 else -1
                pygame.draw.line(canvas, BLADE, (pr["x"] - d * 5, pr["y"]), (pr["x"] + d * 5, pr["y"]), 2)
        for pt in s.parts: pygame.draw.rect(canvas, pt[5], (int(pt[0]), int(pt[1]), pt[6], pt[6]))
        for tx in s.texts: text(tx[2], tx[0], tx[1], tx[3], font, True)
        use(main_cv)
        main_cv.fill(INK)
        main_cv.blit(world, (int(random.uniform(-1, 1) * s.shake), int(random.uniform(-1, 1) * s.shake)))
        main_cv.blit(VIGNETTE, (0, 0))
        s.draw_hud()
        if s.banner[1] > 0 and not s.tut: text(s.banner[0], W // 2, 78, GOLD, mid, True)
        if s.tut:
            title, lines, done, prog = s.tut_info()
            ls = [ln for t in lines for ln in wrap(t, 31)]
            h = 28 + len(ls) * 11 + (12 if prog else 0)
            pygame.draw.rect(main_cv, INK, (132, 4, 216, h)); pygame.draw.rect(main_cv, GOLD, (132, 4, 216, h), 1)
            text(f"{'STEP %d/8: ' % (s.step + 1) if s.step < 8 else ''}{title}", 240, 8, GOLD, font, True)
            for k, ln in enumerate(ls): text(ln, 138, 23 + k * 11)
            if prog: text(f"Progress: {prog}", 138, 23 + len(ls) * 11, CYAN)
            text("Esc = menu", W - 6, H - 14, STEEL_D, font, right=True)
        if s.state == "failed":
            main_cv.blit(DIM, (0, 0))
            title_text("DEFEATED", W // 2, 70, RED)
            text("Both heroes fell - no loot kept from this area!", W // 2, 130, WHITE, mid, True)
            text(f"Press Slash  P1 [{kn(0, 'slash')}]  P2 [{kn(1, 'slash')}]  to retry the area", W // 2, 160, STEEL, font, True)
        if s.state == "loot":
            L = s.loot
            main_cv.blit(DIM, (0, 0))
            use(L["panel"]); L["m"].draw()
            if L["intro"] > 0:
                pygame.draw.rect(canvas, INK, (8, 24, 144, 142)); pygame.draw.rect(canvas, GOLD, (8, 24, 144, 142), 1)
                text(L["m"].title, 80, 32, GOLD, mid, True)
                for k, ln in enumerate(wrap(L["m"].hint, 21) + [""] + wrap(L["m"].ctrl(L["p"].i), 21) + [""] + wrap("Score 40%+ to win the loot!", 21)):
                    text(ln, 80, 62 + k * 12, WHITE if k < 3 else CYAN, font, True)
            elif L["m"].over:
                b = f" (+{int(L['m'].bonus * 100)}% class)" if L["m"].bonus else ""
                text(f"{int(L['m'].score * 100)}%{b}", 80, 154, GOLD if L["m"].score >= .4 else RED, font, True)
            text(f"P{L['p'].i + 1} {L['p'].cls}", 80, 165, P_COL[L["p"].i], font, True)
            use(main_cv)
            main_cv.blit(L["panel"], ((W - PW) // 2, (H - 180) // 2))


# ================================================================ screens
def present():
    if FAST: screen.blit(main_cv, (0, 0))
    else: pygame.transform.scale(main_cv, screen.get_size(), screen)
    pygame.display.flip()


def draw_menu(sel, t):
    canvas.blit(get_bg(0), (0, 0)); draw_torches(t)
    canvas.blit(VIGNETTE, (0, 0))
    title_text("ROGUE LOOT", W // 2, 22, GOLD)
    text("2-PLAYER CO-OP ADVENTURE", W // 2, 76, STEEL, font, True)
    for i, it in enumerate(("START", "TUTORIAL", "SETTINGS", "EXIT")):
        text(f"> {it} <" if i == sel else it, W // 2, 104 + i * 24, GOLD if i == sel else WHITE, mid, True)
    for k, cls in enumerate(("Knight", "Mage")):
        blit_ent(HERO[cls][1][int(t * 10) % 8], (t * 40 + k * 120) % (W + 60) - 30, FLOOR)
    text("W/S or Up/Down: move    Enter/Space: select" + ("" if SET["tutorial_done"] else "    (First launch runs Tutorial)"), W // 2, 252, STEEL, font, True)


def draw_select(sel, ready, t):
    canvas.fill((24, 18, 36))
    title_text("CHOOSE YOUR CLASS", W // 2, 4, GOLD, 2)
    pygame.draw.rect(canvas, (70, 60, 100), (W // 2 - 1, 28, 2, H - 30))
    for p in range(2):
        cx, name = 120 + p * 240, CLASS_NAMES[sel[p]]
        d = CLASSES[name]
        text(f"P{p + 1} - {d['role']}", cx, 28, P_COL[p], font, True)
        pygame.draw.ellipse(canvas, (12, 8, 20), (cx - 16, 82, 32, 6))
        canvas.blit(pygame.transform.scale(HERO[name][1][int(t * 10) % 8], (48, 52)), (cx - 24, 34))
        if not ready[p]:
            text("<", cx - 54, 52, WHITE, big); text(">", cx + 42, 52, WHITE, big)
        text(f"{name.upper()}  (HP {d['hp']} / ATK {d['atk']} / DEF {d['df']})", cx, 90, WHITE, font, True)
        y = 104
        text(f"[{kn(p, 'cast')}] SKILL 1: {d['skill']} ({d['cd']}s)", cx, y, CYAN, font, True); y += 12
        for ln in wrap(d["sdesc"], 35): text(ln, cx, y, WHITE, font, True); y += 11
        text(f"[{kn(p, 'cast2')}] SKILL 2: {d['skill2']} ({d['cd2']}s)", cx, y + 2, GOLD, font, True); y += 14
        for ln in wrap(d["s2desc"], 35): text(ln, cx, y, WHITE, font, True); y += 11
        for ln in wrap(d["pdesc"], 35): text(ln, cx, y + 2, GREEN, font, True); y += 11
        if ready[p]: text("READY!", cx, 246, GREEN, mid, True)
        else: text(f"Swap: [{kn(p, 'left')}]/[{kn(p, 'right')}]   Ready: [{kn(p, 'slash')}]", cx, 250, P_COL[p], font, True)


def main():
    motions = [Motion(0), Motion(1)]
    mode, msel, t = "menu", 0, 0.0
    arena, area, inv, heroes, first_run = None, 0, [[], []], ["Knight", "Tank"], False
    sel, ready, sel_t = [0, 1], [False, False], 0.0
    s_tab, s_row, listening = 0, 0, False

    def new_arena(a):
        return Arena(a, [Player(0, heroes[0], 80), Player(1, heroes[1], 110)])

    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        t += dt
        events = pygame.event.get()
        keys = [e.key for e in events if e.type == pygame.KEYDOWN]
        for e in events:
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
        for m in motions: m.update(events, dt)
        use(main_cv)
        up = any(k in (pygame.K_UP, pygame.K_w) for k in keys)
        dn = any(k in (pygame.K_DOWN, pygame.K_s) for k in keys)
        ok = any(k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER) for k in keys)
        back = pygame.K_ESCAPE in keys

        if mode == "menu":
            msel = (msel + dn - up) % 4
            if ok:
                if msel == 0:
                    if SET["tutorial_done"]: mode, sel, ready = "select", [0, 1], [False, False]
                    else: mode, first_run, arena = "tutorial", True, Arena(0, [Player(0, "Knight", 80)], True)
                elif msel == 1: mode, first_run, arena = "tutorial", False, Arena(0, [Player(0, "Knight", 80)], True)
                elif msel == 2: mode, s_tab, s_row, listening = "settings", 0, 0, False
                else: pygame.quit(); sys.exit()
            draw_menu(msel, t)

        elif mode == "settings":
            n = len(ACTIONS) + 2
            if listening:
                for k in keys:
                    if k == pygame.K_ESCAPE: listening = False
                    else:
                        kb, act = SET["keys"][s_tab], ACTIONS[s_row]
                        for a2 in ACTIONS:
                            if a2 != act and kb[a2] == k: kb[a2] = kb[act]
                        kb[act] = k; save_settings(); listening = False
                        break
            else:
                s_row = (s_row + dn - up) % n
                if any(k in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB, pygame.K_a, pygame.K_d) for k in keys): s_tab = 1 - s_tab
                if back: mode = "menu"
                if ok:
                    if s_row < len(ACTIONS): listening = True
                    elif s_row == len(ACTIONS): SET["keys"] = [dict(k) for k in DEFAULT_KEYS]; save_settings()
                    else: mode = "menu"
            canvas.fill((24, 18, 36))
            title_text("KEY BINDINGS", W // 2, 6, GOLD, 2)
            for i in range(2):
                text(f"PLAYER {i + 1}", 150 + i * 180, 36, P_COL[i] if s_tab == i else STEEL_D, mid, True)
            pygame.draw.rect(canvas, P_COL[s_tab], (90 + s_tab * 180, 54, 120, 2))
            for r in range(n):
                y, sel_row = 62 + r * 15, r == s_row
                if r < len(ACTIONS):
                    val = "press a key..." if (listening and sel_row) else kn(s_tab, ACTIONS[r])
                    text(LABEL[ACTIONS[r]], 100, y, GOLD if sel_row else WHITE)
                    text(val, 380, y, CYAN if listening and sel_row else (GOLD if sel_row else STEEL), font, right=True)
                else:
                    text("RESET TO DEFAULTS" if r == len(ACTIONS) else "BACK", W // 2, y + 4, GOLD if sel_row else WHITE, font, True)
            text("W/S: move   A/D or Left/Right: switch player   Enter: rebind   Esc: back", W // 2, 253, STEEL, font, True)

        elif mode == "select":
            sel_t += dt
            for p, m in enumerate(motions):
                if not ready[p] and m.swing in ("left", "right"): sel[p] = (sel[p] + (1 if m.swing == "right" else -1)) % len(CLASS_NAMES)
                if m.slash_p: ready[p] = not ready[p]
            if back: mode = "menu"
            draw_select(sel, ready, sel_t)
            if all(ready):
                heroes, area, inv = [CLASS_NAMES[i] for i in sel], 0, [[], []]
                arena, mode = new_arena(0), "game"

        elif mode in ("game", "tutorial"):
            arena.update(dt, motions)
            arena.draw()
            if back: mode = "menu"
            r = arena.result
            if r == "menu":
                mode = "select" if first_run else "menu"
                sel, ready, first_run = [0, 1], [False, False], False
            elif r == "retry": arena = new_arena(area)
            elif r == "next":
                for p in range(2): inv[p].extend(arena.pending[p])
                area += 1
                if area >= len(AREAS): mode = "victory"
                else: arena = new_arena(area)

        else:  # victory
            canvas.fill((24, 18, 36))
            title_text("VICTORY!", W // 2, 8, GOLD)
            for p in range(2):
                cx = 120 + p * 240
                text(f"P{p + 1} {heroes[p]} - {len(inv[p])} items", cx, 60, P_COL[p], mid, True)
                for k, it in enumerate(sorted(inv[p], key=lambda i: -i["tier"])[:12]):
                    text(it["name"][:32], cx, 82 + k * 13, RARITY[it["tier"]][1], font, True)
            text("Press Enter for the main menu", W // 2, 252, STEEL, font, True)
            if ok: mode = "menu"
        present()


if __name__ == "__main__":
    main()
