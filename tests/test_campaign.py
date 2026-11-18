"""End-to-end: a bot (with god mode so it can't die) plays the whole campaign through the real Game state machine."""
import random

import pygame

from game import config
from game.app import Game
from game.levels import NUM_LEVELS
from game.qabot import FakeMotion, Bot

DT = 1 / 30


def test_full_campaign_to_victory_via_real_game_loop():
    random.seed(7)
    config.SET["tutorial_done"] = True
    g = Game(dev=False, motions=[FakeMotion(0), FakeMotion(1)])
    bot = Bot("loot")
    g.step(DT, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])
    g.step(DT, [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)])   # players screen: 2 players
    g.step(DT, [])
    for m in g.motions: m.slash_p = True
    g.step(DT, [])
    seen_levels, seen_modes = set(), set()
    for step in range(int(60 * 60 / DT)):                 # at most 60 simulated minutes
        for m in g.motions: m.reset()
        if g.mode == "game":
            g.arena.god = True
            seen_levels.add(g.arena.area)
            bot.drive(g.arena, g.motions, DT)
        g.step(DT, [])
        seen_modes.add(g.mode)
        if g.mode == "victory": break
    assert g.mode == "victory", f"stuck in {g.mode} at level {g.area + 1} after {step} steps"
    assert seen_levels == set(range(NUM_LEVELS)) and {"cutscene", "game", "victory"} <= seen_modes
    assert len(g.inv[0]) + len(g.inv[1]) > 0               # looted along the way
    assert any(it for gd in g.gear for it in gd.values())  # level 3 chest / loot: the bot ends up with gear


def test_content_is_winnable_with_multipliers_off():
    """Content balance (enemy/boss design) on its own: with difficulty scaling off, a basic careful bot should win most levels."""
    from game.arena import Arena
    from game.player import Player
    wins = {}
    for lvl in range(NUM_LEVELS):
        w = 0
        for seed in range(3):
            random.seed(lvl * 100 + seed)
            a = Arena(lvl, [Player(0, "Knight", 80), Player(1, "Tank", 110)], tier=0)
            mo, bot = [FakeMotion(0), FakeMotion(1)], Bot("careful")
            t = 0.0
            while t < 240 and not a.result and a.state != "failed":
                bot.drive(a, mo, DT); a.update(DT, mo); t += DT
            w += bool(a.portal)
        wins[lvl + 1] = w
    assert all(w >= 2 for w in wins.values()), f"wins out of 3 per level: {wins}"
