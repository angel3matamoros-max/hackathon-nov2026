"""Enemy entity. Behaviour is data-driven via ESTATS keys:
   hop=(vy, t_lo, t_hi)   hops instead of walking (moves only while airborne)
   lunge=(range, speed, dur)  telegraphed dash attack            fly=True   hovers at head height
   ranged=dict(keep, shot, dmg, cd, speed)  keeps distance and shoots   summon=(kind, cap, cooldown)
   shield=True  frontal hits reduced unless it is attacking/stunned     dodge=cooldown  sidesteps the first hit
"""
import math, random
from .config import *
from .player import land

ESTATS = {
    # --- original roster
    "skeleton": dict(hp=40, dmg=10, spd=38, rng=24, wind=.55, w=12, h=28),
    "slime": dict(hp=28, dmg=8, spd=34, rng=18, wind=.45, w=16, h=12, hop=(190, .7, 1.3)),
    "bat": dict(hp=18, dmg=7, spd=75, rng=18, wind=.35, w=16, h=14, fly=True),
    "brute": dict(hp=110, dmg=18, spd=26, rng=34, wind=.8, w=26, h=36),
    "dummy": dict(hp=9999, dmg=0, spd=0, rng=0, wind=9, w=14, h=30),
    # --- castle campaign roster
    "zombie": dict(hp=34, dmg=7, spd=22, rng=22, wind=.7, w=14, h=28),
    "wolf": dict(hp=30, dmg=11, spd=58, rng=22, wind=.4, w=26, h=16, lunge=(85, 260, .26)),
    "bunny": dict(hp=30, dmg=9, spd=70, rng=20, wind=.4, w=14, h=26, hop=(300, .8, 1.5)),
    "wolfman": dict(hp=52, dmg=13, spd=44, rng=26, wind=.5, w=14, h=30, lunge=(60, 220, .2)),
    "catman": dict(hp=38, dmg=11, spd=56, rng=22, wind=.4, w=13, h=28, lunge=(70, 260, .22), dodge=3.0, climb=True),
    "knight": dict(hp=90, dmg=16, spd=28, rng=28, wind=.7, w=15, h=31, shield=True),
    "lich": dict(hp=55, dmg=0, spd=30, rng=0, wind=.7, w=14, h=30, ranged=dict(keep=120, shot="soul", dmg=12, cd=2.6, speed=120),
                 summon=("skeleton", 2, 7.0)),
    "gunman": dict(hp=45, dmg=0, spd=40, rng=0, wind=.5, w=13, h=29, ranged=dict(keep=150, shot="bullet", dmg=11, cd=1.9, speed=260)),
    "alien": dict(hp=70, dmg=0, spd=34, rng=0, wind=.6, w=14, h=30, fly=True, ranged=dict(keep=130, shot="laser", dmg=13, cd=2.1, speed=300)),
    "drone": dict(hp=16, dmg=7, spd=80, rng=16, wind=.35, w=18, h=12, fly=True),
}
FLYERS = {k for k, v in ESTATS.items() if v.get("fly")}


