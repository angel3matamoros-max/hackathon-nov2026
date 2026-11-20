"""Surfaces, fonts and pixel-art drawing helpers. `canvas` is the current draw target (see use())."""
import re
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


def fit_lines(s, width, n=6):
    """Word-wrap `s` so no line is wider than `width` px (measured with the UI font), at most `n` lines."""
    out, line = [], ""
    for w in s.split():
        t = (line + " " + w).strip()
        if font.size(t)[0] <= width or not line: line = t
        else: out.append(line); line = w
    if line: out.append(line)
    return out[:n]


# ---- PS2 button glyphs: text() draws a token like "{cross}" as a little button shape instead of the letters
GLYPH_W = 10
TOKEN = re.compile(r"\{(\w+)\}")
tiny = pygame.font.Font(None, 12)
BTN_COL = dict(circle=(230, 70, 80), cross=(110, 150, 240), square=(220, 120, 210), triangle=(90, 210, 150))


def glyph(name, x, y):
    """Draw one PS2 button (8x8 box at x, y). Unknown names draw as a small labelled chip."""
    if name in BTN_COL:
        c = BTN_COL[name]
        if name == "circle": pygame.draw.circle(canvas, c, (x + 4, y + 4), 4, 1)
        elif name == "cross": pygame.draw.line(canvas, c, (x + 1, y + 1), (x + 7, y + 7), 2); pygame.draw.line(canvas, c, (x + 7, y + 1), (x + 1, y + 7), 2)
        elif name == "square": pygame.draw.rect(canvas, c, (x + 1, y + 1, 6, 6), 1)
        else: pygame.draw.polygon(canvas, c, [(x + 4, y + 1), (x + 7, y + 7), (x + 1, y + 7)], 1)
    elif name in ("up", "down", "left", "right"):
        pts = dict(up=[(x + 4, y + 1), (x + 7, y + 6), (x + 1, y + 6)], down=[(x + 4, y + 7), (x + 7, y + 2), (x + 1, y + 2)],
                   left=[(x + 1, y + 4), (x + 6, y + 1), (x + 6, y + 7)], right=[(x + 7, y + 4), (x + 2, y + 1), (x + 2, y + 7)])[name]
        pygame.draw.polygon(canvas, WHITE, pts)
    else:
        pygame.draw.rect(canvas, STEEL_D, (x, y, GLYPH_W - 2, 8), 1, border_radius=2)
        lab = tiny.render({"start": "ST", "select": "SE"}.get(name, name.upper()[:2]), False, WHITE)
        canvas.blit(lab, (x + (GLYPH_W - 2 - lab.get_width()) // 2, y + 1))


def _rich(s, x, y, color, f, center, right):
    parts = TOKEN.split(s)  # text, token, text, token, ...
    w = sum(f.size(p)[0] if i % 2 == 0 else GLYPH_W for i, p in enumerate(parts))
    x -= w // 2 if center else (w if right else 0)
    gy = y + (f.get_height() - 8) // 2
    for i, p in enumerate(parts):
        if i % 2:
            glyph(p, x, gy); x += GLYPH_W
        elif p:
            img, sh = f.render(p, False, color), f.render(p, False, INK)
            canvas.blit(sh, (x + 1, y + 1)); canvas.blit(img, (x, y)); x += img.get_width()


def text(s, x, y, color=WHITE, f=font, center=False, right=False):
    if "{" in s: return _rich(s, x, y, color, f, center, right)
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
