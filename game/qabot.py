"""Scripted players for automated QA (tests, --selftest, balance report). Not used by the real game.

FakeMotion has exactly the Motion fields, so bots exercise the same code paths a keyboard or the GY-521 would.
Bot skill levels: "naive" never defends; "careful" blocks incoming melee and steps out of boss telegraphs (a rough human proxy)."""
from .config import *


class FakeMotion:
    def __init__(s, i):
        s.i, s.axis, s.tilt, s.shake = i, 0, 0.0, 0.0
        s.jump_h = s.down_h = s.block_h = s.interact_h = False
        s.reset()

    def reset(s):
        s.jump_p = s.down_p = s.dash_p = s.slash_p = s.cast_p = s.cast2_p = s.flick = s.skip_p = s.gear_p = False
        s.swing = None

    def update(s, events, dt):  # parity with Motion.update; scripted callers set fields directly
        pass


class Bot:
    def __init__(s, skill="naive"):
        s.skill, s.t, s.cd = skill, 0.0, {}

    def ready(s, p, name, every, first=0.0):
        """True once per `every` seconds for this player+action. Real timers, so the bot plays the same at any frame rate
        (the old `int(t*60) % N` scheme almost never fired for player 2 at 30 Hz)."""
        due = s.cd.setdefault((p.i, name), first)
        if s.t >= due:
            s.cd[(p.i, name)] = s.t + every
            return True
        return False

    def targets(s, arena):
        """What a scripted hero attacks: living foes, plus the breakable boss props (gravestones, aegis orbs, crystals). While the boss is
        immune, only the props that unlock it."""
        foes = [e for e in arena.enemies if e.kind != "dummy" and e.hp > 0]
        props = [q for q in arena.props if q.hp > 0 and q.kind in ("crystal", "orb", "tomb")]
        boss = arena.boss
        if props and boss and boss.hp > 0 and boss.invulnerable(): return props
        return foes + props

    def drive(s, arena, mo, dt):
        """Fill the FakeMotions `mo` for one frame of `arena`."""
        s.t += dt
        t = s.t
        for m in mo:
            m.reset()
        foes = s.targets(arena)
        for p in arena.players:
            m = mo[p.i]
            m.axis, m.interact_h, m.block_h = 0, False, False
            if p.down: continue
            if arena.state == "chest":  # take whatever the chest offers
                if arena.cm and arena.cm["p"] is p: m.swing = "left"; m.slash_p = s.ready(p, "chest", 0.25)
                continue
            if arena.state == "loot":
                m.slash_p = m.flick = True; m.shake = 1.0; m.swing = ("left", "right", "up", "down")[int(t * 4) % 4]
                continue
            if s.skill == "careful" and s.avoid(arena, p, m): continue
            if foes:
                e = min(foes, key=lambda e: abs(e.x - p.x))
                dx = e.x - p.x
                m.axis = 0 if abs(dx) < 22 else (1 if dx > 0 else -1)
                if s.skill == "careful" and e.state == "wind" and abs(dx) < 56 and (dx * p.face >= 0):
                    m.block_h = True
                    continue
                if abs(dx) < 36 and s.ready(p, "slash", 0.34, p.i * 0.11): m.slash_p = True
                if s.ready(p, "cast", 3.0, 0.5 + p.i * 0.5): m.cast_p = True
                if s.ready(p, "cast2", 4.0, 1.7 + p.i * 0.5): m.cast2_p = True
                if e.y < p.y - 30 and s.ready(p, "jump", 0.75): m.jump_p = True
            else:
                near = [c for c in arena.corpses if not c["looted"]]
                ch = arena.chest if (arena.chest and p.i not in arena.chest["used"]) else None
                if ch:
                    m.axis = 0 if abs(ch["x"] - p.x) < 10 else (1 if ch["x"] > p.x else -1)
                    m.interact_h = abs(ch["x"] - p.x) < 20
                elif near and s.skill == "loot":
                    c = near[0]
                    m.axis = 0 if abs(c["x"] - p.x) < 8 else (1 if c["x"] > p.x else -1)
                    m.interact_h = abs(c["x"] - p.x) < 20
                else:
                    m.axis = 1  # head for the portal

    def avoid(s, arena, p, m):
        """Careful bot: leave a warned hazard column, jump/dash incoming shots. Returns True if it acted."""
        for h in arena.hazards:
            if h["x0"] - 14 <= p.x <= h["x1"] + 14 and (h["warn"] > 0 or h["life"] > 0):
                m.axis = 1 if p.x >= (h["x0"] + h["x1"]) / 2 else -1
                if h["kind"] == "beam": m.jump_p = s.ready(p, "hjump", 0.2)
                m.dash_p = s.ready(p, "hdash", 0.42)
                return True
        for pr in arena.eprojs:
            if pr["blast"]:  # lobbed explosive: leave its landing zone
                land_x = pr["x"] + pr["vx"] * max(0.0, (FLOOR - pr["y"]) / max(60.0, abs(pr["vy"]) + 200.0))
                if abs(land_x - p.x) < pr["blast"] + 22:
                    m.axis = 1 if p.x >= land_x else -1
                    m.dash_p = s.ready(p, "ldash", 0.33)
                    return True
                continue
            if abs(pr["x"] - p.x) < 90 and abs(pr["y"] - (p.y - 16)) < 24 and (pr["vx"] * (p.x - pr["x"]) > 0) and pr["kind"] != "wave":
                m.block_h = True  # raise the shield against bullets
                return True
            if abs(pr["x"] - p.x) < 60 and abs(pr["y"] - (p.y - 16)) < 24 and (pr["vx"] * (p.x - pr["x"]) > 0):
                m.dash_p = True
                m.jump_p = pr["kind"] == "wave"
                return True
        return False


def run_bot(arena, seconds, dt=1 / 60, skill="naive", draw=False):
    """Run `arena` with a bot for up to `seconds` of game time (stops early on arena.result). Returns the motions."""
    mo = [FakeMotion(p.i) for p in arena.players]
    bot = Bot(skill)
    for _ in range(int(seconds / dt)):
        bot.drive(arena, mo, dt)
        arena.update(dt, mo)
        if draw: arena.draw()
        if arena.result: break
    return mo
