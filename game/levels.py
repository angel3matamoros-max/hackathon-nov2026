"""Level / area definitions and procedural backgrounds."""
import math, random
import pygame
from . import gfx
from .config import *
from .gfx import lerp, lit, dim, box, glow


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
        pygame.draw.rect(gfx.canvas, BROWN, (x - 1, y, 3, 12)); fl = int(t * 9 + x) % 3
        pygame.draw.rect(gfx.canvas, (240, 120, 40), (x - 3, y - 8 - fl, 7, 9 + fl)); pygame.draw.rect(gfx.canvas, GOLD, (x - 1, y - 5 - fl, 3, 6 + fl))
        glow(x, y - 4, 56, (130, 76, 24))


def draw_runes(t):
    for x, y in ((120, 110), (360, 110)):
        r = 6 + int(math.sin(t * 3 + x) * 2)
        pygame.draw.circle(gfx.canvas, (170, 120, 255), (x, y), r, 1)
        glow(x, y, 36, (80, 40, 130))
