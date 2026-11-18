"""Game state machine: menu, tutorial skip, class select, cutscenes, level progression, retry, victory, dev mode."""
import pygame
import pytest

from game import config
from game.app import Game
from game.arena import SKIP_RECT
from game.levels import NUM_LEVELS
from game.qabot import FakeMotion

DT = 1 / 30


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def click(x, y):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1)


@pytest.fixture
def g():
    return Game(dev=False, motions=[FakeMotion(0), FakeMotion(1)])


@pytest.fixture
def dg():
    return Game(dev=True, motions=[FakeMotion(0), FakeMotion(1)])


def run(g, secs, ev=None):
    for _ in range(int(secs / DT)): g.step(DT, ev or [])


def to_menu_item(g, name):
    items = g.menu_items()
    g.msel = items.index(name)


# ------------------------------------------------------------------ skip tutorial
def test_first_launch_start_runs_tutorial_then_skip_by_key(g):
    assert config.SET["tutorial_done"] is False
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "game" and g.arena.tut and g.first_run
    run(g, 1)
    g.motions[0].skip_p = True
    g.step(DT, [])
    assert g.mode == "select" and config.SET["tutorial_done"] is True
    assert config.load_settings()["tutorial_done"] is True     # persisted to disk


def test_skip_tutorial_by_mouse_click_on_button(g):
    g.step(DT, [key(pygame.K_RETURN)])
    g.step(DT, [click(SKIP_RECT.centerx, SKIP_RECT.centery)])
    assert g.mode == "select" and config.SET["tutorial_done"]


def test_click_elsewhere_does_not_skip(g):
    g.step(DT, [key(pygame.K_RETURN)])
    g.step(DT, [click(5, 5)])
    assert g.mode == "game" and g.arena.tut and not config.SET["tutorial_done"]


def test_skip_button_is_drawn_during_tutorial(g):
    from game.gfx import main_cv
    g.step(DT, [key(pygame.K_RETURN)])
    g.step(DT, [])
    px = main_cv.get_at((SKIP_RECT.x, SKIP_RECT.y))[:3]
    assert px == config.STEEL_D or px == config.GOLD       # the button border


def test_replaying_tutorial_from_menu_and_skipping_returns_to_menu(g):
    config.SET["tutorial_done"] = True
    to_menu_item(g, "TUTORIAL")
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.arena.tut and not g.first_run
    g.motions[0].skip_p = True
    g.step(DT, [])
    assert g.mode == "menu"


def test_skipped_tutorial_never_shows_again_on_start(g):
    config.SET["tutorial_done"] = True
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "select"


def test_esc_leaves_tutorial_without_marking_done(g):
    g.step(DT, [key(pygame.K_RETURN)])
    g.step(DT, [key(pygame.K_ESCAPE)])
    assert g.mode == "menu" and not config.SET["tutorial_done"]


# ------------------------------------------------------------------ level progression + cutscenes
def start_game(g):
    config.SET["tutorial_done"] = True
    g.step(DT, [key(pygame.K_RETURN)])
    g.step(DT, [])
    for m in g.motions: m.slash_p = True
    g.step(DT, [])
    for m in g.motions: m.reset()


def test_class_select_leads_to_intro_cutscene_then_level_one(g):
    start_game(g)
    assert g.mode == "cutscene" and type(g.cuts[0]).__name__ == "IntroCard"
    run(g, 4)
    assert g.mode == "game" and g.arena.area == 0 and not g.arena.tut


def test_cutscene_can_be_skipped_with_esc_tab_and_slash(g):
    for how in ("esc", "tab", "slash"):
        g.mode = "menu"
        start_game(g)
        assert g.mode == "cutscene"
        if how == "esc": g.step(DT, [key(pygame.K_ESCAPE)])
        elif how == "tab": g.motions[0].skip_p = True; g.step(DT, [])
        else:
            run(g, 0.6)
            g.motions[1].slash_p = True; g.step(DT, [])
        g.motions[0].reset(); g.motions[1].reset()
        assert g.mode == "game", how


def test_finishing_a_level_plays_ascend_then_intro_then_next_level(g):
    start_game(g); run(g, 4)
    a = g.arena
    a.result = "next"
    a.pending[0].append({"name": "Sword", "tier": 1})
    g.step(DT, [])
    assert g.mode == "cutscene" and [type(c).__name__ for c in g.cuts] == ["AscendCutscene", "IntroCard"]
    assert g.inv[0] and g.area == 1
    run(g, 12)
    assert g.mode == "game" and g.arena.area == 1


def test_finishing_last_level_plays_ending_then_victory(g):
    start_game(g); run(g, 4)
    g.area = NUM_LEVELS - 1
    g.arena.result = "next"
    g.step(DT, [])
    assert [type(c).__name__ for c in g.cuts] == ["Ending"]
    run(g, 8)
    assert g.mode == "victory"
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "menu"


def test_retry_after_defeat_keeps_level_tier_and_gear(g):
    start_game(g); run(g, 4)
    g.warp(3)
    g.gear = [{"name": "x", "cursed": False, "atk": 1.25}, None]
    g.arena = g.new_arena(3)
    for p in g.arena.players: p.down = True
    run(g, 0.5)
    assert g.arena.state == "failed"
    g.motions[0].slash_p = True
    run(g, 2.0)  # result 'retry' needs the fail timer to elapse
    g.motions[0].slash_p = True
    g.step(DT, [])
    g.motions[0].reset()
    assert g.arena.area == 3 and g.arena.tier == 3 and g.arena.state == "play" and g.arena.players[0].weapon == g.gear[0]


