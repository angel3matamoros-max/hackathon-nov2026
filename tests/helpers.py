"""Shared headless test helpers: a scriptable Motion and a deterministic bot."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


class FakeMotion:
    """Same fields as game Motion (see Motion docstring) but fully scriptable."""

    def __init__(s, i):
        s.i, s.axis, s.tilt, s.shake = i, 0, 0.0, 0.0
        s.jump_h = s.down_h = s.block_h = s.interact_h = False
        s.reset()

    def reset(s):
        s.jump_p = s.down_p = s.dash_p = s.slash_p = s.cast_p = s.cast2_p = s.flick = s.skip_p = False
        s.swing = None

    def update(s, events, dt):  # parity with Motion.update; scripted tests set fields directly
        pass


def bot_step(arena, mo, t, enemy_attr="enemies"):
    """Deterministic bot: walk to nearest enemy/corpse, slash when close, cast on cooldown."""
    for m in mo:
        m.reset()
    foes = [e for e in getattr(arena, enemy_attr) if getattr(e, "kind", "") != "dummy"]
    for p in arena.players:
        m = mo[p.i]
        m.axis = 0
        m.interact_h = False
        if p.down:
            continue
        if foes:
            e = min(foes, key=lambda e: abs(e.x - p.x))
            dx = e.x - p.x
            m.axis = 0 if abs(dx) < 22 else (1 if dx > 0 else -1)
            if abs(dx) < 36 and int(t * 60) % 20 == p.i * 7:
                m.slash_p = True
            if int(t * 60) % 180 == p.i * 31:
                m.cast_p = True
            if int(t * 60) % 240 == 100 + p.i * 31:
                m.cast2_p = True
            if e.y < p.y - 30 and int(t * 60) % 45 == 0:
                m.jump_p = True
        else:
            m.axis = 1  # head for the portal at the right edge
    return mo


def run_bot(arena, seconds, dt=1 / 60):
    mo = [FakeMotion(p.i) for p in arena.players]
    t = 0.0
    for _ in range(int(seconds / dt)):
        bot_step(arena, mo, t)
        arena.update(dt, mo)
        t += dt
        if arena.result:
            break
    return mo
