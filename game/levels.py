"""The six castle levels (data-driven) and their procedural backgrounds.

Level fields: name, tag (intro tagline), sky/floor/top/plat colours, plats [(x, y, w)], waves [[(kind, count), ...], ...] (one list per wave), boss,
tint (slime colour index), amb=(count, colour, shape, motion), torches/runes (decor), grass (floor tufts), hint (show controls).
"""
import math, random
import pygame
from . import gfx
from .config import *
from .gfx import lerp, lit, dim, box, glow

LEVELS = [
    dict(name="Castle Basement", tag="Damp stone, rusty chains. Something shuffles in the dark...",
         sky=((18, 14, 30), (44, 34, 64)), floor=(60, 50, 76), top=(96, 82, 116), plat=(84, 70, 104),
         plats=[(70, 176, 96), (310, 170, 96), (190, 128, 100)], waves=[[("zombie", 4)], [("zombie", 3), ("skeleton", 2)], [("skeleton", 3), ("zombie", 1)]], boss="gravekeeper",
         tint=0, amb=(18, (150, 140, 180), "px", "dust"), torches=True, hint=True, bg="basement"),
    dict(name="Overgrown Jungle", tag="Vines have swallowed the east wing. The beast folk hunt here.",
         sky=((8, 30, 22), (30, 92, 60)), floor=(46, 84, 40), top=(86, 160, 64), plat=(96, 72, 48),
         plats=[(50, 172, 90), (330, 172, 90), (190, 134, 100)], waves=[[("bunny", 3), ("wolf", 2)], [("wolfman", 2), ("catman", 2)], [("bunny", 2), ("catman", 2), ("wolf", 1)]],
         boss="beastlord", tint=1, amb=(22, (230, 240, 120), "glow", "firefly"), grass=True, bg="jungle"),
    dict(name="Holy Cathedral", tag="The knights who guard the light will not let you pass.",
         sky=((38, 32, 60), (140, 120, 160)), floor=(150, 140, 160), top=(232, 222, 200), plat=(190, 180, 200),
         plats=[(60, 170, 100), (320, 170, 100), (190, 130, 100)], waves=[[("knight", 3)], [("knight", 3)], [("knight", 3)]], boss="paladin",
         tint=2, amb=(26, (255, 230, 150), "px", "motes"), torches=True, chest=True, bg="cathedral"),
    dict(name="Necropolis", tag="The dead rise at the Archlich's command.",
         sky=((10, 18, 18), (34, 64, 56)), floor=(44, 60, 52), top=(90, 130, 100), plat=(60, 84, 70),
         plats=[(50, 170, 90), (330, 170, 90), (190, 130, 100), (120, 96, 60)], waves=[[("skeleton", 3), ("zombie", 2)], [("lich", 2), ("zombie", 2)], [("lich", 2), ("skeleton", 2)]],
         boss="archlich", tint=3, amb=(30, (120, 240, 150), "px", "wisp"), runes=True, bg="necropolis"),
    dict(name="Mafia Penthouse", tag="Someone is running a very illegal operation in the castle's top floor.",
         sky=((20, 10, 32), (60, 24, 70)), floor=(92, 28, 48), top=(170, 60, 80), plat=(60, 50, 70),
         plats=[(40, 172, 90), (350, 172, 90), (150, 138, 80), (250, 138, 80)], waves=[[("gunman", 3)], [("wolf", 2), ("gunman", 2)], [("gunman", 2), ("brute", 2)]],
         boss="don", tint=4, amb=(22, (160, 160, 170), "px", "dust"), bg="penthouse"),
    dict(name="Observatory Roof", tag="Above the clouds, something has landed.",
         sky=((6, 4, 20), (44, 20, 80)), floor=(46, 36, 76), top=(130, 100, 210), plat=(74, 56, 124),
         plats=[(48, 174, 84), (348, 174, 84), (130, 132, 76), (274, 132, 76), (200, 94, 80)],
         waves=[[("drone", 4)], [("alien", 3), ("wolf", 2)], [("alien", 2), ("wolf", 2), ("lich", 1)]], boss="tycoon", tint=5,
         amb=(44, (255, 255, 255), "px", "astral"), runes=True, bg="observatory"),
]
NUM_LEVELS = len(LEVELS)


