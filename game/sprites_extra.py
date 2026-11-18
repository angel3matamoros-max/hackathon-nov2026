"""Procedural sprites for the castle-campaign enemies and bosses. All sprites FACE RIGHT (like the heroes)."""
import math
import pygame
from .config import *
from .gfx import box, outlined, dim, lit

YEL = (255, 220, 60)
PINK = (255, 170, 190)

# kind -> palette. keys: skin/fur, body, legs, accent
PAL = {
    "zombie": dict(skin=(112, 150, 104), body=(96, 84, 120), legs=(72, 64, 52), hair=(50, 40, 36)),
    "gunman": dict(skin=SKIN, body=(36, 36, 50), legs=(30, 30, 42), hat=(24, 24, 32)),
    "lich": dict(skin=BONE, body=(60, 34, 90), legs=(40, 24, 60), trim=(110, 230, 130)),
    "knight": dict(skin=(228, 228, 240), body=(228, 228, 240), legs=(190, 190, 205), trim=GOLD),
    "wolfman": dict(skin=(120, 120, 135), body=(110, 70, 40), legs=(80, 80, 95), dark=(80, 80, 95)),
    "catman": dict(skin=(226, 150, 70), body=(226, 150, 70), legs=(190, 118, 52), dark=(150, 80, 30), cream=(250, 230, 200)),
    "bunny": dict(skin=(240, 230, 235), body=(90, 140, 90), legs=(220, 208, 214)),
    "alien": dict(skin=(130, 205, 130), body=(30, 30, 42), legs=(24, 24, 34)),
}


