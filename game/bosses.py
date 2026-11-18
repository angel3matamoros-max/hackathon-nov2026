"""Level bosses. A Boss is an Enemy driven by a pattern script: rest -> telegraph (state "wind", flashing) -> execute.
Patterns unlock by phase (HP > 66% / > 33% / below) and speed up each phase. Perfect blocks stun a boss only briefly."""
import math, random
from .config import *
from .enemies import Enemy, ESTATS
from .player import land

BOSS_HP = [600, 560, 560, 560, 560, 640]  # base HP per level (before the per-level damage reduction). Tunable; see qa balance report.

BOSSES = {
    "gravekeeper": dict(name="Rotting Gravekeeper", w=24, h=42, spd=24, dmg=16, stand=34, minion="zombie",
                        pats=[["swing"], ["swing", "raise"], ["swing", "raise", "slam"]]),
    "beastlord": dict(name="Alpha Beastlord", w=24, h=44, spd=44, dmg=13, stand=34, minion="wolf",
                      pats=[["lunge", "pounce"], ["lunge", "pounce", "howl"], ["lunge", "pounce", "howl", "swing"]]),
    "paladin": dict(name="Paladin Commander", w=24, h=46, spd=30, dmg=17, stand=36, shield=True,
                    pats=[["bash", "smite"], ["bash", "smite", "guard"], ["bash", "smite", "guard", "smite"]]),
    "archlich": dict(name="The Archlich", w=22, h=46, spd=34, dmg=13, keep=130, minion="skeleton",
                     pats=[["fan"], ["fan", "summon", "blink"], ["fan", "summon", "blink", "rain"]]),
    "don": dict(name="The Don", w=22, h=46, spd=34, dmg=9, keep=150, minion="gunman",
                pats=[["burst"], ["burst", "dynamite"], ["burst", "dynamite", "goons"]]),
    "tycoon": dict(name=f"{ALIEN_NAME}, Alien Tycoon", w=24, h=46, spd=38, dmg=12, keep=140, fly=True, minion="drone",
                   pats=[["laser", "rockets"], ["laser", "rockets", "drones"], ["laser", "rockets", "drones", "teleport"]]),
}
WIND = dict(swing=.85, slam=1.1, raise_=.9, lunge=.75, pounce=.9, howl=.8, bash=.7, guard=.3, smite=1.0, fan=.8, summon=.9, blink=.5,
            rain=1.0, burst=.7, dynamite=.8, goons=.8, laser=1.05, rockets=.8, drones=.8, teleport=.45)
for _k, _c in BOSSES.items():
    ESTATS[_k] = dict(hp=BOSS_HP[0], dmg=_c["dmg"], spd=_c["spd"], rng=_c.get("stand", 0), wind=.8, w=_c["w"], h=_c["h"], boss=True,
                      **({"fly": True} if _c.get("fly") else {}), **({"shield": True} if _c.get("shield") else {}))
BOSS_KINDS = list(BOSSES)


