"""Shared headless test helpers (bots live in game.qabot so --selftest can use them too)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from game.qabot import FakeMotion, Bot, run_bot  # noqa: E402,F401
