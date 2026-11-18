"""Destructible arena props used by boss mechanics: gravestones, phylactery crystals, aegis orbs and crates.

A Prop quacks like an enemy for hit detection (x, y = bottom centre, d['w'], d['h']) so slashes, skills and projectiles reuse `overlap`."""
import math
import pygame
from . import gfx
from .config import *
from .gfx import box, glow, bar

SIZE = dict(tomb=(14, 22), crystal=(16, 34), orb=(12, 12), crate=(24, 24))
RAISE_TIME = 4.0  # seconds before a gravestone releases its zombie


class Prop:
    def __init__(s, kind, x, y, hp, owner=None, **data):
        s.kind, s.x, s.y, s.hp, s.maxhp, s.owner, s.flash, s.t, s.data = kind, float(x), float(y), hp, hp, owner, 0.0, 0.0, data
        s.d = dict(w=SIZE[kind][0], h=SIZE[kind][1])
        s.state = "rest"  # lets the scripted bots treat a prop like a (never-telegraphing) foe
        if kind == "tomb": s.t = RAISE_TIME
        if kind == "orb": s.ang = data.get("ang", 0.0)

    def update(s, dt, a):
        s.flash = max(0.0, s.flash - dt)
        if s.kind == "tomb":
            s.t -= dt
            if s.t <= 0 and s.hp > 0:  # nobody broke it in time: the dead rise
                a.burst(s.x, s.y - 10, (140, 200, 120), 14, 90)
                kind = s.owner.cfg["minion"] if s.owner else "zombie"
                if a.count(kind) < 4: a.spawn(kind, x=s.x, dscale=getattr(s.owner, "dscale", 1.0))  # same cap as the boss's own summons
                s.hp = 0; s.data["risen"] = True
        elif s.kind == "orb" and s.owner is not None:
            s.ang += dt * 1.9
            s.x = s.owner.x + math.cos(s.ang) * 46
            s.y = s.owner.y - s.owner.d["h"] * 0.55 + math.sin(s.ang) * 18 + s.d["h"] / 2

    def draw(s, a):
        c, x, y = gfx.canvas, int(s.x), int(s.y)
        fl = s.flash > 0
        if s.kind == "tomb":
            col = (230, 230, 230) if fl else (120, 126, 120)
            pygame.draw.rect(c, INK, (x - 8, y - 22, 16, 22)); pygame.draw.circle(c, INK, (x, y - 22), 8)
            pygame.draw.rect(c, col, (x - 6, y - 20, 12, 20)); pygame.draw.circle(c, col, (x, y - 20), 6)
            pygame.draw.rect(c, (60, 70, 60), (x - 1, y - 18, 2, 8)); pygame.draw.rect(c, (60, 70, 60), (x - 4, y - 15, 8, 2))
            bar(x - 8, y - 29, 16, 3, max(0.0, s.t / RAISE_TIME), (140, 200, 120))  # time until the dead rise
        elif s.kind == "crystal":
            col = (255, 255, 255) if fl else (110, 240, 150)
            glow(x, y - 17, 26, (20, 90, 50))
            pts = [(x, y - 34), (x + 8, y - 22), (x + 5, y), (x - 5, y), (x - 8, y - 22)]
            pygame.draw.polygon(c, INK, [(px + (1 if px > x else -1 if px < x else 0), py) for px, py in pts], 0)
            pygame.draw.polygon(c, col, pts); pygame.draw.line(c, WHITE, (x - 2, y - 28), (x - 2, y - 10), 1)
            bar(x - 9, y - 41, 18, 3, s.hp / s.maxhp, (110, 240, 150))
        elif s.kind == "orb":
            glow(x, y - 6, 14, (130, 110, 40))
            pygame.draw.circle(c, INK, (x, y - 6), 7); pygame.draw.circle(c, WHITE if fl else GOLD, (x, y - 6), 5); pygame.draw.circle(c, WHITE, (x - 1, y - 7), 2)
        elif s.kind == "crate":
            col = (255, 255, 255) if fl else BROWN
            box(c, BROWN_D, x - 12, y - 24, 24, 24); pygame.draw.rect(c, col, (x - 10, y - 22, 20, 20))
            pygame.draw.line(c, BROWN_D, (x - 10, y - 22), (x + 9, y - 3), 2); pygame.draw.line(c, BROWN_D, (x + 9, y - 22), (x - 10, y - 3), 2)
            pygame.draw.rect(c, GOLD, (x - 10, y - 22, 20, 20), 1)
            bar(x - 10, y - 30, 20, 3, s.hp / s.maxhp, GOLD)