class Boss(Enemy):
    is_boss, stun_mult, kb_res = True, 0.4, 0.15

    def __init__(s, kind, x, y, tint, dscale=1.0, hp=None):
        super().__init__(kind, x, y, tint, dscale, hp)
        s.cfg, s.name = BOSSES[kind], BOSSES[kind]["name"]
        s.phase, s.rest, s.act, s.act_t, s.last, s.guard_t = 0, 1.6, None, 0.0, None, 0.0
        s.queue, s.dash, s.pounce, s.pvx, s.air = [], None, False, 0.0, False

    # ------------------------------------------------------------ main loop
    def update(s, dt, a):
        s.flash = max(0, s.flash - dt)
        s.stun = max(0, s.stun - dt)
        s.frozen = max(0, s.frozen - dt)
        s.guard_t = max(0, s.guard_t - dt)
        if s.frozen <= 0: s.anim += dt
        s.x = max(14, min(W - 14, s.x + s.kb * dt)); s.kb *= max(0, 1 - dt * 7)
        t = a.nearest(s.x)
        if t is None: return
        dx = t.x - s.x
        frac = s.hp / s.maxhp
        ph = 0 if frac > .66 else (1 if frac > .33 else 2)
        if ph != s.phase:
            s.phase, s.act, s.rest, s.dash, s.state = ph, None, 0.7, None, "walk"
            a.texts.append([s.x, s.y - s.d["h"] - 18, "ENRAGED!", RED, 1.4]); a.shake = 8; a.burst(s.x, s.y - 20, RED, 24, 150)
        for q in s.queue[:]:
            q[0] -= dt
            if q[0] <= 0:
                s.queue.remove(q); q[1]()
        if s.stun > 0 or s.frozen > 0:
            s.act, s.dash, s.state = None, None, "rest"
            s.physics(t, dx, dt, a)
            return
        if s.state == "rest": s.state = "walk"
        if s.dash:
            s.dash[1] -= dt
            s.x = max(14, min(W - 14, s.x + s.dash[0] * dt))
            if not s.dash[2] and abs(t.x - s.x) < s.d["w"] / 2 + 12 and abs(t.y - s.y) < 40:
                s.dash[2] = True
                t.take(s.pdmg(1.0, a), s.x, a, s)
            if s.dash[1] <= 0: s.dash = None
        elif s.act:
            s.act_t -= dt
            if s.act_t <= 0:
                name, s.act, s.state = s.act, None, "walk"
                getattr(s, "pat_" + name.rstrip("_"))(t, a)
                s.rest = max(0.5, 1.5 - 0.25 * s.phase)
        else:
            s.face = 1 if dx > 0 else -1
            s.move(dx, dt)
            s.rest -= dt
            if s.rest <= 0: s.choose(t, a)
        s.physics(t, dx, dt, a)

    def move(s, dx, dt):
        c, dist = s.cfg, abs(dx)
        if c.get("keep"):
            if dist > c["keep"] + 30: s.x += s.face * c["spd"] * dt
            elif dist < c["keep"] - 30: s.x -= s.face * c["spd"] * 0.8 * dt
        elif dist > c.get("stand", 30):
            s.x += s.face * c["spd"] * dt

    def physics(s, t, dx, dt, a):
        if s.d.get("fly"):
            s.y += (FLOOR - 30 + math.sin(s.anim * 2) * 6 - s.y) * min(1, dt * 2)  # low hover: reachable with a jump
            return
        was = s.ground
        s.vy = min(520, s.vy + 1000 * dt); s.py = s.y; s.y += s.vy * dt
        land(s, a)
        if s.pounce:
            s.x = max(14, min(W - 14, s.x + s.pvx * dt))
            if s.ground and not was:
                s.pounce = False
                s.aoe(a, 44, 1.0)
                a.burst(s.x, s.y, (255, 220, 150), 18, 140); a.shake = 7

    def choose(s, t, a):
        pats = s.cfg["pats"][min(s.phase, len(s.cfg["pats"]) - 1)]
        pool = [p for p in pats if p != s.last] or pats
        name = random.choice(pool)
        key = "raise_" if name == "raise" else name
        s.last, s.act, s.state = name, key, "wind"
        s.act_t = WIND[key] * (1 - 0.1 * s.phase)
        s.face = 1 if t.x > s.x else -1
        getattr(s, "pre_" + name, lambda t, a: None)(t, a)

    # ------------------------------------------------------------ helpers
    def pdmg(s, mult, a):
        return s.cfg["dmg"] * mult * s.dscale * a.dealt

    def alive(s, a):
        return [p for p in a.players if not p.down]

    def reach(s, a, reach, mult, front=True):
        for p in s.alive(a):
            ahead = (p.x - s.x) * s.face >= -4 if front else True
            if ahead and abs(p.x - s.x) <= reach and abs(p.y - s.y) < 44:
                p.take(s.pdmg(mult, a), s.x, a, s)

    def aoe(s, a, r, mult):
        for p in s.alive(a):
            if abs(p.x - s.x) <= r and abs(p.y - s.y) < 34:
                p.take(s.pdmg(mult, a), s.x, a, s)

    def minions(s, a, n=2):
        kind = s.cfg["minion"]
        for k in range(n):
            if a.count(kind) < 4:
                x = max(14, min(W - 14, s.x + (-1 if k % 2 else 1) * (40 + 22 * k)))
                a.spawn(kind, x=x, dscale=s.dscale)

    def aim(s, t, speed, sy=None):
        sx, sy = s.x + s.face * 12, sy if sy is not None else s.y - s.d["h"] * 0.6
        ang = math.atan2((t.y - 16) - sy, t.x - sx)
        return sx, sy, math.cos(ang) * speed, math.sin(ang) * speed

    # ------------------------------------------------------------ patterns
    def pat_swing(s, t, a):
        s.reach(a, 50, 1.0)
        a.burst(s.x + s.face * 30, s.y - 22, WHITE, 10, 110)

    def pat_slam(s, t, a):
        s.aoe(a, 64, 1.15)
        a.shake = 9; a.burst(s.x, s.y, (255, 220, 150), 26, 170)
        for d in (-1, 1):
            a.eshot(s, s.x + d * 14, FLOOR - 6, d * 170, 0, s.cfg["dmg"] * 0.6, "wave", life=1.6)

    def pat_raise(s, t, a):
        s.minions(a, 2)
        a.burst(s.x, s.y, (140, 200, 120), 18, 90)

    def pat_lunge(s, t, a):
        s.dash = [s.face * 380, 0.5, False]

    def pat_pounce(s, t, a):
        s.vy, s.ground, s.pounce = -400, False, True
        s.pvx = max(-230, min(230, (t.x - s.x) / 0.8))

    def pat_howl(s, t, a):
        s.minions(a, 2)
        a.texts.append([s.x, s.y - s.d["h"] - 10, "AWOOOO!", WHITE, 1.2]); a.shake = 5

    def pat_bash(s, t, a):
        s.reach(a, 46, 1.1)
        a.burst(s.x + s.face * 30, s.y - 22, GOLD, 12, 130)

    def pat_guard(s, t, a):
        s.guard_t = 2.4
        a.texts.append([s.x, s.y - s.d["h"] - 10, "GUARD!", GOLD, 1.0])

    def pre_smite(s, t, a):
        xs = [p.x for p in s.alive(a)] + ([random.uniform(30, W - 30)] if s.phase >= 1 else []) + ([random.uniform(30, W - 30)] if s.phase >= 2 else [])
        for x in xs:
            a.hazard("pillar", x - 11, x + 11, 0, FLOOR + 4, s.act_t, 0.3, s.pdmg(1.3, a), s)

    def pat_smite(s, t, a):
        a.shake = 6

    def pat_fan(s, t, a):
        n = 5 + s.phase
        sx, sy, vx, vy = s.aim(t, 130, s.y - s.d["h"] * 0.6)
        base = math.atan2(vy, vx)
        for k in range(n):
            ang = base + math.radians(-34 + 68 * k / (n - 1))
            a.eshot(s, sx, sy, math.cos(ang) * 130, math.sin(ang) * 130, s.cfg["dmg"], "soul", life=3.0)

    def pat_summon(s, t, a):
        s.minions(a, 2)
        a.burst(s.x, s.y - 20, (110, 230, 130), 18, 100)

    def pat_blink(s, t, a):
        a.burst(s.x, s.y - 20, (150, 90, 220), 16, 110)
        far = [x for x in range(30, W - 29, 30) if abs(x - t.x) > 120] or [30]
        s.x = float(random.choice(far)); s.face = 1 if t.x > s.x else -1
        a.burst(s.x, s.y - 20, (150, 90, 220), 16, 110)
        s.queue.append([0.45, lambda: s.pat_fan(t, a)])

    def pre_rain(s, t, a):
        for k in range(4 + s.phase):
            x = random.uniform(30, W - 30)
            a.hazard("pillar", x - 9, x + 9, 0, FLOOR + 4, 0.8 + 0.3 * k, 0.3, s.pdmg(1.0, a), s)

    def pat_rain(s, t, a):
        a.shake = 4

    def pat_burst(s, t, a):
        for k in range(4 + s.phase):
            s.queue.append([0.18 * k, lambda: a.eshot(s, *s.aim(t, 240), s.cfg["dmg"], "bullet", life=2.2)])

    def pat_dynamite(s, t, a):
        T, g = 0.9, 700.0
        sx, sy = s.x + s.face * 10, s.y - s.d["h"] * 0.7
        vx, vy = (t.x - sx) / T, (FLOOR - 4 - sy - 0.5 * g * T * T) / T
        a.eshot(s, sx, sy, vx, vy, s.cfg["dmg"] * 1.4, "dyn", g=g, life=2.0, blast=40)

    def pat_goons(s, t, a):
        s.minions(a, 2)
        a.burst(s.x, s.y - 20, (200, 200, 210), 14, 90)

    def pre_laser(s, t, a):
        y = t.y - 16
        x0, x1 = (s.x, W) if s.face > 0 else (0, s.x)
        a.hazard("beam", x0, x1, y - 7, y + 7, s.act_t, 0.55, s.pdmg(1.1, a), s)

    def pat_laser(s, t, a):
        a.shake = 5

    def pat_rockets(s, t, a):
        for k in range(2 + s.phase):
            tx = max(20, min(W - 20, t.x + random.uniform(-90, 90)))

            def fire(tx=tx):
                sx, sy, T, g = s.x, s.y - 30, 0.85, 600.0
                a.eshot(s, sx, sy, (tx - sx) / T, (FLOOR - 4 - sy - 0.5 * g * T * T) / T, s.cfg["dmg"] * 1.2, "rocket", g=g, life=2.0, blast=30)

            s.queue.append([0.22 * k, fire])

    def pat_drones(s, t, a):
        s.minions(a, 2)

    def pat_teleport(s, t, a):
        s.pat_blink(t, a)
