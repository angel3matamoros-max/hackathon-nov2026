"""Input layer. Every gameplay system reads Motion fields only, never the keyboard directly."""
import pygame
from .config import *


class Motion:
    """One per player. Keyboard now; for the GY-521 make a subclass that fills these fields:
       axis -1/0/1 (walk) | jump_h, down_h, block_h, interact_h (held)
       jump_p, down_p, dash_p, slash_p, cast_p, cast2_p (one frame)
       tilt -1..1, shake 0..1, swing 'left'/'right'/'up'/'down', flick (used by loot mini-games), skip_p (skip tutorial/cutscene)."""

    def __init__(s, i):
        s.i, s.axis, s.tilt, s.shake = i, 0, 0.0, 0.0
        s.jump_h = s.down_h = s.block_h = s.interact_h = False
        s.reset()

    def reset(s):
        s.jump_p = s.down_p = s.dash_p = s.slash_p = s.cast_p = s.cast2_p = s.flick = s.skip_p = False
        s.swing = None

    def update(s, events, dt):
        k, p = SET["keys"][s.i], pygame.key.get_pressed()
        s.axis = int(p[k["right"]]) - int(p[k["left"]])
        s.tilt += (s.axis - s.tilt) * min(1, dt * 8)
        s.jump_h = bool(p[k["jump"]])
        s.down_h = bool(p[k["down"]])
        s.block_h = bool(p[k["block"]])
        s.interact_h = bool(p[k["interact"]])
        s.reset()
        for e in events:
            if e.type != pygame.KEYDOWN:
                continue
            if e.key == k["jump"]: s.jump_p, s.swing = True, "up"
            if e.key == k["down"]: s.down_p, s.swing = True, "down"
            if e.key == k["left"]: s.swing = "left"
            if e.key == k["right"]: s.swing = "right"
            if e.key == k["dash"]: s.dash_p = True
            if e.key == k["slash"]:
                s.slash_p = s.flick = True
                s.shake = min(1, s.shake + 0.15)
            if e.key == k["cast"]: s.cast_p = True
            if e.key == k["cast2"]: s.cast2_p = True
            if e.key == pygame.K_TAB: s.skip_p = True  # skip tutorial / cutscene (a controller button can set this too)
        s.shake = max(0, s.shake - dt * 0.7)


def make_motions(backend="keyboard"):
    """Factory for the two players' input objects. This is the single place a new controller plugs in:
    a future backend (e.g. "gy521": GyroMotion subclasses Motion and fills the same fields from serial data,
    see docs/controller-protocol.md) is added here. Nothing else in the game needs to change."""
    if backend == "keyboard":
        return [Motion(0), Motion(1)]
    raise ValueError(f"unknown input backend {backend!r} (available: 'keyboard')")
