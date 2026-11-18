"""Simple procedural cutscenes. Each has update(dt, motions) -> done and draw() (renders to main_cv).
IntroCard opens every level; AscendCutscene shows the heroes climbing the castle after a boss; Ending tops the tower."""
import pygame
from . import gfx
from .config import *
from .gfx import text, title_text, wrap, lerp, lit, dim, use, main_cv, blit_ent, glow, font, mid
from .levels import LEVELS, NUM_LEVELS
from .bosses import BOSSES
from .sprites import HERO

FH, TX0, TX1 = 64, 130, 350  # castle: floor height, left/right wall x
_FADE = pygame.Surface((W, H))
_FADE.fill(INK)


def fade(a):
    """Black overlay with alpha a in 0..1."""
    if a > 0:
        _FADE.set_alpha(int(255 * min(1, a)))
        gfx.canvas.blit(_FADE, (0, 0))


def envelope(t, dur, edge=0.45):
    return max(0.0, 1 - t / edge, 1 - (dur - t) / edge) if dur > 2 * edge else 0.0


class Cutscene:
    dur = 3.0

    def __init__(s):
        s.t, s.done = 0.0, False

    def update(s, dt, motions=None):
        s.t += dt
        if s.t >= s.dur: s.done = True
        return s.done

    def skip(s):
        s.done = True


