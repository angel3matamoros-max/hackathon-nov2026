"""
ROGUE LOOT - 2-player co-op pixel-art action game.
Install:  uv sync        Run:  uv run python main.py        (or .venv/bin/python main.py)

Menu: Start / Tutorial / Settings (rebind keys) / Exit. First launch plays the tutorial.
Menus: W/S or Up/Down, Enter or Space to select, Esc to go back.
Default keys (all rebindable in Settings, saved to rogue_settings.json):
  P1: A/D move, W jump (x2 / wall-jump), S drop / fast-fall, LShift dash, J slash, K block (hold), L skill 1, U skill 2, E loot (hold)
  P2: Left/Right move, Up jump (x2 / wall-jump), Down drop / fast-fall, RShift dash, , slash, . block (hold), / skill 1, M skill 2, Enter loot (hold)

Controller plan: each player has a Motion object (game/inputs.py) - subclass it for the GY-521.
"""
from game.app import main

if __name__ == "__main__":
    main()
