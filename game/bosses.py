"""Level bosses. A Boss is an Enemy driven by a pattern script: rest -> telegraph (state "wind", flashing) -> execute.
Patterns unlock by phase (HP > 66% / > 33% / below) and speed up each phase. Perfect blocks stun a boss only briefly."""
import math, random
from .config import *
from .enemies import Enemy, ESTATS
from .player import land
from .props import Prop
from .sprites_extra import PADB

BOSS_HP = [600, 560, 560, 560, 560, 640]  # base HP per level (before the per-level damage reduction). Tunable; see qa balance report.

BOSSES = {
    "gravekeeper": dict(name="Rotting Gravekeeper", tag="Keeper of the crypt. The dead rise at his word.", w=36, h=84, spd=24, dmg=16, stand=48, minion="zombie",
                        pats=[["swing", "raise"], ["swing", "raise", "grab"], ["swing", "raise", "slam", "grab"]]),
    "beastlord": dict(name="Alpha Beastlord", tag="He charges until something stops him.", w=36, h=86, spd=44, dmg=13, stand=48, minion="wolf",
                      pats=[["lunge", "pounce"], ["lunge", "pounce", "howl"], ["lunge", "pounce", "howl", "swing"]]),
    "paladin": dict(name="Paladin Commander", tag="Shielded by the aegis. Break the orbs.", w=38, h=88, spd=30, dmg=17, stand=50, shield=True,
                    pats=[["bash", "smite"], ["bash", "smite", "guard"], ["bash", "smite", "guard", "smite"]]),
    "archlich": dict(name="The Archlich", tag="Death cannot touch him while his crystals stand.", w=34, h=90, spd=34, dmg=13, keep=140, minion="skeleton",
                     pats=[["fan"], ["fan", "summon", "blink"], ["fan", "summon", "blink", "rain"]]),
    "don": dict(name="The Don", tag="Bulletproof, until he has to reload.", w=34, h=88, spd=34, dmg=9, keep=160, minion="gunman",
                pats=[["burst"], ["burst", "dynamite"], ["burst", "dynamite", "goons"]]),
    "tycoon": dict(name=f"{ALIEN_NAME}, Alien Tycoon", tag="Something has landed. It wants the castle.", w=36, h=90, spd=38, dmg=12, keep=150, fly=True, minion="drone",
                   pats=[["laser", "rockets"], ["laser", "rockets", "drones", "tractor"], ["laser", "rockets", "drones", "tractor", "teleport"]]),
}
WIND = dict(swing=.85, slam=1.1, raise_=.9, lunge=.75, pounce=.9, howl=.8, bash=.7, guard=.3, smite=1.0, fan=.8, summon=.9, blink=.5,
            rain=1.0, burst=.7, dynamite=.8, goons=.8, laser=1.05, rockets=.8, drones=.8, teleport=.45, grab=.9, tractor=1.0)
for _k, _c in BOSSES.items():
    ESTATS[_k] = dict(hp=BOSS_HP[0], dmg=_c["dmg"], spd=_c["spd"], rng=_c.get("stand", 0), wind=.8, w=_c["w"], h=_c["h"], boss=True, foot=PADB,
                      **({"fly": True} if _c.get("fly") else {}), **({"shield": True} if _c.get("shield") else {}))
BOSS_KINDS = list(BOSSES)


