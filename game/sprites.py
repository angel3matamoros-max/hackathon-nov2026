"""Procedural pixel-art sprites."""
import math
import pygame
from .config import *
from .gfx import box, outlined, lit, dim
from .classes import CLASSES
from .sprites_extra import build_extra


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
ENEMY.update(build_extra())
CORPSE = {k: (pygame.transform.rotate(v[0], 90) if v[0].get_height() >= v[0].get_width() else v[0]) for k, v in ENEMY.items()}

MIMIC = pygame.Surface((16, 14), pygame.SRCALPHA)
box(MIMIC, BROWN, 0, 6, 16, 8); box(MIMIC, BROWN, 0, 0, 16, 4); pygame.draw.rect(MIMIC, INK, (1, 4, 14, 3))
for _x in (2, 6, 10):
    pygame.draw.rect(MIMIC, WHITE, (_x, 4, 2, 3))
pygame.draw.rect(MIMIC, RED, (3, 1, 2, 2)); pygame.draw.rect(MIMIC, RED, (11, 1, 2, 2))
MIMIC = outlined(MIMIC)