class Enemy:
    stun_mult = 1.0  # perfect-block stun scaling (bosses resist)
    kb_res = 1.0
    is_boss = False

    def __init__(s, kind, x, y, tint, dscale=1.0, hp=None):
        s.kind, s.d, s.tint, s.dscale = kind, ESTATS[kind], tint, dscale
        s.x, s.y, s.py, s.vy, s.drop, s.ground = float(x), float(y), float(y), 0.0, 0.0, False
        s.hp = s.maxhp = hp or s.d["hp"]
        s.face, s.state, s.st, s.flash, s.stun, s.frozen, s.kb, s.anim, s.hop = -1, "walk", 0.0, 0.0, 0.0, 0.0, 0.0, random.random() * 3, 0.0
        s.act, s.cd, s.cd2, s.dodge_cd, s.hit_done = "melee", random.uniform(0.6, 1.6), random.uniform(2.0, 4.0), 0.0, False

    # ------------------------------------------------------------ AI
    def update(s, dt, a):
        d = s.d
        s.flash = max(0, s.flash - dt)
        s.stun = max(0, s.stun - dt)
        s.frozen = max(0, s.frozen - dt)
        s.cd, s.cd2, s.dodge_cd = max(0, s.cd - dt), max(0, s.cd2 - dt), max(0, s.dodge_cd - dt)
        if s.frozen <= 0:
            s.anim += dt
        s.x = max(8, min(W - 8, s.x + s.kb * dt)); s.kb *= max(0, 1 - dt * 7)
        if s.kind == "dummy": return
        t = a.nearest(s.x)
        if t is None: return
        dx = t.x - s.x
        if s.stun <= 0 and s.frozen <= 0:
            if s.state == "walk":
                s.think(t, dx, dt, a)
            elif s.state == "wind":
                s.st -= dt
                if s.st <= 0: s.strike(t, a)
            elif s.state == "lunge":
                s.do_lunge(t, dt, a)
            else:
                s.st -= dt
                if s.st <= 0: s.state = "walk"
        if d.get("fly"):
            if s.frozen <= 0:
                s.y += (t.y - (30 if d.get("ranged") else 22) + math.sin(s.anim * 3) * 8 - s.y) * min(1, dt * 2.5)
        else:
            s.physics(t, dx, dt, a)

    def physics(s, t, dx, dt, a):
        d = s.d
        if s.ground and s.stun <= 0 and s.frozen <= 0 and s.state == "walk":
            if d.get("hop"):
                s.hop -= dt
                if s.hop <= 0: s.vy, s.hop = -d["hop"][0], random.uniform(d["hop"][1], d["hop"][2])
            elif t.y < s.y - 30 and abs(dx) < (110 if d.get("climb") else 50) and random.random() < dt * 2:
                s.vy = -380 if d.get("climb") else -330
        s.vy = min(520, s.vy + 1000 * dt); s.py = s.y; s.y += s.vy * dt
        land(s, a)

    def think(s, t, dx, dt, a):
        d = s.d
        s.face = 1 if dx > 0 else -1
        if d.get("ranged"): return s.think_ranged(t, dx, dt, a)
        lg = d.get("lunge")
        if lg and s.cd <= 0 and abs(t.y - s.y) < 30 and d["rng"] < abs(dx) <= lg[0]:
            s.state, s.st, s.act = "wind", d["wind"], "lunge"
        elif abs(dx) <= d["rng"] and abs(t.y - s.y) < (40 if d.get("fly") else 30):
            s.state, s.st, s.act = "wind", d["wind"], "melee"
        elif not d.get("hop") or not s.ground:
            s.x += s.face * d["spd"] * dt

    def think_ranged(s, t, dx, dt, a):
        d, r, dist = s.d, s.d["ranged"], abs(dx)
        sm = d.get("summon")
        if sm and s.cd2 <= 0 and a.count(sm[0]) < sm[1] and dist < 260:
            s.state, s.st, s.act = "wind", d["wind"] + 0.5, "summon"
        elif s.cd <= 0 and dist <= r["keep"] + 110 and (d.get("fly") or abs(t.y - s.y) < 70):
            s.state, s.st, s.act = "wind", d["wind"], "shoot"
        elif dist > r["keep"] + 15:
            s.x += s.face * d["spd"] * dt
        elif dist < r["keep"] - 35:
            s.x -= s.face * d["spd"] * 0.8 * dt

    def strike(s, t, a):
        d = s.d
        s.state, s.st = "rest", 0.55
        if s.act == "shoot":
            a.enemy_shoot(s, d["ranged"], t)
            s.cd = d["ranged"]["cd"]
        elif s.act == "summon":
            kind, _, cool = d["summon"]
            a.spawn(kind, x=max(14, min(W - 14, s.x - s.face * 26)), dscale=s.dscale)
            s.cd2 = cool
        elif s.act == "lunge":
            s.state, s.st, s.hit_done = "lunge", d["lunge"][2], False
        elif abs(t.x - s.x) <= d["rng"] + 12 and abs(t.y - s.y) < 40 and (t.x - s.x) * s.face >= 0:
            t.take(d["dmg"] * s.dscale * a.dealt, s.x, a, s)

    def do_lunge(s, t, dt, a):
        d = s.d
        s.st -= dt
        s.x = max(8, min(W - 8, s.x + s.face * d["lunge"][1] * dt))
        if not s.hit_done and abs(t.x - s.x) <= d["w"] / 2 + 12 and abs(t.y - s.y) < 34:
            s.hit_done = True
            t.take(d["dmg"] * s.dscale * a.dealt, s.x, a, s)
        if s.st <= 0:
            s.state, s.st, s.cd = "rest", 0.6, 1.8