def humanoid_raw(i, kind, boss=None):
    """One walk-cycle frame (i in 0..3) of a humanoid, un-outlined. `boss` adds boss-only accessories."""
    P = PAL[kind]
    oy = 7 if (boss or kind == "bunny") else (4 if kind == "alien" else 0)
    s = pygame.Surface((30, 28 + oy), pygame.SRCALPHA)
    sw = math.sin(i / 4 * 2 * math.pi)
    bob, lx, ax = i % 2, round(sw * 3), round(-sw * 2)

    def B(c, x, y, w, h):
        box(s, c, x, y + oy, w, h)

    # legs (alien hovers on rocket boots instead)
    for x in (8 - lx, 14 + lx):
        if kind == "alien":
            B(P["legs"], x, 20 + bob, 3, 4); B((255, 170, 50), x, 24 + bob, 3, 3 + (i % 2)); B(YEL, x + 1, 24 + bob, 1, 2)
        else:
            B(P["legs"], x, 20 + bob, 3, 8 - bob); B(dim(P["legs"]), x, 25, 5, 3)

    if kind == "zombie":
        B(P["body"], 8, 11 + bob, 9, 9); B(dim(P["body"]), 9, 16 + bob, 3, 4); B(P["skin"], 10, 12 + bob, 2, 3)
        B(P["skin"], 8, 3 + bob, 9, 8); B(P["hair"], 8, 2 + bob, 9, 2); B(P["hair"], 8, 4 + bob, 2, 3)
        B(WHITE, 11, 6 + bob, 2, 2); B(WHITE, 14, 6 + bob, 2, 2); B(RED, 12, 7 + bob, 1, 1); B(RED, 15, 7 + bob, 1, 1); B(INK, 11, 9 + bob, 4, 1)
        B(P["skin"], 16, 12 + bob, 8, 3); B(P["skin"], 16, 16 + bob, 6, 3)  # arms stretched out
        if boss:
            B(BROWN, 21 + ax, 0 + bob, 2, 26); B(STEEL, 19 + ax, 22 + bob, 6, 5); B((50, 50, 60), 7, 0 + bob, 11, 3); B((50, 50, 60), 9, -3, 7, 3)
    elif kind == "gunman":
        B(P["body"], 8, 11 + bob, 9, 10); B(WHITE, 11, 11 + bob, 3, 6); B(RED, 12, 12 + bob, 1, 5)
        B(P["skin"], 9, 4 + bob, 8, 7); B(P["hat"], 7, 3 + bob, 12, 2); B(P["hat"], 9, 0 + bob, 8, 4); B(RED, 9, 3 + bob, 8, 1)
        B(INK, 14, 7 + bob, 1, 1); B((200, 120, 60), 16, 9 + bob, 3, 1); B((255, 90, 40), 19, 9 + bob, 1, 1)
        B(P["body"], 15, 13 + bob, 4, 3); B((60, 60, 70), 18, 13 + bob, 7, 3); B((60, 60, 70), 19, 16 + bob, 2, 3)
        if boss:
            B(WHITE, 8, 11 + bob, 9, 10); B(RED, 12, 12 + bob, 1, 5); B(WHITE, 7, 3 + bob, 12, 2); B(WHITE, 9, 0 + bob, 8, 4)
            B((90, 90, 100), 20, 16 + bob, 5, 6); B((60, 60, 70), 18, 13 + bob, 11, 3)
    elif kind == "lich":
        B(P["body"], 6, 12 + bob, 14, 16); B(P["trim"], 6, 26, 14, 2); B(dim(P["body"]), 11, 14 + bob, 4, 12)
        B(P["skin"], 8, 2 + bob, 10, 9); B(INK, 10, 5 + bob, 3, 3); B(INK, 14, 5 + bob, 3, 3)
        B(P["trim"], 11, 6 + bob, 1, 1); B(P["trim"], 15, 6 + bob, 1, 1); B(dim(BONE), 9, 10 + bob, 8, 2)
        B(P["body"], 7, 1 + bob, 12, 2); B(GOLD, 8, -1 + bob, 2, 3); B(GOLD, 16, -1 + bob, 2, 3)
        B(P["body"], 17 + ax, 13 + bob, 3, 6); B(BROWN, 21 + ax, 3 + bob, 2, 24)
        B(P["trim"], 19 + ax, -1 + bob, 6, 5); B(WHITE, 21 + ax, 1 + bob, 2, 2)
        if boss:
            B(BONE, 5, -3, 2, 5); B(BONE, 19, -3, 2, 5); B((120, 60, 170), 3, 12 + bob, 3, 16)
    elif kind == "knight":
        B(P["body"], 7, 11 + bob, 11, 10); B(WHITE, 10, 11 + bob, 5, 10); B(GOLD, 12, 12 + bob, 1, 7); B(GOLD, 10, 14 + bob, 5, 1); B(GOLD, 7, 19 + bob, 11, 2)
        B(P["body"], 8, 3 + bob, 9, 8); B(INK, 12, 6 + bob, 5, 2); B(GOLD, 8, 3 + bob, 9, 1); B(GOLD, 11, 0 + bob, 3, 3)
        B(STEEL, 2, 12 + bob, 6, 12); B(GOLD, 4, 14 + bob, 2, 8); B(GOLD, 2, 17 + bob, 6, 2)  # shield
        B(P["body"], 16 + ax, 13 + bob, 3, 5); B(BLADE, 19 + ax, 4 + bob, 2, 14); B(GOLD, 17 + ax, 17 + bob, 6, 2); B(BROWN, 19 + ax, 19 + bob, 2, 3)
        if boss:
            pygame.draw.ellipse(s, GOLD, (7, 0, 12, 5), 1); B((250, 250, 255), 1, 11 + bob, 5, 15); B(GOLD, 1, 11 + bob, 5, 1)
    elif kind == "wolfman":
        B(P["legs"], 3, 16 + bob, 5, 3)  # tail
        B(P["body"], 8, 11 + bob, 9, 9); B(P["skin"], 10, 11 + bob, 3, 5)
        B(P["skin"], 8, 3 + bob, 9, 8); B(P["skin"], 15, 6 + bob, 5, 4); B(INK, 19, 6 + bob, 2, 2); B(WHITE, 16, 10 + bob, 1, 2)
        B(P["dark"], 8, 0 + bob, 3, 4); B(P["dark"], 14, 0 + bob, 3, 4); B(YEL, 13, 5 + bob, 2, 1)
        B(P["skin"], 16 + ax, 12 + bob, 3, 6); B(WHITE, 19 + ax, 17 + bob, 1, 3); B(WHITE, 21 + ax, 16 + bob, 1, 3)
        if boss:
            B(GOLD, 8, -3 + bob, 9, 2); B(GOLD, 8, -5 + bob, 2, 3); B(GOLD, 12, -5 + bob, 2, 3); B(GOLD, 15, -5 + bob, 2, 3); B(RED_D, 3, 11 + bob, 5, 15)
    elif kind == "catman":
        B(P["skin"], 2, 12 + bob, 2, 10); B(P["skin"], 3, 10 + bob, 2, 3); B(P["dark"], 3, 10 + bob, 2, 1)  # tail
        B(P["body"], 8, 11 + bob, 9, 9); B(P["dark"], 9, 13 + bob, 7, 1); B(P["dark"], 9, 16 + bob, 7, 1); B(P["cream"], 12, 12 + bob, 3, 6)
        B(P["skin"], 8, 3 + bob, 9, 8); B(P["skin"], 8, 0 + bob, 3, 4); B(P["skin"], 14, 0 + bob, 3, 4); B(PINK, 9, 1 + bob, 1, 2); B(PINK, 15, 1 + bob, 1, 2)
        B((120, 255, 120), 12, 6 + bob, 2, 2); B(INK, 13, 6 + bob, 1, 2); B(PINK, 16, 8 + bob, 1, 1); B(WHITE, 17, 9 + bob, 4, 1); B(WHITE, 17, 10 + bob, 3, 1)
        B(P["skin"], 16 + ax, 12 + bob, 3, 6); B(WHITE, 19 + ax, 17 + bob, 1, 3); B(WHITE, 21 + ax, 16 + bob, 1, 3)
    elif kind == "bunny":
        B(P["skin"], 9, -6, 3, 9); B(P["skin"], 14, -6, 3, 9); B(PINK, 10, -4, 1, 6); B(PINK, 15, -4, 1, 6)
        B(P["skin"], 8, 3 + bob, 9, 8); B(RED, 13, 6 + bob, 1, 2); B(PINK, 15, 8 + bob, 2, 1); B(WHITE, 14, 10 + bob, 2, 2)
        B(P["body"], 8, 11 + bob, 9, 9); B(P["skin"], 10, 11 + bob, 3, 3)
        B(P["skin"], 16 + ax, 12 + bob, 3, 5); B((240, 140, 40), 18 + ax, 12 + bob, 3, 10); B(GREEN, 19 + ax, 9 + bob, 1, 3)  # carrot club
    elif kind == "alien":
        B(P["body"], 7, 11 + bob, 11, 10); B(WHITE, 11, 11 + bob, 3, 4); B(STEEL, 9, 14 + bob, 2, 2); B(CYAN, 14, 16 + bob, 2, 1)
        B(P["skin"], 6, 1 + bob, 14, 10); B(P["skin"], 9, -3, 1, 5); B(P["skin"], 16, -3, 1, 5); B(RED, 8, -4, 3, 2); B(RED, 15, -4, 3, 2)
        B(INK, 8, 5 + bob, 4, 4); B(INK, 14, 5 + bob, 4, 4); B(WHITE, 9, 5 + bob, 1, 1); B(WHITE, 15, 5 + bob, 1, 1); B(INK, 11, 9 + bob, 5, 1)
        B(P["body"], 16 + ax, 13 + bob, 3, 4); B(CYAN, 19 + ax, 13 + bob, 6, 3); B(WHITE, 23 + ax, 13 + bob, 2, 3)
        if boss:
            B((70, 40, 110), 3, 11 + bob, 4, 14); B(STEEL, 2, 4 + bob, 3, 10); B(RED, 2, 2 + bob, 3, 3)  # cape + jetpack rocket
    return s


