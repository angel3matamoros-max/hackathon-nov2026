"""Side-scrolling support for the Mario-style levels: floor segments with pits, camera maths, and ground / platform / scenery drawing.

World coordinates: x runs 0..length. The screen shows [camx, camx + W]. All gameplay code works in world coordinates; the arena draws
the world onto a wide surface and copies the camera window to the screen, so none of the draw code needs a camera offset."""
import pygame
from .config import *
from .gfx import lit, dim, box

WORLD_W = 2600  # widest level the world surface supports


def floor_segments(length, pits):
    """Solid floor pieces (x, width) of a level `length` px long with pits [(x0, x1), ...]."""
    segs, x = [], 0
    for p0, p1 in sorted(pits):
        if p0 > x: segs.append((x, p0 - x))
        x = max(x, p1)
    if x < length: segs.append((x, length - x))
    return segs


def make_platforms(length, pits, plats):
    """Platform list used by physics (`land`): the floor pieces plus the floating platforms."""
    return [(x, FLOOR, w) for x, w in floor_segments(length, pits)] + list(plats)


def camera_target(lead_x, length, lock_x0=None):
    """Where the camera wants to be: the leading hero sits about 55% across the screen. Clamped to the level; fixed when the boss gate is locked."""
    if lock_x0 is not None: return float(lock_x0)
    return float(max(0, min(length - W, lead_x - W * 0.55)))


def pit_ahead(pits, x, direction, reach=46):
    """True if a pit starts within `reach` px in front of x (for the bots / CPU ally to hop)."""
    for p0, p1 in pits:
        if direction > 0 and 0 <= p0 - x <= reach: return True
        if direction < 0 and 0 <= x - p1 <= reach: return True
    return False


def over_pit(pits, x):
    return any(p0 + 4 < x < p1 - 4 for p0, p1 in pits)


def draw_scenery(canvas, far, camx, parallax=0.5):
    """Tile the 480-wide scenery surface (no floor, no platforms) across the visible window, scrolling at `parallax` of the camera speed."""
    off = camx * parallax
    k0 = int(off // W)
    for k in range(k0, k0 + 3):
        x = int(k * W - off + camx)
        if camx - W <= x <= camx + W: canvas.blit(far, (x, 0))


def draw_ground(canvas, A, length, pits, plats, camx):
    """Floor with pits plus platforms, only the part inside the camera window [camx, camx + W]."""
    x0, x1 = int(camx) - 4, int(camx) + W + 4
    floor, top = A["floor"], A["top"]
    for sx, sw in floor_segments(length, pits):
        a, b = max(sx, x0), min(sx + sw, x1)
        if b <= a: continue
        pygame.draw.rect(canvas, floor, (a, FLOOR, b - a, H - FLOOR))
        pygame.draw.rect(canvas, top, (a, FLOOR, b - a, 3)); pygame.draw.rect(canvas, dim(top), (a, FLOOR + 3, b - a, 1))
        for x in range(a - a % 24, b, 24):
            pygame.draw.rect(canvas, dim(floor), (x, FLOOR + 8 + (x // 24 % 3) * 9, 22, 1))
            pygame.draw.rect(canvas, dim(floor), (x + 11, FLOOR + 4, 1, 30))
            if A.get("grass") and a <= x + 4 < b: pygame.draw.rect(canvas, lit(top), (x + 4, FLOOR - 2, 2, 2)); pygame.draw.rect(canvas, top, (x + 15, FLOOR - 1, 3, 1))
        for ex in (sx, sx + sw - 4):  # crumbling pit edges
            if a <= ex <= b and (ex != 0) and ex != length - 4: pygame.draw.rect(canvas, dim(top), (ex, FLOOR, 4, H - FLOOR))
    for p0, p1 in pits:
        if p1 < x0 or p0 > x1: continue
        pygame.draw.rect(canvas, (6, 4, 12), (p0, FLOOR, p1 - p0, H - FLOOR))
        for sxp in range(p0 + 3, p1 - 3, 8): pygame.draw.polygon(canvas, (90, 90, 110), [(sxp, H), (sxp + 3, H - 9), (sxp + 6, H)])  # spikes far below
    for px, py, pw in plats:
        if px + pw < x0 or px > x1: continue
        box(canvas, A["plat"], px, py, pw, 9); pygame.draw.rect(canvas, A["top"], (px, py, pw, 2))
        pygame.draw.rect(canvas, dim(A["plat"]), (px + 4, py + 9, pw - 8, 3))
