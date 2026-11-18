"""
ROGUE LOOT - 2-player co-op pixel-art action game (castle climb: 6 levels, a boss each).
Install:  uv sync        Run:  uv run python main.py        (or .venv/bin/python main.py)

Menu: Start / Tutorial / Settings (rebind keys) / Exit. First launch plays the tutorial (Tab or the on-screen button skips it).
Menus: W/S or Up/Down, Enter or Space to select, Esc to go back.
Default keys (all rebindable in Settings, saved to rogue_settings.json):
  P1: A/D move, W jump (x2 / wall-jump), S drop / fast-fall, LShift dash, J slash, K block (hold), L skill 1, U skill 2, E loot (hold)
  P2: Left/Right move, Up jump (x2 / wall-jump), Down drop / fast-fall, RShift dash, , slash, . block (hold), / skill 1, M skill 2, Enter loot (hold)

Developer mode:  python main.py --dev            (menu gets "DEV: LEVEL SELECT"; in a level press F1 for the dev keys)
                 python main.py --level 3        (jump straight into level 3, dev keys on)
                 python main.py --gallery        (enemy gallery: Y spawns every enemy / boss in turn)
Self-test:       python main.py --selftest       (headless smoke test of every screen, level, boss and cutscene)

Hand controller: plugged in, it drives player 1 (game/padbridge.py). Tune it with --pad-monitor (see docs/controller-protocol.md).
  python main.py --pad-monitor    print the controller's raw values and gestures, then exit
"""
import argparse
import os
import sys


def parse(argv=None):
    ap = argparse.ArgumentParser(description="Rogue Loot")
    ap.add_argument("--dev", action="store_true", help="developer mode (level warp, god mode, hitboxes...)")
    ap.add_argument("--level", type=int, metavar="N", help="start directly in level N (1-6), implies --dev")
    ap.add_argument("--gallery", action="store_true", help="start in the enemy gallery, implies --dev")
    ap.add_argument("--selftest", action="store_true", help="run a headless smoke test and exit")
    ap.add_argument("--pad-monitor", action="store_true", help="print the hand controller's raw values and gestures (for tuning) and exit")
    return ap.parse_args(argv)


if __name__ == "__main__":
    args = parse()
    if args.selftest:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    from game import config
    config.DEV = args.dev or os.environ.get("ROGUE_DEV") == "1" or args.level is not None or args.gallery
    if args.pad_monitor:
        from game.padbridge import monitor
        monitor()
        sys.exit(0)
    if args.selftest:
        from game.selftest import run
        sys.exit(run())
    from game.app import main
    main(dev=config.DEV, level=args.level, gallery=args.gallery)
