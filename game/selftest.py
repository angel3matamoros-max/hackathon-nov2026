"""Headless smoke test: python main.py --selftest. Drives every screen, level, boss and cutscene; exit code 0 = healthy."""
import os
import random
import tempfile
import time
import pygame
from . import config
from .config import *


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def run():
    # never touch the player's real settings file
    config.SAVE = os.path.join(tempfile.mkdtemp(), "rogue_settings.json")
    config.SET.update(config.load_settings())
    from .app import Game, init_display
    from .qabot import FakeMotion, Bot
    from .levels import NUM_LEVELS, get_bg
    from .bosses import BOSSES
    from .enemies import ESTATS
    from .sprites import ENEMY, CORPSE
    init_display()
    t0, fails, dt = time.time(), [], 1 / 30

    def check(name, cond, info=""):
        print(("  ok   " if cond else "  FAIL ") + name + (f"  {info}" if info and not cond else ""))
        if not cond: fails.append(name)

    print("selftest: assets")
    check("every enemy kind has sprite + corpse", all((k, 0) in ENEMY and (k, 0) in CORPSE for k in ESTATS))
    check("every level has waves + a known boss", all(l["waves"] and l["boss"] in BOSSES for l in __import__("game.levels", fromlist=["LEVELS"]).LEVELS))
    for i in range(NUM_LEVELS): get_bg(i)

    print("selftest: menus")
    g = Game(dev=True, motions=[FakeMotion(0), FakeMotion(1)])
    config.SET["tutorial_done"] = True
    for _ in range(3): g.step(dt, [])
    g.step(dt, [key(pygame.K_DOWN)])
    g.step(dt, [key(pygame.K_DOWN)])
    g.step(dt, [key(pygame.K_RETURN)])  # settings
    check("settings screen opens", g.mode == "settings")
    for _ in range(3): g.step(dt, [])
    g.step(dt, [key(pygame.K_ESCAPE)])
    check("back to menu", g.mode == "menu")

    print("selftest: tutorial + skip")
    config.SET["tutorial_done"] = False
    g.msel = 1
    g.step(dt, [key(pygame.K_RETURN)])
    check("tutorial starts", g.mode == "game" and g.arena.tut)
    for _ in range(30): g.step(dt, [])
    g.motions[0].skip_p = True
    g.first_run = True
    g.step(dt, [])
    check("skip leaves the tutorial and marks it done", g.mode == "select" and config.SET["tutorial_done"] is True)

    print("selftest: class select -> intro cutscene -> level 1")
    g.step(dt, [])
    for m in g.motions: m.slash_p = True
    g.step(dt, [])
    for m in g.motions: m.reset()
    check("both ready starts the intro cutscene", g.mode == "cutscene")
    for _ in range(400):
        g.step(dt, [])
        if g.mode == "game": break
    check("intro cutscene ends in the level", g.mode == "game" and g.arena.area == 0)

    print("selftest: every level + boss (bot plays, dev shortcuts)")
    bot = Bot("careful")
    for lvl in range(NUM_LEVELS):
        random.seed(lvl)
        g.warp(lvl)
        a = g.arena
        for _ in range(int(25 / dt)):
            bot.drive(a, g.motions, dt); g.step(dt, [])
            if g.mode != "game": break
        check(f"level {lvl + 1} runs 25s without error", True)
        g.dev.handle(g, [pygame.K_b])  # boss now
        a = g.arena
        check(f"level {lvl + 1} boss spawns", a.boss is not None and a.boss.kind == a.A["boss"])
        g.dev.handle(g, [pygame.K_g])
        for _ in range(int(20 / dt)):
            bot.drive(a, g.motions, dt); g.step(dt, [])
        g.dev.handle(g, [pygame.K_x])
        for _ in range(8): bot.drive(a, g.motions, dt); g.step(dt, [])
        check(f"level {lvl + 1} boss can be defeated -> portal opens", a.boss.hp <= 0 and a.portal)
        g.dev.handle(g, [pygame.K_g])

    print("selftest: cutscenes + victory")
    g.warp(0)
    g.dev.handle(g, [pygame.K_n])
    g.step(dt, [])
    g.step(dt, [])
    check("finishing a level starts the ascend cutscene", g.mode == "cutscene")
    for _ in range(600):
        g.step(dt, [])
        if g.mode != "cutscene": break
    check("ascend + intro end in level 2", g.mode == "game" and g.arena.area == 1)
    g.warp(NUM_LEVELS - 1)
    g.dev.handle(g, [pygame.K_n]); g.step(dt, [])
    for _ in range(600):
        g.step(dt, [])
        if g.mode == "victory": break
    check("beating the last level shows victory", g.mode == "victory")
    g.step(dt, [key(pygame.K_RETURN)])
    check("victory returns to menu", g.mode == "menu")

    print(f"selftest: {'FAILED ' + str(fails) if fails else 'all checks passed'} in {time.time() - t0:.1f}s")
    return 1 if fails else 0
