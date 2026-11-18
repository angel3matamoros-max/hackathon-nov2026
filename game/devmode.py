"""Developer mode (python main.py --dev  or  ROGUE_DEV=1): warp between levels, boss/cutscene shortcuts, god mode, hitboxes.
Never saved to settings. Keys are chosen not to clash with the default P1/P2 bindings."""
import random
import pygame
from .config import *
from .gfx import text
from .levels import NUM_LEVELS
from .enemies import ESTATS
from .bosses import BOSSES
from .cutscenes import IntroCard, AscendCutscene, Ending

HELP = [
    "DEV MODE KEYS", "1-6: warp to level     [ / ]: prev / next level", "N: finish level (ascend cutscene)   B: spawn boss now",
    "X: kill everything   G: god mode   V: fly (noclip)", "T: cycle difficulty tier   Y: spawn next enemy type",
    "C: preview cutscenes   H: hitboxes + FPS   F1: this help",
]
SPAWNABLE = [k for k in ESTATS if k != "dummy" and k not in BOSSES] + list(BOSSES)


class Dev:
    def __init__(s):
        s.help, s.kind_i, s.cut_i, s.tier, s.fps = False, 0, 0, None, 0.0

    def handle(s, g, keys):
        a = g.arena
        if a is None or a.tut: return
        for k in keys:
            if pygame.K_1 <= k <= pygame.K_6 and k - pygame.K_1 < NUM_LEVELS:
                g.warp(k - pygame.K_1); return
            if k == pygame.K_LEFTBRACKET: g.warp(max(0, a.area - 1)); return
            if k == pygame.K_RIGHTBRACKET: g.warp(min(NUM_LEVELS - 1, a.area + 1)); return
            if k == pygame.K_n: a.result = "next"
            elif k == pygame.K_b and not a.gallery:
                a.queue = []
                a.enemies = [e for e in a.enemies if e.kind == "dummy" or e.is_boss]
                if not a.boss_spawned: a.spawn_boss()
            elif k == pygame.K_x:
                for e in a.enemies:
                    if e.kind != "dummy": e.hp = 0
            elif k == pygame.K_g: a.god = not a.god
            elif k == pygame.K_v:
                for p in a.players: p.fly = not p.fly
            elif k == pygame.K_t:
                s.tier = ((a.tier if s.tier is None else s.tier) + 1) % NUM_LEVELS
                g.tier_override = s.tier
                a.tier = s.tier
                a.taken, a.dealt = difficulty(a.tier)
            elif k == pygame.K_y:
                kind = SPAWNABLE[s.kind_i % len(SPAWNABLE)]
                s.kind_i += 1
                a.spawn(kind, x=random.choice((60, W - 60)), dscale=1.0)
                a.banner = [f"spawned: {kind}", 1.5]
            elif k == pygame.K_c: s.preview(g)
            elif k == pygame.K_h: a.debug = not a.debug
            elif k == pygame.K_F1: s.help = not s.help

    def preview(self, g):
        a, n = g.arena, self.cut_i % 3
        self.cut_i += 1
        cuts = [[IntroCard(a.area)], [AscendCutscene(a.area, min(a.area + 1, NUM_LEVELS - 1), g.heroes)], [Ending(g.heroes)]][n]
        g.play(cuts, lambda: setattr(g, "mode", "game"))

    def overlay(s, g, dt):
        a = g.arena
        s.fps = s.fps * 0.9 + (1 / dt if dt > 0 else 0) * 0.1
        if a is None: return
        text(f"DEV  L{a.area + 1} tier{a.tier}  x{a.dealt:.2f}/x{a.taken:.2f}  F1=help" + (f"  {s.fps:.0f}fps" if a.debug else ""), 4, H - 11, (120, 255, 150))
        if s.help:
            for i, ln in enumerate(HELP): text(ln, 8, 78 + i * 11, (120, 255, 150) if i else GOLD)
