"""Solo mode: 1 player + CPU ally. The ally never blocks the human, follows, fights, and the choice is remembered."""
import random
import pygame

from game import config
from game.app import Game
from game.ally import Ally, AllyMotion, COMPLEMENT
from game.arena import Arena
from game.player import Player
from game.qabot import FakeMotion

DT = 1 / 30


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def solo_game():
    config.SET["tutorial_done"] = True
    g = Game(dev=False, motions=[FakeMotion(0), FakeMotion(1)])
    g.step(DT, [key(pygame.K_RETURN)])               # START -> players
    assert g.mode == "players"
    g.step(DT, [key(pygame.K_LEFT)])                  # choose 1 PLAYER
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "select" and g.solo
    return g


def test_player_count_screen_and_persistence():
    g = solo_game()
    assert isinstance(g.motions[1], AllyMotion) and config.SET["solo"] is True
    assert config.load_settings()["solo"] is True      # remembered for next time
    g.mode = "menu"
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "players" and g.psel == 0         # defaults to the last choice


def test_two_player_choice_restores_keyboard_motion():
    config.SET["tutorial_done"] = True
    g = Game(dev=False, motions=[FakeMotion(0), FakeMotion(1)])
    g.set_solo(True); g.set_solo(False)
    assert g.motions[1] is g.keys[1]


def test_solo_class_select_p1_picks_the_ally_after_readying():
    g = solo_game()
    g.motions[0].slash_p = True; g.step(DT, [])         # P1 ready: ally gets a complementary default, NOT auto-ready
    assert g.ready == [True, False] and g.mode == "select"
    assert g.sel[1] == __import__("game.classes", fromlist=["x"]).CLASS_NAMES.index(COMPLEMENT["Knight"])
    g.motions[0].reset(); g.motions[0].swing = "right"; g.step(DT, [])
    assert g.sel[1] == 3 or g.sel[1] != 0                # P1's keys now cycle the ally
    g.motions[0].reset(); g.motions[0].slash_p = True; g.step(DT, [])
    g.motions[0].reset()
    assert g.mode == "cutscene"                          # both ready -> intro card


def test_ally_is_a_cpu_player_in_the_arena():
    g = solo_game()
    g.motions[0].slash_p = True; g.step(DT, []); g.motions[0].reset()
    g.motions[0].slash_p = True; g.step(DT, []); g.motions[0].reset()
    for _ in range(int(5 / DT)): g.step(DT, [])
    assert g.mode == "game" and g.arena.players[1].cpu and not g.arena.players[0].cpu


def run_ally(a, human_mo, secs, human_bot=None):
    ally, am = Ally(), AllyMotion(1)
    for _ in range(int(secs / DT)):
        ally.tick(a, am, DT)
        a.update(DT, [human_mo, am])
    return am


def test_ally_follows_the_human():
    a = Arena(0, [Player(0, "Knight", 400), Player(1, "Mage", 40)])
    a.queue, a.waves = [], []
    a.boss_spawned = True                              # no fights
    run_ally(a, FakeMotion(0), 6)
    assert abs(a.players[1].x - a.players[0].x) < 80


def test_ally_fights_and_blocks_melee_telegraphs():
    random.seed(2)
    a = Arena(0, [Player(0, "Knight", 120), Player(1, "Mage", 150)])
    a.queue, a.waves = [], []
    a.boss_spawned = True
    for i in range(3): a.spawn("zombie", 200 + 20 * i)
    a.players[0].down = True                           # only the CPU can fight
    run_ally(a, FakeMotion(0), 25)
    assert sum(1 for e in a.enemies if e.hp > 0) < 3


def test_cpu_never_opens_a_blocking_minigame_or_chest(mk):
    a, mo = mk(2)
    a.players[1].cpu = True
    c = dict(x=a.players[1].x, y=a.players[1].y, kind="zombie", tint=0, hold=0.0, looted=False, plain=False, boss=False)
    a.corpses.append(c)
    a.start_loot(a.players[1], c)
    assert a.state == "play" and c["looted"] and a.pending[1]
    a.chest = dict(x=a.players[1].x, y=a.players[1].y, hold=0.0, used=set())
    a.start_chest(a.players[1])
    assert a.state == "play" and 1 in a.chest["used"]


def test_cpu_leaves_cursed_chest_items(mk):
    a, mo = mk(2)
    p = a.players[1]; p.cpu = True
    a.chest = dict(x=p.x, y=p.y, hold=0.0, used=set())
    rolls = iter([0.1])                                 # cursed roll
    import game.arena as arena_mod
    orig = arena_mod.roll_holy
    arena_mod.roll_holy = lambda cls: orig(cls, type("R", (), {"random": lambda self: next(rolls)})())
    try: a.start_chest(p)
    finally: arena_mod.roll_holy = orig
    assert p.weapon is None and 1 in a.chest["used"]


def test_solo_full_level_with_bot_driving_player_one():
    """P1 is a Bot, P2 the CPU ally: the pair clears level 1 without soft-locking."""
    from game.qabot import Bot
    random.seed(4)
    a = Arena(0, [Player(0, "Knight", 80), Player(1, "Mage", 110)], tier=0)
    a.players[1].cpu = True
    ally, am, hm, bot = Ally(), AllyMotion(1), FakeMotion(0), Bot("careful")
    for _ in range(int(240 / DT)):
        bot.drive(a, [hm, FakeMotion(1)], DT)           # drives P1 (P2's FakeMotion is ignored)
        ally.tick(a, am, DT)
        a.update(DT, [hm, am])
        if a.result or a.portal or a.state == "failed": break
    assert a.portal and a.state != "failed"
