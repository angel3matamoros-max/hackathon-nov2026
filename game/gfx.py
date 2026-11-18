"""Surfaces, fonts and pixel-art drawing helpers. `canvas` is the current draw target (see use())."""
import pygame
from .config import *

pygame.init()
main_cv = pygame.Surface((W, H))
world = pygame.Surface((W, H))
canvas = main_cv
font, mid, big = pygame.font.Font(None, 17), pygame.font.Font(None, 23), pygame.font.Font(None, 34)


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
    if tint:  # positive components brighten, negative ones darken (pygame rejects negative colours, so split them)
        fr = fr.copy()
        if any(v > 0 for v in tint): fr.fill(tuple(max(0, v) for v in tint) + (0,), special_flags=pygame.BLEND_RGB_ADD)
        if any(v < 0 for v in tint): fr.fill(tuple(max(0, -v) for v in tint) + (0,), special_flags=pygame.BLEND_RGB_SUB)
    canvas.blit(fr, (int(x - fr.get_width() / 2), int(y - fr.get_height() + 1)))



def make_vignette():
    v = pygame.Surface((W, H), pygame.SRCALPHA)
    for k in range(24):
        pygame.draw.rect(v, (0, 0, 0, int(90 * (1 - k / 24) ** 2)), (k, k, W - 2 * k, H - 2 * k), 1)
    return v


VIGNETTE, DIM = make_vignette(), pygame.Surface((W, H), pygame.SRCALPHA)
DIM.fill((0, 0, 0, 150))
