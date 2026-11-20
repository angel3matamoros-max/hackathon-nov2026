"""Loot mini-games and loot rolling."""
import math, random
import pygame
from . import gfx
from .config import *
from .gfx import text, bar, lerp, font, mid
from .sprites import HERO, MIMIC
from .items import describe


class Mini:
    over, score, t, bonus, hero = False, 0.0, 0.0, 0.0, "Knight"
    kind = title = hint = ""

    def finish(s, score):
        s.over, s.score = True, max(0, min(1, score * (1 + s.bonus)))

    def bg(s):
        gfx.canvas.fill((24, 18, 36))
        pygame.draw.rect(gfx.canvas, (70, 60, 100), (2, 2, PW - 4, 176), 1)
        text(s.title, PW // 2, 8, GOLD, mid, True)


PIPS = {1: [(1, 1)], 2: [(0, 0), (2, 2)], 3: [(0, 0), (1, 1), (2, 2)], 4: [(0, 0), (2, 0), (0, 2), (2, 2)],
        5: [(0, 0), (2, 0), (1, 1), (0, 2), (2, 2)], 6: [(0, 0), (2, 0), (0, 1), (2, 1), (0, 2), (2, 2)]}


class DiceShake(Mini):
    kind, title, hint = "dice", "DICE ROLL", "Shake hard! Bigger shake = better loot."

    def ctrl(s, p): return f"Mash [{kn(p, 'slash')}] as fast as you can!"

    def __init__(s): s.acc, s.face, s.sh = 0.0, 1, 0.0

    def update(s, dt, m):
        s.t += dt
        if s.over: return
        s.sh = m.shake
        s.acc = min(1, s.acc + m.shake * dt * 0.4)
        if random.random() < dt * 18: s.face = random.randint(1, 6)
        if s.t >= 4:
            s.face, s.sh = 1 + round(s.acc * 5), 0
            s.finish(s.acc)

    def draw(s):
        s.bg()
        j = int(s.sh * 4)
        cx, cy = 80 + random.randint(-j, j), 62 + random.randint(-j, j)
        pygame.draw.rect(gfx.canvas, INK, (cx - 22, cy - 22, 44, 44)); pygame.draw.rect(gfx.canvas, WHITE, (cx - 20, cy - 20, 40, 40))
        pygame.draw.rect(gfx.canvas, (200, 200, 215), (cx - 20, cy + 16, 40, 4))
        for gx, gy in PIPS[s.face]:
            pygame.draw.rect(gfx.canvas, INK, (cx + (gx - 1) * 11 - 3, cy + (gy - 1) * 11 - 3, 6, 6))
        text("SHAKE POWER", 80, 100, WHITE, font, True)
        bar(30, 113, 100, 8, s.acc, GOLD); bar(30, 130, 100, 3, 1 - s.t / 4, STEEL_D)


class LockPick(Mini):
    kind, title, hint = "lock", "LOCK PICK", "Find the sweet spot and hold steady!"

    def ctrl(s, p): return f"Hold [{kn(p, 'left')}] / [{kn(p, 'right')}] to tilt the pick"

    def __init__(s): s.target, s.pick, s.hold, s.err = random.uniform(-60, 60), 0.0, 0.0, 90

    def update(s, dt, m):
        if s.over: return
        s.t += dt
        s.pick = max(-90, min(90, s.pick + m.tilt * dt * 80))
        s.err = abs(s.pick - s.target)
        if s.err < 8: s.hold += dt
        if s.hold >= 2: s.finish(max(0.35, 1 - s.t / 12))
        elif s.t >= 12: s.finish(min(0.3, s.hold / 2 * 0.3))

    def draw(s):
        s.bg()
        col, cx, cy = lerp(BLUE, GOLD, max(0, 1 - s.err / 60)), 80, 66
        pygame.draw.circle(gfx.canvas, INK, (cx, cy), 36); pygame.draw.circle(gfx.canvas, col, (cx, cy), 34)
        pygame.draw.circle(gfx.canvas, INK, (cx, cy), 27); pygame.draw.circle(gfx.canvas, (50, 42, 70), (cx, cy), 25)
        pygame.draw.rect(gfx.canvas, INK, (cx - 2, cy, 4, 9))
        a = math.radians(s.pick)
        pygame.draw.line(gfx.canvas, STEEL, (cx, cy), (cx + math.sin(a) * 26, cy - math.cos(a) * 26), 2)
        pygame.draw.circle(gfx.canvas, INK, (cx, cy), 5)
        text("UNLOCKING", 80, 106, WHITE, font, True)
        bar(30, 118, 100, 6, s.hold / 2, GREEN); bar(30, 132, 100, 3, 1 - s.t / 12, STEEL_D)


class SlashLoot(Mini):
    kind, title, hint = "slash", "SLASH THE LOOT", "Swing the way the arrow points!"
    N = 8
    ARROW = [(-12, -5), (2, -5), (2, -11), (14, 0), (2, 11), (2, 5), (-12, 5)]
    ROT = {"right": lambda x, y: (x, y), "left": lambda x, y: (-x, y), "down": lambda x, y: (-y, x), "up": lambda x, y: (y, -x)}

    def ctrl(s, p):
        if PAD[p] and PAD[p].get("_name") == "PS2": return "Tap the arrow on the D-pad, or hold it and press [{square}]"  # PS2: no Cross, D-pad + Square only
        return f"Press [{kn(p, 'left')}] [{kn(p, 'right')}] [{kn(p, 'jump')}] [{kn(p, 'down')}]"

    def __init__(s):
        s.res, s.tt, s.win, s.flash, s.msg = [], 0.0, 1.1, 0.0, ""
        s.cur = random.choice(list(s.ROT))

    def step(s, ok):
        s.res.append(ok)
        s.flash, s.msg = 0.35, "HIT!" if ok else "MISS"
        if len(s.res) >= s.N: s.finish(sum(s.res) / s.N)
        s.cur, s.tt, s.win = random.choice(list(s.ROT)), 0.0, max(0.65, 1.1 - 0.05 * len(s.res))

    def update(s, dt, m):
        if s.over: return
        s.tt += dt
        s.flash = max(0, s.flash - dt)
        if m.swing: s.step(m.swing == s.cur)
        elif s.tt > s.win: s.step(False)

    def draw(s):
        s.bg()
        cx, cy = 80, 64
        if not s.over:
            pygame.draw.circle(gfx.canvas, STEEL_D, (cx, cy), 8 + int(36 * (1 - s.tt / s.win)), 1)
            f = s.ROT[s.cur]
            pts = [(cx + f(x, y)[0], cy + f(x, y)[1]) for x, y in s.ARROW]
            pygame.draw.polygon(gfx.canvas, INK, pts, 3); pygame.draw.polygon(gfx.canvas, GOLD, pts)
        if s.flash: text(s.msg, cx, 116, GREEN if s.msg == "HIT!" else RED, mid, True)
        for i in range(s.N):
            c = GREY if i >= len(s.res) else (GREEN if s.res[i] else RED)
            pygame.draw.rect(gfx.canvas, INK, (15 + i * 16, 138, 11, 11)); pygame.draw.rect(gfx.canvas, c, (16 + i * 16, 139, 9, 9))


class Parry(Mini):
    kind, title, hint = "parry", "PARRY THE MIMIC", "Strike when it hits the green zone!"
    ZC, HALF, ROUNDS = 98, 12, 3

    def ctrl(s, p): return f"Press [{kn(p, 'slash')}] in the green zone"

    def __init__(s): s.r, s.res, s.mx, s.pause, s.msg = 0, [], 200.0, 0.0, ""

    def resolve(s, q):
        s.res.append(q); s.r += 1
        s.pause, s.msg = 0.8, "PARRY!" if q > 0 else "OUCH!"
        if q > 0: s.mx = s.ZC + 40

    def update(s, dt, m):
        if s.over: return
        if s.pause > 0:
            s.pause -= dt
            if s.pause <= 0:
                if s.r >= s.ROUNDS: s.finish(sum(s.res) / s.ROUNDS)
                else: s.mx, s.msg = 200.0, ""
            return
        s.mx -= (100 + 30 * s.r) * dt
        d = abs(s.mx - s.ZC)
        if m.flick: s.resolve(1 - d / s.HALF if d <= s.HALF else 0)
        elif s.mx < 76: s.resolve(0)

    def draw(s):
        s.bg()
        pygame.draw.rect(gfx.canvas, (62, 50, 74), (4, 112, PW - 8, 38))
        pygame.draw.rect(gfx.canvas, (40, 110, 60), (s.ZC - s.HALF, 80, 2 * s.HALF, 32)); pygame.draw.rect(gfx.canvas, GREEN, (s.ZC - s.HALF, 80, 2 * s.HALF, 32), 1)
        gfx.canvas.blit(pygame.transform.scale(HERO[s.hero][0], (60, 60)), (8, 54))
        gfx.canvas.blit(pygame.transform.scale(MIMIC, (36, 32)), (int(s.mx) - 18, 80))
        text(f"ROUND {min(s.r + 1, s.ROUNDS)}/{s.ROUNDS}", 80, 30, WHITE, font, True)
        if s.msg: text(s.msg, 80, 44, GREEN if s.msg == "PARRY!" else RED, mid, True)


MINIS = [DiceShake, LockPick, SlashLoot, Parry]
# ---------------------------------------------------------------- holy chest (level 3): class weapons, 75% holy / 25% cursed
HOLY = {
    "Knight": dict(name="Lightbringer", cursed="Lightbringer, Fallen", curse=("Brittle Soul", "Take +30% damage", dict(dmg_taken=1.3))),
    "Tank": dict(name="Sanctified Maul", cursed="Maul of Ruin", curse=("Withering", "Max HP -20%", dict(hp=0.8))),
    "Fighter": dict(name="Radiant Greatsword", cursed="Greatsword of Wrath", curse=("Heavy Soul", "Skill cooldowns +40%", dict(cd_mult=1.4))),
    "Mage": dict(name="Staff of Dawn", cursed="Staff of Dusk", curse=("Frail Mind", "Max HP -25%", dict(hp=0.75))),
    "Rogue": dict(name="Sunfang Daggers", cursed="Moonfang Daggers", curse=("Glass Edge", "Take +35% damage", dict(dmg_taken=1.35))),
}
HOLY_ATK, CURSED_ATK, CURSE_CHANCE = 1.25, 1.70, 0.25


def roll_holy(cls, rng=random):
    """One chest roll for a player of class `cls`: 75% holy weapon (+25% ATK), 25% stronger cursed one (+70% ATK + a curse)."""
    h = HOLY[cls]
    if rng.random() < CURSE_CHANCE:
        cname, ctext, eff = h["curse"]
        it = dict(name=h["cursed"], slot="weapon", tier=3, cursed=True, atk=CURSED_ATK, curse=cname, curse_text=ctext, **eff)
    else:
        it = dict(name=h["name"], slot="weapon", tier=2, cursed=False, atk=HOLY_ATK)
    it["desc"] = describe(it)
    return it
