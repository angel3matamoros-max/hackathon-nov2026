"""QA outcome screenshots (headless) -> qa/shots/*.png. The QA agent views these to check visuals.
Run:  .venv/bin/python qa/render_shots.py"""
import os
import random
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame  # noqa: E402
from game import config  # noqa: E402

config.SAVE = os.path.join(tempfile.mkdtemp(), "s.json")
from game.app import Game, init_display  # noqa: E402
from game.qabot import FakeMotion, Bot  # noqa: E402
from game.gfx import main_cv  # noqa: E402
from game.levels import NUM_LEVELS  # noqa: E402
from game.cutscenes import IntroCard, AscendCutscene, Ending  # noqa: E402
from game.loot import roll_holy  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(OUT, exist_ok=True)
init_display()
DT = 1 / 30


def snap(name):
    pygame.image.save(pygame.transform.scale(main_cv, (960, 540)), os.path.join(OUT, name + ".png"))
    print("saved", name)


def play(g, bot, secs):
    for _ in range(int(secs / DT)):
        bot.drive(g.arena, g.motions, DT)
        g.step(DT, [])


def main():
    g = Game(dev=True, motions=[FakeMotion(0), FakeMotion(1)])
    g.heroes = ["Knight", "Mage"]
    bot = Bot("careful")
    for lvl in range(NUM_LEVELS):
        random.seed(100 + lvl)
        g.warp(lvl)
        play(g, bot, 9)
        snap(f"level{lvl + 1}_fight")
        g.dev.handle(g, [pygame.K_b])
        a = g.arena
        play(g, bot, 2.0)
        a.boss.rest = 0.0
        for _ in range(200):  # run until the boss is mid-telegraph
            bot.drive(a, g.motions, DT); g.step(DT, [])
            if a.boss.state == "wind": break
        snap(f"level{lvl + 1}_boss_telegraph")
        play(g, bot, 1.0)
        snap(f"level{lvl + 1}_boss_fight")
    # holy chest modal (one holy, one cursed)
    g.warp(2)
    a = g.arena
    g.dev.handle(g, [pygame.K_b]); g.dev.handle(g, [pygame.K_x]); play(g, bot, 1)
    snap("level3_chest_dropped")
    for cursed in (False, True):
        r = random.Random(1 if cursed else 7)
        while (roll_holy("Mage", random.Random(r.random())) ["cursed"]) != cursed:
            r.random()
        a.start_chest(a.players[1]); a.cm["offer"] = roll_holy("Mage", type("R", (), {"random": lambda self: 0.1 if cursed else 0.9})())
        a.cm["t"] = 1.0
        a.draw()
        snap("chest_cursed" if cursed else "chest_holy")
        a.state, a.cm = "play", None
    # cutscenes
    for name, c, ts in (("intro", IntroCard(2), (1.2,)), ("ascend", AscendCutscene(0, 1, g.heroes), (0.5, 2.4, 4.4)),
                        ("ascend_top", AscendCutscene(4, 5, g.heroes), (2.4,)), ("ending", Ending(g.heroes), (3.5,))):
        t = 0.0
        for target in ts:
            while t < target:
                c.update(DT); t += DT
            c.draw()
            snap(f"cutscene_{name}_{target:.1f}")
    # tutorial with skip button, menu, dev menu
    g.start_tutorial(True)
    for _ in range(5): g.step(DT, [])
    snap("tutorial_skip_button")
    g.mode = "menu"; g.step(DT, []); snap("menu_dev")
    g.mode, g.dsel = "devmenu", 0; g.step(DT, []); snap("dev_menu")
    g.warp(0, gallery=True)
    g.dev.help = True
    for _ in range(3): g.step(DT, [])
    snap("dev_help")


if __name__ == "__main__":
    main()