class Boss(Enemy):
    is_boss, stun_mult, kb_res = True, 0.4, 0.15

    def __init__(s, kind, x, y, tint, dscale=1.0, hp=None):
        super().__init__(kind, x, y, tint, dscale, hp)
        s.cfg, s.name = BOSSES[kind], BOSSES[kind]["name"]
        s.phase, s.rest, s.act, s.act_t, s.last, s.guard_t = 0, 1.6, None, 0.0, None, 0.0
        s.queue, s.dash, s.pounce, s.pvx, s.air = [], None, False, 0.0, False
        s.arena, s.intro, s.home = None, 0.0, W - 90.0   # intro: seconds left of the entrance (immune, no attacks)
        s.reload_t, s.rage_t, s.extra_rest, s.beam_t, s.beam_hit = 0.0, 0.0, 0.0, 0.0, 0.0

    def setup(s, a):
        """Called by Arena.spawn_boss: remember the arena, start the entrance and create this boss's props."""
        s.arena, s.intro = a, 2.2
        if s.kind == "paladin":
            for k in range(3): a.props.append(Prop("orb", s.x, s.y, 22, s, ang=k * 2.094))
        elif s.kind == "archlich": s.crystals(a, 3)
        elif s.kind == "don":
            for x in (150, 300): a.props.append(Prop("crate", x, FLOOR, 45, s))

    def crystals(s, a, n):
        for k in range(n): a.props.append(Prop("crystal", 60 + (W - 120) * (k + 0.5) / n, FLOOR, 40 + 6 * s.phase, s))

    def props_of(s, kind):
        return [p for p in (s.arena.props if s.arena else []) if p.owner is s and p.kind == kind and p.hp > 0]

    # ------------------------------------------------------------ rules the arena reads
    def dmg_mult(s):
        a = s.arena
        if s.kind == "paladin": return 0.1 if s.props_of("orb") else 1.0
        if s.kind == "don": return 1.0 if s.reload_t > 0 else 0.6
        if s.kind == "tycoon": return 0.5 if a and a.count("drone") >= 2 else 1.0
        return 1.0

    def invulnerable(s):
        return s.intro > 0 or (s.kind == "archlich" and bool(s.props_of("crystal")))

    def status(s):
        if s.intro > 0: return None
        if s.kind == "paladin" and s.props_of("orb"): return ("SHIELDED: break the aegis orbs!", GOLD)
        if s.kind == "archlich" and s.props_of("crystal"): return ("IMMUNE: shatter the crystals!", (110, 240, 150))
        if s.kind == "don": return ("RELOADING - hit him now!", GREEN) if s.reload_t > 0 else ("Bulletproof vest: wait for the reload", STEEL)
        if s.kind == "tycoon" and s.arena and s.arena.count("drone") >= 2: return ("Drone shield: destroy the drones", CYAN)
        if s.kind == "beastlord" and s.stun > 0: return ("DAZED - attack!", GREEN)
        if s.rage_t > 0: return ("MOON RAGE!", RED)
        return None

    def on_prop_died(s, prop, a):
        """A crystal shatters: the Archlich staggers and blinks away. Called by the arena."""
        if prop.kind == "crystal":
            s.stun, s.act, s.state, s.dash = max(s.stun, 1.2), None, "rest", None
            a.texts.append([s.x, s.y - s.d["h"] - 12, "STAGGERED!", CYAN, 1.2]); a.shake = 6
            t = a.nearest(s.x)
            if t: s.pat_blink(t, a)

    # ------------------------------------------------------------ main loop
    def update(s, dt, a):
        if s.intro > 0:  # entrance: slide in from the right edge; immune, no attacks yet
            s.intro -= dt
            s.x += (s.home - s.x) * min(1.0, dt * 2.2)
            s.anim += dt
            if s.d.get("fly"):
                t = a.nearest(s.x)
                if t: s.physics(t, t.x - s.x, dt, a)
            else:
                s.y, s.vy, s.ground = float(FLOOR), 0.0, True  # off-screen there is no floor to land on: stay at floor height
            s.face = -1
            return
        s.flash = max(0, s.flash - dt)
        s.reload_t, s.rage_t = max(0, s.reload_t - dt), max(0, s.rage_t - dt)
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
            if s.kind == "archlich" and not s.props_of("crystal"): s.crystals(a, 1 + ph); a.texts.append([s.x, s.y - s.d["h"] - 30, "CRYSTALS REFORM", (110, 240, 150), 1.4])
            a.texts.append([s.x, s.y - s.d["h"] - 18, "ENRAGED!", RED, 1.4]); a.shake = 8; a.burst(s.x, s.y - 20, RED, 24, 150)
        for q in s.queue[:]:
            q[0] -= dt
            if q[0] <= 0:
                s.queue.remove(q); q[1]()
        if s.beam_t > 0: s.tractor(a, dt)
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
            if s.dash[1] <= 0:
                if not s.dash[2] and (s.x <= 40 or s.x >= W - 40) and s.kind == "beastlord":  # charged into the wall instead of a hero
                    s.stun = 1.8
                    a.texts.append([s.x, s.y - s.d["h"] - 12, "DAZED!", GREEN, 1.3]); a.shake = 8; a.burst(s.x + s.face * 20, s.y - 30, (255, 220, 150), 18, 150)
                s.dash = None
        elif s.act:
            s.act_t -= dt
            if s.act_t <= 0:
                name, s.act, s.state = s.act, None, "walk"
                getattr(s, "pat_" + name.rstrip("_"))(t, a)
                s.rest = max(0.5, 1.5 - 0.25 * s.phase) + s.extra_rest
                s.extra_rest = 0.0
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
            s.x += s.face * c["spd"] * (1.3 if s.rage_t > 0 else 1.0) * dt

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
                s.aoe(a, 60, 1.0)
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
        s.reach(a, 68, 1.0)
        a.burst(s.x + s.face * 30, s.y - 22, WHITE, 10, 110)

    def pat_slam(s, t, a):
        s.aoe(a, 84, 1.15)
        a.shake = 9; a.burst(s.x, s.y, (255, 220, 150), 26, 170)
        for d in (-1, 1):
            a.eshot(s, s.x + d * 14, FLOOR - 6, d * 170, 0, s.cfg["dmg"] * 0.6, "wave", life=1.6)

    def pat_raise(s, t, a):
        """Gravestones push up out of the floor. Break them in time or a zombie rises from each."""
        for k in range(2 + s.phase):
            x = max(40, min(W - 40, s.x + random.choice((-1, 1)) * random.uniform(70, 190) + (k * 23 - 20)))
            a.props.append(Prop("tomb", x, FLOOR, 24, s))
            a.burst(x, FLOOR - 6, (140, 200, 120), 10, 80)
        a.shake = 4

    def pre_grab(s, t, a):
        for p in s.alive(a):
            a.hazard("grab", p.x - 12, p.x + 12, FLOOR - 30, FLOOR + 4, s.act_t, 0.35, s.pdmg(0.6, a), s)

    def pat_grab(s, t, a):
        a.shake = 4

    def pat_lunge(s, t, a):
        """Chain-charge: he keeps running until he hits a hero or the wall. A wall hit leaves him dazed."""
        sp = 380 * (1.3 if s.rage_t > 0 else 1.0)
        wall = W - 20 if s.face > 0 else 20
        s.dash = [s.face * sp, min(1.8, max(0.4, abs(wall - s.x) / sp)), False]

    def pat_pounce(s, t, a):  # leaping slam
        s.vy, s.ground, s.pounce = -400, False, True
        s.pvx = max(-230, min(230, (t.x - s.x) / 0.8))

    def pat_howl(s, t, a):
        s.minions(a, 2)
        s.rage_t = 6.0
        a.texts.append([s.x, s.y - s.d["h"] - 10, "AWOOOO!", WHITE, 1.2]); a.shake = 5

    def pat_bash(s, t, a):
        s.reach(a, 64, 1.1)
        a.burst(s.x + s.face * 30, s.y - 22, GOLD, 12, 130)

    def pat_guard(s, t, a):
        s.guard_t = 2.4
        a.texts.append([s.x, s.y - s.d["h"] - 10, "GUARD!", GOLD, 1.0])
        if not s.props_of("orb"):  # the aegis reforms
            for k in range(3): a.props.append(Prop("orb", s.x, s.y, 22 + 4 * s.phase, s, ang=k * 2.094))
            a.texts.append([s.x, s.y - s.d["h"] - 24, "AEGIS REFORMS", GOLD, 1.2])

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
        n = 4 + s.phase
        for k in range(n):
            s.queue.append([0.18 * k, lambda: a.eshot(s, *s.aim(t, 240), s.cfg["dmg"], "bullet", life=2.2)])

        def reload():
            s.reload_t = 2.2  # the vest comes off while he reloads: the damage window
            a.texts.append([s.x, s.y - s.d["h"] - 12, "RELOADING!", GREEN, 1.5])
        s.queue.append([0.18 * n, reload])
        s.extra_rest = 1.4

    def pat_dynamite(s, t, a):
        T, g = 0.9, 700.0
        sx, sy = s.x + s.face * 10, s.y - s.d["h"] * 0.7
        vx, vy = (t.x - sx) / T, (FLOOR - 4 - sy - 0.5 * g * T * T) / T
        a.eshot(s, sx, sy, vx, vy, s.cfg["dmg"] * 1.4, "dyn", g=g, life=2.0, blast=40)

    def pat_tractor(s, t, a):
        s.beam_t, s.beam_hit = 2.4, 0.0
        a.texts.append([s.x, s.y - s.d["h"] - 12, "TRACTOR BEAM!", CYAN, 1.2])

    def tractor(s, a, dt):
        """Pulls every hero under the saucer upward. Move sideways (or dash out) to escape; reaching the top hurts."""
        s.beam_t -= dt
        s.beam_hit = max(0.0, s.beam_hit - dt)
        for p in s.alive(a):
            if abs(p.x - s.x) < 44:
                if p.y > FLOOR - 150: p.vy, p.ground = min(p.vy, -110.0), False
                else: p.y, p.vy = FLOOR - 150.0, 0.0  # a ceiling: the beam lifts heroes, it never flings them off screen
                if p.y < FLOOR - 120 and s.beam_hit <= 0:
                    s.beam_hit = 0.7
                    p.take(s.pdmg(0.7, a), None, a, None)

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
