"""Enemy entity."""
import math, random
from .config import *
from .player import land


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
