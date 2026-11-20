"""Player entity and shared physics helpers."""
import random
from .config import *
from .classes import CLASSES
from .items import mods, SLOTS
from . import sound


def land(o, a):
    o.ground = False
    if o.vy >= 0:
        for px, py, pw in a.plats:
            if (py == FLOOR or o.drop <= 0) and o.py <= py + 0.5 and o.y >= py and px - 4 <= o.x <= px + pw + 4:
                o.y, o.vy, o.ground = float(py), 0.0, True
                return True
    return False


def overlap(x0, x1, y0, y1, e):
    return x0 < e.x + e.d["w"] / 2 and x1 > e.x - e.d["w"] / 2 and y0 < e.y and y1 > e.y - e.d["h"]


class Player:
    def __init__(s, i, cls, x):
        d = CLASSES[cls]
        s.i, s.cls, s.x, s.y, s.py, s.vx, s.vy = i, cls, float(x), float(FLOOR), float(FLOOR), 0.0, 0.0
        s.maxhp = s.hp = d["hp"] * 12 + 12
        s.shield = s.shield_t = 0.0
        s.atk = 8 + d["atk"] * 2
        s.face, s.jumps, s.ground, s.down = 1, 0, True, False
        s.skill, s.block, s.block_t, s.anim = None, False, 9.0, 0.0
        s.slash_t = s.slash_cd = s.cast_cd = s.cast2_cd = 0.0
        s.dash_t = s.dash_cd = s.inv = s.stun = s.drop = s.flash = s.skill_t = s.tick = s.kb = 0.0
        s.coyote = s.jbuf = 0.0
        s.wall = 0  # -1 left wall, +1 right wall, 0 none
        s.hitset = set()
        s.travel = 0.0
        s.djumps = s.dashes = s.blocks = s.perfects = s.casts = s.casts2 = 0
        s.gear, s.dmg_taken, s.cd_mult, s.fly = dict.fromkeys(SLOTS), 1.0, 1.0, False  # gear / curse / dev state
        s.speed, s.lifesteal, s.crit, s.thorns, s.block_window = 1.0, 0.0, 0.0, 0.0, 0.0
        s.heal_acc = 0.0  # fractional lifesteal carried between hits
        s.cpu, s.rooted = False, 0.0  # cpu: the solo-mode ally; rooted: held by grave hands (dash breaks free)

    @property
    def weapon(s):
        return s.gear["weapon"]

    def recompute(s):
        """Fold the three equipped items into ATK / max HP / damage taken / cooldowns / perks. Keeps the HP ratio."""
        d, m = CLASSES[s.cls], mods(s.gear.values())
        if s.cpu: m["atk"] *= 0.6; m["cd_mult"] *= 1.5  # the CPU ally is an assistant: weaker hits, slower skills
        s.atk = int(round((8 + d["atk"] * 2) * m["atk"]))
        s.dmg_taken, s.cd_mult, s.speed = m["dmg_taken"], m["cd_mult"], m["speed"]
        s.lifesteal, s.crit, s.thorns, s.block_window = m["lifesteal"], m["crit"], m["thorns"], m["block_window"]
        new_max = max(1, int(round((d["hp"] * 12 + 12) * m["hp"])))
        ratio = s.hp / s.maxhp if s.maxhp else 1.0
        s.maxhp, s.hp = new_max, max(1, min(new_max, int(round(new_max * ratio)))) if not s.down else 0

    def equip(s, it):
        """Put item `it` into its slot (replacing what was there) and recompute stats."""
        s.gear[it["slot"]] = it
        s.recompute()

    def update(s, dt, m, a):
        if s.down:
            s.rooted = 0.0
            return
        if s.fly:  # dev-mode noclip flight
            s.x = max(10, min(W - 10, s.x + m.axis * 200 * dt)); s.y = max(30.0, min(float(FLOOR), s.y + (int(m.down_h) - int(m.jump_h)) * 200 * dt))
            s.vx = s.vy = 0.0; s.py = s.y
            if m.axis: s.face = m.axis
            return
        for n in ("slash_cd", "cast_cd", "cast2_cd", "dash_cd", "inv", "stun", "drop", "flash", "coyote", "jbuf", "shield_t", "rooted"):
            setattr(s, n, max(0.0, getattr(s, n) - dt))
        if s.shield_t <= 0:
            s.shield = 0.0
        free = s.stun <= 0 and s.skill != "charge"
        ax = m.axis if free and s.rooted <= 0 else 0
        was = s.block
        s.block = bool(m.block_h) and free and s.dash_t <= 0 and s.slash_t <= 0
        s.block_t = (s.block_t + dt) if (s.block and was) else (0.0 if s.block else 9.0)

        # smoother acceleration + responsive air control
        max_spd = 128 * s.speed * (0.38 if s.block else 1.0)
        accel = 1350 if s.ground else 920
        if ax:
            s.face = ax
            s.anim += dt * (11 if not s.block else 4)
            s.travel += abs(s.vx) * dt
            target_vx = ax * max_spd
            if s.vx < target_vx: s.vx = min(target_vx, s.vx + accel * dt)
            elif s.vx > target_vx: s.vx = max(target_vx, s.vx - accel * dt)
        else:
            s.anim = 0.0
            fric = 1400 if s.ground else 420
            if s.vx > 0: s.vx = max(0.0, s.vx - fric * dt)
            elif s.vx < 0: s.vx = min(0.0, s.vx + fric * dt)

        if m.jump_p:
            s.jbuf = 0.12
            sound.play("jump")

        if free:
            # jump / coyote jump / wall jump / double jump
            if s.jbuf > 0 and s.rooted <= 0:
                if s.ground or s.coyote > 0:
                    s.vy, s.ground, s.coyote, s.jbuf, s.jumps = -345, False, 0.0, 0.0, 1
                    a.burst(s.x, s.y, WHITE, 5, 45)
                elif s.wall != 0 and not s.ground:
                    s.vy = -335
                    s.vx = -s.wall * 195
                    s.face = -s.wall
                    s.jbuf, s.jumps = 0.0, 1
                    a.burst(s.x + s.wall * 6, s.y - 12, WHITE, 7, 65)
                elif s.jumps < 2:
                    s.vy, s.ground, s.jbuf = -305, False, 0.0
                    s.jumps = 2
                    s.djumps += 1
                    a.burst(s.x, s.y, WHITE, 8, 70)
            # variable jump cut when releasing jump early
            if not m.jump_h and s.vy < -130:
                s.vy *= 0.65 ** (dt * 60)  # per-frame cut made jump height depend on frame rate
            # drop through platform or fast-fall in air
            if m.down_p:
                s.drop = 0.25
            if m.down_h and not s.ground and s.vy > 0:
                s.vy = min(560, s.vy + 750 * dt)
            if m.dash_p and s.dash_cd <= 0:
                s.rooted = 0.0
                s.dash_t, s.dash_cd, s.inv, s.dashes = 0.18, 0.72, max(s.inv, 0.24), s.dashes + 1
                if not s.ground:
                    s.vy = min(s.vy, 0.0)
            if m.slash_p and s.slash_cd <= 0 and not s.block:
                s.slash_t, s.slash_cd, s.hitset = 0.16, 0.34, set()
                sound.play("swing")
            if m.cast_p and s.cast_cd <= 0 and s.skill is None:
                a.cast(s)
            if m.cast2_p and s.cast2_cd <= 0 and s.skill is None:
                a.cast2(s)

        if s.dash_t > 0:
            s.dash_t -= dt
            s.vx = s.face * 355
            if random.random() < 0.7:
                a.burst(s.x, s.y - 12, (200, 220, 255), 1, 20)
        if s.slash_t > 0:
            s.slash_t -= dt
            s.vx += s.face * 28
            a.slash_hit(s)
        if s.skill:
            s.skill_t -= dt
            if s.skill == "charge":
                s.vx = s.face * 350
                a.slash_hit(s, 30, s.atk * 1.35)
                a.burst(s.x, s.y - 12, GOLD, 1, 30)
            else:
                s.tick -= dt
                if s.tick <= 0:
                    s.tick = 0.16
                    a.hit_radius(s.x, s.y - 14, 38, s.atk * 0.75, 130, by=s)
            if s.skill_t <= 0:
                s.skill = None

        s.vx += s.kb
        s.kb *= max(0.0, 1 - dt * 8)

        # wall detection & wall-slide friction
        s.wall = -1 if s.x <= 11 else (1 if s.x >= W - 11 else 0)
        grav = 1000
        if not s.ground and s.wall != 0 and ax == s.wall and s.vy > 0:
            grav = 260
            s.vy = min(s.vy, 95)
            if random.random() < 0.35:
                a.burst(s.x + s.wall * 6, s.y - 10, STEEL, 1, 15)

        s.vy = min(540, s.vy + grav * dt)
        s.x = max(10, min(W - 10, s.x + s.vx * dt))
        s.py = s.y
        s.y += s.vy * dt
        was_ground = s.ground
        if land(s, a):
            if not was_ground:
                a.burst(s.x, s.y, STEEL_D, 4, 35)
            s.jumps, s.coyote = 0, 0.10
        elif was_ground and s.vy >= 0:
            s.coyote = 0.10

    def take(s, dmg, sx, a, src):
        if s.down or s.inv > 0 or getattr(a, 'god', False): return
        if s.block and sx is not None and (sx - s.x) * s.face >= 0:
            s.blocks += 1
            sound.play("block")
            if s.block_t < 0.2 + s.block_window:
                s.perfects += 1
                if src is not None and hasattr(src, "stun"):
                    src.stun, src.state, src.st = 1.4 * src.stun_mult, "rest", 0.4
                a.texts.append([s.x, s.y - 46, "PERFECT BLOCK!", GOLD, 1.0]); a.burst(s.x + s.face * 12, s.y - 16, GOLD, 12, 120); a.shake = 4
                return
            dmg *= 0.2; s.kb = -s.face * 60
            a.texts.append([s.x, s.y - 42, "BLOCKED", CYAN, 0.6])
        else:
            s.kb, s.stun = (0 if sx is None else (1 if s.x >= sx else -1) * 120), 0.22
        dmg = max(1, int(round(dmg * (1 - CLASSES[s.cls]["df"] * 0.04) * s.dmg_taken))) if dmg > 0 else 0
        s.inv, s.flash = 0.5, 0.15
        if dmg > 0 and s.shield > 0:
            absorbed = min(s.shield, dmg)
            s.shield -= absorbed
            dmg -= int(absorbed)
            a.texts.append([s.x, s.y - 48, "SHIELDED", CYAN, 0.6])
        if dmg > 0:
            s.hp -= dmg
            sound.play("hurt")
            if s.thorns and src is not None and getattr(src, "hp", 0) > 0 and not getattr(src, "is_boss", False) and getattr(src, "kind", "") != "dummy":
                src.hp -= s.thorns; src.flash = 0.1  # reflected damage; the arena's update loop handles the kill
            a.texts.append([s.x, s.y - 40, f"-{dmg}", (255, 90, 90), 0.8]); a.burst(s.x, s.y - 16, RED, 6, 90); a.shake = 3
        if s.hp <= 0:
            s.hp, s.down = 0, True
            a.burst(s.x, s.y - 14, P_COL[s.i], 22, 130); a.texts.append([s.x, s.y - 40, "DOWN!", RED, 1.5])


def apply_gear(p, w):
    """Equip weapon-slot item `w` (or None to unequip the weapon). Kept for the holy chest and old callers."""
    if w is None:
        p.gear["weapon"] = None
        p.recompute()
    else:
        p.equip(w if "slot" in w else dict(w, slot="weapon"))