def waves_of(level):
    """The level's waves as a list of waves, each a list of (kind, count). Accepts the old flat form [(kind, n), ...] as a single wave."""
    w = level["waves"]
    return [list(x) for x in w] if (w and isinstance(w[0], list)) else ([list(w)] if w else [])


def wave_total(level):
    return sum(n for wv in waves_of(level) for _, n in wv)


# ---------------------------------------------------------------- ambient particle motion (name -> fn(m, t, dt))
def _dust(m, t, dt): m["y"] -= 4 * dt; m["x"] += math.sin(t + m["p"]) * 4 * dt
def _firefly(m, t, dt): m["x"] += math.sin(t * .7 + m["p"]) * 14 * dt; m["y"] += math.cos(t * .9 + m["p"]) * 10 * dt
def _motes(m, t, dt): m["y"] -= (10 + m["p"] * 2) * dt; m["x"] += math.sin(t * .8 + m["p"]) * 6 * dt
def _wisp(m, t, dt): m["x"] += math.sin(t * .5 + m["p"]) * 16 * dt; m["y"] += math.cos(t * .4 + m["p"]) * 5 * dt
def _astral(m, t, dt): m["y"] -= (8 + m["p"] * 2) * dt; m["x"] += math.cos(t * .8 + m["p"]) * 12 * dt


AMB_MOVES = dict(dust=_dust, firefly=_firefly, motes=_motes, wisp=_wisp, astral=_astral)


def new_ambient(level):
    n = LEVELS[level]["amb"][0]
    return [dict(x=random.random() * W, y=random.random() * FLOOR, p=random.random() * 6.28) for _ in range(n)]


def move_ambient(level, parts, t, dt):
    fn = AMB_MOVES[LEVELS[level]["amb"][3]]
    for m in parts:
        fn(m, t, dt)
        if m["y"] < 0: m["y"] = FLOOR
        if m["y"] > FLOOR: m["y"] = 0
        m["x"] %= W


