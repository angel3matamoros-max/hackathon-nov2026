"""The CPU ally for solo play: an assistant, not a second hero.

It drives player 2's Motion every frame, using the same fields a human would. It is deliberately weaker than the human and waits
on the human's decisions: it stays close to the human, reacts to a telegraph only after a short delay, casts its skills rarely,
never loots corpses (those are the human's), and takes a boss-chest item only after the human has taken theirs.
Its handicap (weaker hits, slower skills) lives in Player.recompute()."""
from .config import *
from .qabot import Bot, FakeMotion

COMPLEMENT = dict(Knight="Mage", Tank="Fighter", Fighter="Knight", Mage="Tank", Rogue="Knight")  # default CPU class for each P1 class
STAY, LEASH = 80, 150    # follow the human when further than STAY; drop everything and return when further than LEASH
ENGAGE = 130             # only fight foes within this distance of the human
REACT = 0.35             # seconds before the ally reacts to a telegraph


class AllyMotion(FakeMotion):
    """Inert for the keyboard: filled in by Ally.tick()."""


class Ally(Bot):
    def __init__(s):
        super().__init__("careful")
        s.seen = None  # when the ally first saw the current telegraph

    def tick(s, arena, m, dt, me=1, lead=0):
        """Fill AllyMotion `m` for player index `me`, staying with player index `lead` (the human)."""
        s.t += dt
        m.reset()
        m.axis, m.interact_h, m.block_h = 0, False, False
        p, human = arena.players[me], arena.players[lead]
        if p.down or arena.state != "play": return
        if s.avoid(arena, p, m): return  # leave a hazard column / dash an incoming shot (same as the careful bot)
        if abs(human.x - p.x) > LEASH and not human.down:  # too far away: go back first
            m.axis = 1 if human.x > p.x else -1
            return
        near = [e for e in s.targets(arena) if abs(e.x - human.x) < ENGAGE or human.down]
        if near:
            e = min(near, key=lambda e: abs(e.x - p.x))
            dx = e.x - p.x
            m.axis = 0 if abs(dx) < 22 else (1 if dx > 0 else -1)
            if e.state == "wind" and abs(dx) < 56 and dx * p.face >= 0:
                s.seen = s.t if s.seen is None else s.seen
                if s.t - s.seen >= REACT: m.block_h, m.axis = True, 0
                return
            s.seen = None
            if abs(dx) < 36 and s.ready(p, "slash", 0.5, 0.3): m.slash_p = True
            if s.ready(p, "cast", 9.0, 4.0): m.cast_p = True    # skills are rare: an assistant, not a damage dealer
            if s.ready(p, "cast2", 14.0, 8.0): m.cast2_p = True
            if e.y < p.y - 30 and s.ready(p, "jump", 1.5): m.jump_p = True
            return
        s.seen = None
        ch = arena.chest if (arena.chest and p.i not in arena.chest["used"] and human.i in arena.chest["used"]) else None
        if ch:  # the boss chest, once the human has chosen
            m.axis = 0 if abs(ch["x"] - p.x) < 10 else (1 if ch["x"] > p.x else -1)
            m.interact_h = abs(ch["x"] - p.x) < 20
        elif abs(human.x - p.x) > STAY:
            m.axis = 1 if human.x > p.x else -1
            if m.axis * (human.x - p.x) > 120 and p.ground and s.ready(p, "hop", 1.5): m.jump_p = True
