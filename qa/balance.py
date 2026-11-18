"""Balance report: bot-driven runs of every level -> win rate, clear time, boss time-to-kill, damage taken.
Run:  .venv/bin/python qa/balance.py [seeds=3] [skill=careful|naive] [--flat]   (--flat turns the per-level multipliers off)
The bots are only a rough proxy for a human (the 'careful' bot blocks melee and sidesteps telegraphs) - use the trend, not exact numbers."""
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.arena import Arena  # noqa: E402
from game.player import Player  # noqa: E402
from game.levels import NUM_LEVELS  # noqa: E402
from game.qabot import FakeMotion, Bot  # noqa: E402
from game.config import difficulty  # noqa: E402

DT = 1 / 30
TEAMS = [("Knight", "Tank"), ("Mage", "Rogue"), ("Fighter", "Knight")]


def run_level(level, team, seed, skill, limit=240.0, tier=None):
    random.seed(seed)
    a = Arena(level, [Player(0, team[0], 80), Player(1, team[1], 110)], tier=tier)
    mo, bot = [FakeMotion(0), FakeMotion(1)], Bot(skill)
    boss_t = kill_t = None
    t = 0.0
    while t < limit and not a.result and a.state != "failed":
        bot.drive(a, mo, DT)
        a.update(DT, mo)
        t += DT
        if a.boss_spawned and boss_t is None: boss_t = t
        if a.portal and kill_t is None: kill_t = t
    won = a.result == "next" or a.portal
    hp_left = sum(p.hp for p in a.players) / sum(p.maxhp for p in a.players)
    return dict(won=won, t=t, boss_t=boss_t, ttk=(kill_t - boss_t) if (kill_t and boss_t) else None, hp=hp_left)


def main(seeds=3, skill="careful", flat=False):
    print(f"bot skill: {skill}   seeds/team: {seeds}   difficulty multipliers: {'OFF (content only)' if flat else 'ON'}")
    print(f"{'lvl':>3} {'take':>5} {'deal':>5} {'win%':>5} {'waves(s)':>9} {'boss TTK(s)':>12} {'team HP left':>13}")
    rows = []
    for lvl in range(NUM_LEVELS):
        res = [run_level(lvl, tm, 1000 * lvl + s, skill, tier=0 if flat else None) for tm in TEAMS for s in range(seeds)]
        w = [r for r in res if r["won"]]
        take, deal = difficulty(0 if flat else lvl)
        pct = 100 * len(w) / len(res)
        waves = sum(r["boss_t"] for r in res if r["boss_t"]) / max(1, sum(1 for r in res if r["boss_t"]))
        ttk = sum(r["ttk"] for r in w if r["ttk"]) / max(1, sum(1 for r in w if r["ttk"]))
        hp = sum(r["hp"] for r in res) / len(res)
        rows.append((lvl + 1, take, deal, pct, waves, ttk, hp))
        print(f"{lvl + 1:>3} {take:>5.2f} {deal:>5.2f} {pct:>5.0f} {waves:>9.1f} {ttk:>12.1f} {hp:>12.0%}")
    return rows


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3, sys.argv[2] if len(sys.argv) > 2 else "careful", "--flat" in sys.argv)