# ---------------------------------------------------------------- backgrounds
def _bg_basement(sf, rnd):
    for row in range(0, FLOOR, 16):
        for x in range(-(row // 16 % 2) * 20, W, 40):
            pygame.draw.rect(sf, lerp((40, 32, 60), (58, 46, 82), rnd.random()), (x, row, 39, 15))
            pygame.draw.rect(sf, (74, 62, 100), (x, row, 39, 1))
    for x in (36, 200, 364):  # arches with tattered banners
        pygame.draw.rect(sf, (12, 8, 20), (x, 96, 64, FLOOR - 96)); pygame.draw.circle(sf, (12, 8, 20), (x + 32, 96), 32)
        pygame.draw.rect(sf, (96, 80, 124), (x - 4, 92, 72, 4)); pygame.draw.circle(sf, (96, 80, 124), (x + 32, 96), 36, 4)
        pygame.draw.polygon(sf, RED_D, [(x + 22, 104), (x + 42, 104), (x + 42, 148), (x + 32, 140), (x + 22, 148)])
        pygame.draw.rect(sf, GOLD, (x + 22, 104, 20, 2))
    for x in (130, 300, 440):  # hanging chains
        pygame.draw.line(sf, (96, 96, 116), (x, 0), (x, rnd.randint(50, 90)), 2)
    for bx in (100, 268, 420):  # barrels
        box(sf, BROWN_D, bx, FLOOR - 22, 18, 22); pygame.draw.rect(sf, (60, 40, 30), (bx, FLOOR - 16, 18, 2)); pygame.draw.rect(sf, (60, 40, 30), (bx, FLOOR - 7, 18, 2))
    for py in (30, 60):  # pipes
        pygame.draw.rect(sf, (70, 70, 90), (0, py, W, 5)); pygame.draw.rect(sf, (110, 110, 130), (0, py, W, 1))


def _bg_jungle(sf, rnd):
    pygame.draw.circle(sf, (70, 130, 90), (380, 48), 34); pygame.draw.circle(sf, (232, 240, 200), (380, 48), 22)
    for col, base, hh, stp in (((22, 70, 46), 176, 70, 30), ((14, 54, 38), 196, 90, 36), ((8, 38, 28), 216, 110, 44)):
        for x in range(-10, W + 20, stp):
            h = rnd.randint(hh - 18, hh + 18)
            pygame.draw.rect(sf, col, (x - 2, base, 4, FLOOR - base))
            pygame.draw.polygon(sf, col, [(x - 18, base), (x, base - h), (x + 18, base)])
            pygame.draw.polygon(sf, lit(col), [(x - 14, base - h // 3), (x, base - h - 8), (x + 14, base - h // 3)])
    for x in range(8, W, 36):  # hanging vines
        ln = rnd.randint(30, 90)
        for y in range(0, ln, 3):
            pygame.draw.rect(sf, (40, 130, 60), (x + int(math.sin(y * .2 + x) * 3), y, 2, 3))
        pygame.draw.circle(sf, (230, 90, 150), (x + int(math.sin(ln * .2 + x) * 3), ln), 3)
    for x in (70, 250, 420):  # ruined castle wall peeking through the leaves
        pygame.draw.rect(sf, (74, 84, 80), (x, 150, 26, FLOOR - 150)); pygame.draw.rect(sf, (96, 108, 100), (x, 150, 26, 3))


def _bg_cathedral(sf, rnd):
    for row in range(0, FLOOR, 18):
        for x in range(-(row // 18 % 2) * 22, W, 44):
            pygame.draw.rect(sf, lerp((64, 56, 86), (86, 78, 108), rnd.random()), (x, row, 43, 17))
    glass = [(220, 70, 90), (240, 190, 70), (80, 150, 230), (110, 210, 130)]
    for n, x in enumerate((46, 190, 334)):  # stained glass windows + light shafts
        pygame.draw.rect(sf, (20, 14, 30), (x, 40, 44, 130)); pygame.draw.circle(sf, (20, 14, 30), (x + 22, 40), 22)
        for k in range(4):
            c = glass[(n + k) % 4]
            pygame.draw.rect(sf, c, (x + 4 + (k % 2) * 19, 50 + (k // 2) * 52, 17, 46)); pygame.draw.circle(sf, c, (x + 22, 40), 15) if k == 0 else None
        pygame.draw.rect(sf, GOLD, (x, 40, 44, 130), 2)
        shaft = pygame.Surface((W, FLOOR), pygame.SRCALPHA)
        pygame.draw.polygon(shaft, (255, 240, 190, 26), [(x + 6, 90), (x + 38, 90), (x + 90, FLOOR), (x - 50, FLOOR)])
        sf.blit(shaft, (0, 0))
    for x in (8, 110, 258, 400, 462):  # columns
        pygame.draw.rect(sf, (200, 192, 214), (x, 60, 12, FLOOR - 60)); pygame.draw.rect(sf, (240, 232, 250), (x + 2, 60, 3, FLOOR - 60))
        pygame.draw.rect(sf, GOLD, (x - 3, 56, 18, 5)); pygame.draw.rect(sf, GOLD, (x - 3, FLOOR - 6, 18, 6))
    pygame.draw.rect(sf, (160, 40, 60), (150, FLOOR - 6, 180, 6))  # red carpet runner
    pygame.draw.rect(sf, GOLD, (232, 6, 3, 30)); pygame.draw.rect(sf, GOLD, (224, 14, 19, 3))  # hanging cross


def _bg_necropolis(sf, rnd):
    pygame.draw.circle(sf, (50, 90, 80), (90, 54), 30); pygame.draw.circle(sf, (200, 240, 220), (90, 54), 19)
    for x in range(-10, W, 34):  # tombstones & dead trees
        h = rnd.randint(16, 34)
        pygame.draw.rect(sf, (20, 34, 30), (x, FLOOR - h, 16, h)); pygame.draw.circle(sf, (20, 34, 30), (x + 8, FLOOR - h), 8)
        pygame.draw.rect(sf, (60, 90, 76), (x + 7, FLOOR - h + 2, 2, 8)); pygame.draw.rect(sf, (60, 90, 76), (x + 4, FLOOR - h + 5, 8, 2))
    for x in (70, 240, 400):
        pygame.draw.rect(sf, (14, 24, 22), (x, 110, 6, FLOOR - 110))
        for k in range(5):
            pygame.draw.line(sf, (14, 24, 22), (x + 3, 130 + k * 12), (x + rnd.choice((-1, 1)) * rnd.randint(14, 30), 112 + k * 10), 2)
    fog = pygame.Surface((W, FLOOR), pygame.SRCALPHA)
    for y in range(130, FLOOR, 6):
        pygame.draw.rect(fog, (110, 200, 150, 8), (0, y, W, 6))
    sf.blit(fog, (0, 0))


def _bg_penthouse(sf, rnd):
    for x in range(0, W, 40):  # wallpaper stripes + gold trim
        pygame.draw.rect(sf, (54, 22, 58), (x, 0, 20, FLOOR)); pygame.draw.rect(sf, (74, 30, 76), (x + 20, 0, 20, FLOOR))
    pygame.draw.rect(sf, GOLD, (0, 0, W, 4)); pygame.draw.rect(sf, GOLD, (0, FLOOR - 40, W, 3))
    pygame.draw.rect(sf, (14, 12, 30), (150, 30, 180, 120))  # big city window
    for x in range(150, 330, 14):
        h = rnd.randint(20, 90)
        pygame.draw.rect(sf, (26, 22, 52), (x, 150 - h, 12, h))
        for wy in range(150 - h + 4, 148, 8):
            if rnd.random() < .6: pygame.draw.rect(sf, rnd.choice(((255, 220, 120), (120, 220, 255), (255, 120, 200))), (x + 3, wy, 2, 3))
    pygame.draw.rect(sf, GOLD, (150, 30, 180, 120), 3); pygame.draw.line(sf, GOLD, (240, 30), (240, 150), 2)
    for x in (60, 400):  # framed portraits + chandelier
        pygame.draw.rect(sf, GOLD, (x, 60, 32, 42), 2); pygame.draw.rect(sf, (90, 60, 40), (x + 3, 63, 26, 36))
    pygame.draw.line(sf, GOLD, (240, 0), (240, 16), 1)
    pygame.draw.polygon(sf, GOLD, [(222, 18), (258, 18), (248, 30), (232, 30)])
    for cx in range(224, 258, 7): pygame.draw.rect(sf, (255, 240, 180), (cx, 12, 2, 6))
    pygame.draw.rect(sf, (130, 30, 40), (0, FLOOR - 4, W, 4))


def _bg_observatory(sf, rnd):
    for _ in range(90):
        c = rnd.choice([(255, 255, 255), (180, 210, 255), (255, 210, 160)])
        pygame.draw.rect(sf, c, (rnd.randint(0, W), rnd.randint(0, 170), rnd.choice((1, 1, 2)), 1))
    pygame.draw.circle(sf, (92, 54, 150), (110, 56), 24); pygame.draw.circle(sf, (132, 82, 200), (105, 51), 16)
    pygame.draw.ellipse(sf, (210, 170, 255), (72, 48, 76, 16), 2)
    pygame.draw.circle(sf, (58, 48, 92), (360, 150), 70); pygame.draw.rect(sf, (30, 24, 56), (290, 150, 140, FLOOR - 150))  # dome
    pygame.draw.polygon(sf, (10, 6, 26), [(350, 90), (372, 90), (388, 150), (338, 150)])  # dome slit
    pygame.draw.line(sf, (150, 150, 180), (340, 168), (420, 120), 6); pygame.draw.circle(sf, (200, 200, 230), (420, 120), 6)  # telescope
    pygame.draw.ellipse(sf, (150, 160, 180), (190, 36, 60, 16)); pygame.draw.ellipse(sf, (110, 230, 240), (206, 28, 28, 14))  # parked UFO
    for x in (212, 220, 228, 236): pygame.draw.rect(sf, (255, 220, 90), (x, 44, 3, 3))
    for ox, oy, oh in ((40, 140, 46), (440, 142, 44)):
        pygame.draw.polygon(sf, (64, 44, 110), [(ox, oy - oh // 2), (ox + 12, oy), (ox, oy + oh // 2), (ox - 12, oy)])
        pygame.draw.polygon(sf, (150, 110, 230), [(ox, oy - oh // 2), (ox + 12, oy), (ox, oy)])


_BG = dict(basement=_bg_basement, jungle=_bg_jungle, cathedral=_bg_cathedral, necropolis=_bg_necropolis,
           penthouse=_bg_penthouse, observatory=_bg_observatory)
BGS = {}


def make_bg(i, plats=None):
    A, rnd, sf = LEVELS[i], random.Random(i + 10), pygame.Surface((W, H))
    for y in range(H):
        pygame.draw.line(sf, lerp(A["sky"][0], A["sky"][1], y / FLOOR), (0, y), (W, y))
    _BG[A["bg"]](sf, rnd)
    pygame.draw.rect(sf, A["floor"], (0, FLOOR, W, H - FLOOR))
    pygame.draw.rect(sf, A["top"], (0, FLOOR, W, 3)); pygame.draw.rect(sf, dim(A["top"]), (0, FLOOR + 3, W, 1))
    for x in range(0, W, 24):
        pygame.draw.rect(sf, dim(A["floor"]), (x, FLOOR + 8 + (x // 24 % 3) * 9, 22, 1))
        pygame.draw.rect(sf, dim(A["floor"]), (x + 11, FLOOR + 4, 1, 30))
        if A.get("grass"):
            pygame.draw.rect(sf, lit(A["top"]), (x + 4, FLOOR - 2, 2, 2)); pygame.draw.rect(sf, A["top"], (x + 15, FLOOR - 1, 3, 1))
    for px, py, pw in (A["plats"] if plats is None else plats):
        box(sf, A["plat"], px, py, pw, 9); pygame.draw.rect(sf, A["top"], (px, py, pw, 2))
        pygame.draw.rect(sf, dim(A["plat"]), (px + 4, py + 9, pw - 8, 3))
    for wx in (0, W - 4):  # wall trim marks the wall-jumpable arena borders
        pygame.draw.rect(sf, dim(A["plat"]), (wx, 24, 4, FLOOR - 24))
    return sf


def get_bg(i, plats=None):
    """Cached background for theme i. Castle levels pass their own platform layout so the drawn ledges match the physics."""
    key = (i, None if plats is None else tuple(map(tuple, plats)))
    if key not in BGS:
        BGS[key] = make_bg(i, plats)
    return BGS[key]


def draw_torches(t, col=(130, 76, 24)):
    for x, y in ((70, 118), (240, 118), (410, 118)):
        pygame.draw.rect(gfx.canvas, BROWN, (x - 1, y, 3, 12)); fl = int(t * 9 + x) % 3
        pygame.draw.rect(gfx.canvas, (240, 120, 40), (x - 3, y - 8 - fl, 7, 9 + fl)); pygame.draw.rect(gfx.canvas, GOLD, (x - 1, y - 5 - fl, 3, 6 + fl))
        glow(x, y - 4, 56, col)


def draw_runes(t, col=(80, 40, 130)):
    for x, y in ((120, 110), (360, 110)):
        r = 6 + int(math.sin(t * 3 + x) * 2)
        pygame.draw.circle(gfx.canvas, (170, 120, 255), (x, y), r, 1)
        glow(x, y, 36, col)