def test_defeat_discards_unbanked_loot(g):
    start_game(g); run(g, 4)
    a = g.arena
    a.pending[0].append({"name": "Sword", "tier": 1})
    for p in a.players: p.down = True
    run(g, 0.3)
    assert a.state == "failed" and a.pending == [[], []] and g.inv == [[], []]


# ------------------------------------------------------------------ dev mode
def test_dev_menu_entry_only_in_dev_mode(g, dg):
    assert not any("DEV" in i for i in g.menu_items())
    assert any("DEV" in i for i in dg.menu_items())


def test_dev_level_select_warps_to_every_level(dg):
    to_menu_item(dg, "DEV: LEVEL SELECT")
    dg.step(DT, [key(pygame.K_RETURN)])
    assert dg.mode == "devmenu"
    for lvl in range(NUM_LEVELS):
        dg.mode, dg.dsel = "devmenu", lvl
        dg.step(DT, [key(pygame.K_RETURN)])
        assert dg.mode == "game" and dg.arena.area == lvl and dg.arena.tier == lvl


def test_dev_number_keys_and_brackets_warp(dg):
    dg.warp(0)
    dg.step(DT, [key(pygame.K_4)]); assert dg.arena.area == 3
    dg.step(DT, [key(pygame.K_RIGHTBRACKET)]); assert dg.arena.area == 4
    dg.step(DT, [key(pygame.K_LEFTBRACKET)]); assert dg.arena.area == 3
    dg.step(DT, [key(pygame.K_6)]); dg.step(DT, [key(pygame.K_RIGHTBRACKET)]); assert dg.arena.area == 5   # clamps at last level
    dg.step(DT, [key(pygame.K_1)]); dg.step(DT, [key(pygame.K_LEFTBRACKET)]); assert dg.arena.area == 0


def test_dev_keys_do_nothing_without_dev_mode(g):
    g.heroes = ["Knight", "Tank"]
    g.warp(0)
    g.step(DT, [key(pygame.K_4)]); g.step(DT, [key(pygame.K_g)])
    assert g.arena.area == 0 and not g.arena.god


def test_dev_toggles_god_fly_debug_help(dg):
    dg.warp(0)
    dg.step(DT, [key(pygame.K_g)]); assert dg.arena.god
    dg.step(DT, [key(pygame.K_g)]); assert not dg.arena.god
    dg.step(DT, [key(pygame.K_v)]); assert all(p.fly for p in dg.arena.players)
    dg.step(DT, [key(pygame.K_h)]); assert dg.arena.debug
    dg.step(DT, [key(pygame.K_F1)]); assert dg.dev.help
    dg.step(DT, [])                                       # overlay + hitboxes draw


def test_dev_fly_moves_in_the_air_without_falling(dg):
    dg.warp(0)
    dg.step(DT, [key(pygame.K_v)])
    dg.motions[0].jump_h = True
    y0 = dg.arena.players[0].y
    run(dg, 0.5)
    assert dg.arena.players[0].y < y0 - 20
    dg.motions[0].jump_h = False
    y1 = dg.arena.players[0].y
    run(dg, 0.5)
    assert dg.arena.players[0].y == y1                     # hovers instead of falling


def test_dev_boss_kill_next_and_tier_cycle(dg):
    dg.warp(1)
    dg.step(DT, [key(pygame.K_b)])
    a = dg.arena
    assert a.boss is not None and a.boss.kind == "beastlord" and not a.queue
    dg.step(DT, [key(pygame.K_t)])
    assert a.tier == 2 and (a.taken, a.dealt) == config.difficulty(2)
    dg.step(DT, [key(pygame.K_x)]); dg.step(DT, [])
    assert a.portal
    dg.step(DT, [key(pygame.K_n)]); dg.step(DT, [])
    assert dg.mode == "cutscene"


def test_dev_spawn_cycles_through_every_enemy_and_boss(dg):
    from game.devmode import SPAWNABLE
    dg.warp(0, gallery=True)
    for _ in SPAWNABLE:
        dg.step(DT, [key(pygame.K_y)])
        dg.step(DT, [])
    kinds = {e.kind for e in dg.arena.enemies}
    assert {"zombie", "wolf", "lich", "gunman", "alien", "knight"} <= kinds | {"x"}
    assert dg.arena.state == "play"


def test_dev_cutscene_preview_returns_to_the_level(dg):
    dg.warp(2)
    for _ in range(3):
        dg.step(DT, [key(pygame.K_c)])
        assert dg.mode == "cutscene"
        dg.step(DT, [key(pygame.K_ESCAPE)])
        dg.step(DT, [])
        assert dg.mode == "game" and dg.arena.area == 2


def test_gallery_never_spawns_waves_or_ends(dg):
    dg.warp(0, gallery=True)
    run(dg, 30)
    assert dg.arena.gallery and not dg.arena.boss_spawned and not dg.arena.portal and dg.mode == "game"
    assert [e.kind for e in dg.arena.enemies] == ["dummy"]


def test_tier_override_survives_retries_and_warps(dg):
    dg.warp(0)
    dg.step(DT, [key(pygame.K_t)])
    dg.step(DT, [key(pygame.K_3)])
    assert dg.arena.tier == 1 and dg.tier_override == 1


# ------------------------------------------------------------------ misc screens
def test_settings_rebind_still_works(g):
    to_menu_item(g, "SETTINGS")
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.mode == "settings"
    g.step(DT, [key(pygame.K_RETURN)])
    assert g.listening
    g.step(DT, [key(pygame.K_t)])
    assert config.SET["keys"][0]["left"] == pygame.K_t and not g.listening
    assert config.load_settings()["keys"][0]["left"] == pygame.K_t


def test_quit_event_sets_quit_flag(g):
    g.step(DT, [pygame.event.Event(pygame.QUIT)])
    assert g.quit