def hum(i, kind, boss=None, k=1.0):
    raw = humanoid_raw(i, kind, boss)
    if k != 1.0:
        raw = pygame.transform.scale(raw, (round(raw.get_width() * k), round(raw.get_height() * k)))
    return outlined(raw)


def wolf_frame(i):
    """Plain wolf: low quadruped, 4-frame run cycle."""
    s = pygame.Surface((36, 20), pygame.SRCALPHA)
    sw = math.sin(i / 4 * 2 * math.pi)
    lx, bob = round(sw * 3), i % 2
    fur, dk = (140, 140, 152), (88, 88, 102)
    for x, d in ((9, lx), (13, -lx), (21, -lx), (25, lx)):
        box(s, dk, x + d, 14, 3, 6 - (1 if d > 0 else 0))
    box(s, fur, 6, 6 + bob, 20, 9); box(s, lit(fur), 8, 6 + bob, 16, 2); box(s, (200, 200, 210), 10, 12 + bob, 12, 3)
    box(s, fur, 24, 3 + bob, 9, 8); box(s, fur, 31, 6 + bob, 5, 4); box(s, INK, 35, 6 + bob, 1, 2); box(s, WHITE, 31, 10 + bob, 1, 2)
    box(s, dk, 25, 0 + bob, 3, 4); box(s, dk, 30, 0 + bob, 3, 4); box(s, YEL, 29, 5 + bob, 2, 1)
    box(s, dk, 1, 4 + bob + (i % 2), 6, 3); box(s, fur, 4, 5 + bob, 4, 3)
    return outlined(s)


