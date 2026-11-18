import pygame
import pytest

from game.bosses import BOSSES, BOSS_HP
from game.config import W, FLOOR
from game.enemies import ESTATS
from game.levels import LEVELS, NUM_LEVELS, AMB_MOVES, waves_of, make_bg, new_ambient, move_ambient
from game.sprites import ENEMY, CORPSE


def test_six_levels():
    assert NUM_LEVELS == 6 and len(BOSS_HP) >= NUM_LEVELS


@pytest.mark.parametrize("i", range(NUM_LEVELS))
def test_level_data_is_complete(i):
    L = LEVELS[i]
    ws = waves_of(L)
    assert len(ws) >= 3 and all(wv for wv in ws)    # fought wave by wave, never all at once
    assert all(n > 0 and k in ESTATS and (k, 0) in ENEMY and (k, 0) in CORPSE for wv in ws for k, n in wv)
    assert L["boss"] in BOSSES and (L["boss"], 0) in ENEMY
    assert L["amb"][3] in AMB_MOVES
    for px, py, pw in L["plats"]:
        assert 0 <= px and px + pw <= W and py < FLOOR


@pytest.mark.parametrize("i", range(NUM_LEVELS))
def test_background_builds_and_ambient_moves(i):
    sf = make_bg(i)
    assert sf.get_size() == (480, 270)
    parts = new_ambient(i)
    for _ in range(100): move_ambient(i, parts, 1.0, 1 / 30)
    assert all(0 <= m["x"] < W and 0 <= m["y"] <= FLOOR for m in parts)


def test_spec_level_rosters():
    kinds = lambda i: {k for wv in waves_of(LEVELS[i]) for k, _ in wv}  # noqa: E731
    assert kinds(0) == {"zombie", "skeleton"}                       # level 1: simple weak zombies and skeletons
    assert kinds(1) == {"bunny", "wolfman", "catman", "wolf"}       # level 2: bunny / wolf / cat beast men (+ plain wolves)
    assert kinds(2) == {"knight"} and LEVELS[2].get("chest")        # level 3: holy knights + chest
    assert "lich" in kinds(3) and "gunman" in kinds(4) and "alien" in kinds(5)
    assert [LEVELS[i]["boss"] for i in range(6)] == ["gravekeeper", "beastlord", "paladin", "archlich", "don", "tycoon"]
    assert not any(LEVELS[i].get("chest") for i in (0, 1, 3, 4, 5))


def test_level1_zombies_are_weak():
    assert ESTATS["zombie"]["hp"] <= ESTATS["skeleton"]["hp"] and ESTATS["zombie"]["dmg"] < ESTATS["skeleton"]["dmg"]


def test_every_enemy_and_boss_has_sprite_frames():
    for k in ESTATS:
        frames = ENEMY[(k, 0)]
        assert frames and all(isinstance(f, pygame.Surface) for f in frames)


def test_boss_hp_is_positive_and_ordered_sensibly():
    assert all(h > 0 for h in BOSS_HP)