def draw_tower(cam, lit_to, sky_top=(10, 8, 28), sky_bot=(60, 40, 90), current=None, screen_grad=False):
    """Castle cross-section. World y: ground at 270, floor k spans [270-FH*(k+1), 270-FH*k]. cam = world y at screen top."""
    use(main_cv)
    cv = gfx.canvas
    for y in range(0, H, 6):
        k = y / H if screen_grad else max(0.0, min(1.0, (cam + y) / (270 + FH * NUM_LEVELS)))
        pygame.draw.rect(cv, lerp(sky_top, sky_bot, k), (0, y, W, 6))
    for n in range(40):  # stars (fixed in the sky, drift with camera)
        sx, sy = (n * 97) % W, (n * 53) % (FH * NUM_LEVELS + 140) - cam * 0.3
        if 0 <= sy < H: pygame.draw.rect(cv, (220, 220, 255), (sx, int(sy), 1, 1))
    ground = 270 - cam
    pygame.draw.rect(cv, (30, 44, 36), (0, ground, W, 40))
    # roof spire above floor 6
    roof = 270 - FH * NUM_LEVELS - cam
    pygame.draw.polygon(cv, (70, 50, 110), [(TX0 - 10, roof), (240, roof - 70), (TX1 + 10, roof)])
    pygame.draw.polygon(cv, lit((70, 50, 110)), [(TX0 - 10, roof), (240, roof - 70), (240, roof)])
    pygame.draw.line(cv, STEEL, (240, roof - 70), (240, roof - 92), 2)
    pygame.draw.polygon(cv, RED, [(240, roof - 92), (258, roof - 86), (240, roof - 80)])
    for k in range(NUM_LEVELS):
        top = 270 - FH * (k + 1) - cam
        A = LEVELS[k]
        room = lerp(A["sky"][0], A["sky"][1], 0.5) if k <= lit_to else dim(dim(A["sky"][0]))
        pygame.draw.rect(cv, (62, 54, 82), (TX0 - 6, top, TX1 - TX0 + 12, FH))
        pygame.draw.rect(cv, room, (TX0, top + 4, TX1 - TX0, FH - 8))
        pygame.draw.rect(cv, A["top"] if k <= lit_to else (50, 46, 66), (TX0, top + FH - 6, TX1 - TX0, 3))  # floor slab
        for bx in range(TX0, TX1, 24):
            pygame.draw.rect(cv, dim(room), (bx + 10, top + 10, 1, FH - 22))
        if k <= lit_to: glow(TX0 + 20, top + 28, 26, (80, 60, 20)); glow(TX1 - 20, top + 28, 26, (80, 60, 20))
        for wx in (TX0 + 14, TX1 - 24):  # windows
            pygame.draw.rect(cv, (255, 220, 120) if k <= lit_to else (30, 28, 44), (wx, top + 14, 10, 18))
        # stairs zig-zag between floors
        sx0, sx1 = (TX1 - 50, TX0 + 60) if k % 2 == 0 else (TX0 + 60, TX1 - 50)
        for n in range(8):
            x = sx0 + (sx1 - sx0) * n / 8
            y = top + FH - 6 - FH * n / 8
            pygame.draw.rect(cv, (110, 100, 130), (int(x) - 5, int(y), 12, 3))
        lab = f"{k + 1}. {A['name']}"
        on = current is not None and k == current
        text(lab, TX0 - 12, top + FH // 2 - 4, GOLD if on else STEEL_D, font, right=True)


def stair_pos(frm, to, u):
    """Hero position (x, world y) for progress u in 0..1 along the stairs from floor frm to floor to."""
    k = frm
    sx0, sx1 = (TX1 - 50, TX0 + 60) if k % 2 == 0 else (TX0 + 60, TX1 - 50)
    return sx0 + (sx1 - sx0) * u, 270 - FH * k - 6 - FH * (to - frm) * u


class IntroCard(Cutscene):
    dur = 2.8

    def __init__(s, level):
        super().__init__()
        s.level = level

    def draw(s):
        use(main_cv)
        A = LEVELS[s.level]
        main_cv.fill(INK)
        for y in range(0, H, 4):
            pygame.draw.rect(main_cv, lerp(A["sky"][0], A["sky"][1], y / H * 0.8), (0, y, W, 4))
        title_text(f"LEVEL {s.level + 1}", W // 2, 56, GOLD)
        title_text(A["name"].upper(), W // 2, 100, WHITE, 2)
        for i, ln in enumerate(wrap(A["tag"], 56)):
            text(ln, W // 2, 150 + i * 12, STEEL, font, True)
        text(f"Boss: {BOSSES[A['boss']]['name']}", W // 2, 178, RED, mid, True)
        for k in range(NUM_LEVELS):  # tower minimap: current floor lit
            y = 238 - k * 6
            pygame.draw.rect(main_cv, GOLD if k == s.level else (70, 62, 96), (W // 2 - 20, y, 40, 5))
        fade(envelope(s.t, s.dur))


class AscendCutscene(Cutscene):
    dur = 5.2

    def __init__(s, frm, to, heroes):
        super().__init__()
        s.frm, s.to, s.heroes = frm, to, heroes

    def draw(s):
        t = s.t
        u = max(0.0, min(1.0, (t - 1.3) / 2.6))  # stair climb progress
        u = u * u * (3 - 2 * u)
        _, wy = stair_pos(s.frm, s.to, u)
        cam = wy - 150
        draw_tower(cam, s.frm if t < 3.6 else s.to, current=s.frm if t < 3.6 else s.to)
        for n, cls in enumerate(s.heroes):
            un = max(0.0, min(1.0, u - 0.06 * n))
            x, y = stair_pos(s.frm, s.to, un)
            if t < 1.3: x, y = TX1 - 50 + 14 * n, 270 - FH * s.frm - 6
            walking = 0 < u < 1 or t < 1.3
            blit_ent(HERO[cls][1][int(t * 10) % 8] if walking else HERO[cls][0], x, y - cam, (s.frm % 2 == 0) == (un > 0) if u > 0 else True)
        if t < 1.4:
            title_text("BOSS DEFEATED!", W // 2, 20, GOLD, 2)
        elif t > 3.4:
            text(f"Floor {s.to + 1}: {LEVELS[s.to]['name']}", W - 8, 12, WHITE, mid, right=True)
        fade(envelope(t, s.dur))


class Ending(Cutscene):
    dur = 6.0

    def __init__(s, heroes):
        super().__init__()
        s.heroes = heroes

    def draw(s):
        use(main_cv)
        t = s.t
        cam = 270 - FH * NUM_LEVELS - 150
        draw_tower(cam, NUM_LEVELS, (40, 20, 70), (250, 140, 80), current=None, screen_grad=True)
        for n, cls in enumerate(s.heroes):
            blit_ent(HERO[cls][0], 226 + n * 26, 270 - FH * NUM_LEVELS - 6 - cam, n == 1)
        title_text("THE CASTLE IS CONQUERED", W // 2, 16, GOLD, 2)
        if t > 2.5: text("The sun rises over the summit...", W // 2, 46, WHITE, mid, True)
        fade(envelope(t, s.dur))

