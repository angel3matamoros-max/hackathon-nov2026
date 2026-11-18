import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random  # noqa: E402
import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    """Never touch the real rogue_settings.json; start every test from default settings and a fixed RNG seed."""
    from game import config
    monkeypatch.setattr(config, "SAVE", str(tmp_path / "rogue_settings.json"))
    config.SET.clear()
    config.SET.update(config.load_settings())
    random.seed(12345)
    yield


@pytest.fixture
def mk():
    """Factory: mk(level, ("Knight", "Mage"), **arena_kwargs) -> (arena, [FakeMotion, FakeMotion])."""
    from game.arena import Arena
    from game.player import Player
    from game.qabot import FakeMotion

    def make(level=0, classes=("Knight", "Mage"), waves=False, **kw):
        """waves=False clears the level's spawn queue so a test only sees the enemies it spawns itself."""
        players = [Player(i, c, 80 + 30 * i) for i, c in enumerate(classes)]
        a = Arena(level, players, **kw)
        if not waves: a.queue = []
        return a, [FakeMotion(i) for i in range(len(players))]
    return make
