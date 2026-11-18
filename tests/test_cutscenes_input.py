import pygame
import pytest

from game.cutscenes import IntroCard, AscendCutscene, Ending
from game.inputs import Motion
from game.levels import NUM_LEVELS
from game.qabot import FakeMotion


@pytest.mark.parametrize("make", [
    lambda: IntroCard(0), lambda: IntroCard(NUM_LEVELS - 1), lambda: AscendCutscene(0, 1, ["Knight", "Mage"]),
    lambda: AscendCutscene(NUM_LEVELS - 2, NUM_LEVELS - 1, ["Rogue", "Tank"]), lambda: Ending(["Fighter", "Knight"])])
def test_cutscene_runs_draws_and_finishes(make):
    c = make()
    n = 0
    while not c.update(1 / 30):
        c.draw(); n += 1
        assert n < 1000
    c.draw()
    assert 30 < n < 400                                    # roughly 1-13 s: short enough to be "simple", long enough to read


def test_cutscene_skip_finishes_immediately():
    c = IntroCard(2)
    c.skip()
    assert c.done


def test_cutscene_durations_are_short():
    assert IntroCard.dur <= 3.5 and AscendCutscene.dur <= 6.5 and Ending.dur <= 8


def test_motion_tab_sets_skip_and_other_fields_still_work():
    m = Motion(0)
    m.update([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB)], 1 / 60)
    assert m.skip_p
    m.update([], 1 / 60)
    assert not m.skip_p                                    # one-frame pulse
    m.update([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)], 1 / 60)
    assert m.slash_p and m.flick


def test_fake_motion_has_the_same_interface_as_motion():
    """Controller seam: anything the game reads from Motion must exist on every input backend (keyboard, bots, future GY-521)."""
    assert set(vars(Motion(0))) == set(vars(FakeMotion(0)))


def test_game_code_reads_only_motion_fields():
    """Guard the seam: gameplay modules must not poll the keyboard themselves (only inputs.py and the menu layer may)."""
    import pathlib, re
    root = pathlib.Path(__file__).resolve().parents[1] / "game"
    for f in ("arena.py", "player.py", "enemies.py", "bosses.py", "loot.py", "cutscenes.py"):
        src = (root / f).read_text()
        assert not re.search(r"key\.get_pressed|pygame\.key\.|event\.get", src), f