def drone_frame(i):
    s = pygame.Surface((22, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (140, 150, 172), (1, 6, 20, 7)); pygame.draw.ellipse(s, (96, 108, 132), (1, 9, 20, 4))
    pygame.draw.ellipse(s, (110, 230, 240), (6, 1, 10, 8)); pygame.draw.ellipse(s, WHITE, (8, 2, 3, 3))
    for x in (4, 10, 16):
        pygame.draw.rect(s, RED if (x // 6 + i) % 2 else YEL, (x, 10, 2, 2))
    return outlined(s)


BOSS_K = 2.5  # boss sprites are the humanoid frame scaled 2.5x, then decorated at full resolution
PAD = 14  # side / top margin around a boss sprite (cape, halo, horns)
PADB = 12  # bottom margin (robe tail, saucer); the arena draws bosses PADB lower so the feet stand on the floor


def boss_sprite(src, i, deco):
    """Big boss frame: scaled humanoid with a back layer (cape / mane / saucer) and a front layer (crown / glow) drawn at full resolution."""
    raw = humanoid_raw(i, src, "boss")
    w, h = round(raw.get_width() * BOSS_K), round(raw.get_height() * BOSS_K)
    body = pygame.transform.scale(raw, (w, h))
    out = pygame.Surface((w + 2 * PAD, h + PAD + PADB), pygame.SRCALPHA)
    bob = i % 2
    deco(out, w, h, i, bob, "back")
    out.blit(body, (PAD, PAD))
    deco(out, w, h, i, bob, "front")
    return outlined(out)


def _gravekeeper(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        pygame.draw.polygon(s, (52, 66, 56), [(cx - 6, PAD + h * 0.3), (cx - 44, PAD + h + 6), (cx - 26 + (i % 2) * 3, PAD + h - 4), (cx - 12, PAD + h + 8), (cx + 10, PAD + h - 3)])
        pygame.draw.polygon(s, (34, 44, 38), [(cx - 6, PAD + h * 0.3), (cx - 44, PAD + h + 6), (cx - 38, PAD + h - 14)])
    else:
        for ex in (cx - 9, cx + 2): pygame.draw.rect(s, (120, 255, 130), (ex, PAD + 14 + bob * 2, 5, 4))
        for k in range(3): pygame.draw.line(s, STEEL_D, (cx - 4 + k * 4, PAD + h * 0.55), (cx - 8 + k * 5, PAD + h * 0.55 + 12), 2)  # chains


def _beastlord(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        for k in range(7):  # mane
            a = math.radians(-160 + k * 23)
            pygame.draw.polygon(s, (160, 100, 56), [(cx - 6, PAD + 22), (cx - 6 + math.cos(a) * 34, PAD + 22 + math.sin(a) * 30 - 6), (cx - 6 + math.cos(a + .35) * 22, PAD + 22 + math.sin(a + .35) * 20)])
    else:
        pygame.draw.polygon(s, (190, 190, 200), [(cx - 16, PAD + 8), (cx - 22, PAD - 8), (cx - 10, PAD + 2)])
        pygame.draw.polygon(s, (190, 190, 200), [(cx + 10, PAD + 8), (cx + 18, PAD - 8), (cx + 4, PAD + 2)])  # horns
        pygame.draw.rect(s, RED, (cx - 2, PAD + 30, 3, 10)); pygame.draw.rect(s, RED, (cx + 5, PAD + 32, 3, 8))  # war paint


def _paladin(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        pygame.draw.polygon(s, (170, 36, 56), [(cx - 10, PAD + h * 0.28), (cx - 42, PAD + h + 4), (cx - 28 + (i % 2) * 2, PAD + h - 2), (cx - 4, PAD + h + 6)])
        pygame.draw.ellipse(s, GOLD, (cx - 22, PAD - 12, 44, 14), 2)  # halo
    else:
        pygame.draw.rect(s, GOLD, (cx - 24, PAD + h * 0.34, 12, 6)); pygame.draw.rect(s, GOLD, (cx + 6, PAD + h * 0.34, 12, 6))  # pauldrons


def _archlich(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        for k in range(5):  # spectral robe tail
            pygame.draw.polygon(s, (90 + k * 6, 50, 140), [(cx - 24 + k * 12, PAD + h - 14), (cx - 18 + k * 12, PAD + h + 10 + ((i + k) % 2) * 4), (cx - 12 + k * 12, PAD + h - 14)])
    else:
        pygame.draw.circle(s, (30, 120, 70), (cx - 2, int(PAD + h * 0.5)), 9)
        pygame.draw.circle(s, INK, (cx - 2, int(PAD + h * 0.5)), 7); pygame.draw.circle(s, (110, 240, 150), (cx - 2, int(PAD + h * 0.5)), 5); pygame.draw.circle(s, WHITE, (cx - 3, int(PAD + h * 0.5) - 1), 2)


def _don(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        pygame.draw.polygon(s, (28, 28, 38), [(cx - 12, PAD + h * 0.32), (cx - 36, PAD + h), (cx - 8, PAD + h - 8)])
    else:
        pygame.draw.rect(s, GOLD, (cx - 8, PAD + h * 0.36, 16, 3)); pygame.draw.rect(s, GOLD, (cx - 1, PAD + h * 0.36, 3, 12))  # gold chain + dollar bar
        pygame.draw.rect(s, (255, 150, 60), (cx + 15, PAD + 26, 8, 3)); pygame.draw.rect(s, (255, 90, 40), (cx + 22, PAD + 26, 3, 3))  # cigar


def _tycoon(s, w, h, i, bob, layer):
    cx = PAD + w // 2
    if layer == "back":
        pygame.draw.ellipse(s, (96, 108, 132), (cx - 40, PAD + h - 12, 80, 22)); pygame.draw.ellipse(s, (140, 150, 172), (cx - 40, PAD + h - 16, 80, 16))
        for k in range(5): pygame.draw.rect(s, RED if (k + i) % 2 else YEL, (cx - 32 + k * 15, PAD + h - 1, 4, 4))
    else:
        pygame.draw.circle(s, (110, 230, 240), (cx + 2, PAD + 4), 10, 2)  # helmet glint
        pygame.draw.line(s, STEEL, (cx - 16, PAD - 2), (cx - 22, PAD - 12), 2); pygame.draw.circle(s, RED, (cx - 22, PAD - 12), 3)  # antenna


BOSS_DECO = dict(gravekeeper=("zombie", _gravekeeper), beastlord=("wolfman", _beastlord), paladin=("knight", _paladin),
                 archlich=("lich", _archlich), don=("gunman", _don), tycoon=("alien", _tycoon))


def build_extra():
    n = 4
    e = {}
    for kind in ("zombie", "gunman", "lich", "knight", "wolfman", "catman", "bunny", "alien"):
        e[(kind, 0)] = [hum(i, kind) for i in range(n)]
    e[("wolf", 0)] = [wolf_frame(i) for i in range(n)]
    e[("drone", 0)] = [drone_frame(i) for i in range(2)]
    for boss, (src, deco) in BOSS_DECO.items():
        e[(boss, 0)] = [boss_sprite(src, i, deco) for i in range(n)]
    return e
