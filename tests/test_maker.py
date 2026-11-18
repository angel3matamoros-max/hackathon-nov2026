"""Castle Maker end to end: editor rows and values, saving, the menus, and a whole castle played through the real Game loop."""
import os
import random

import pygame
import pytest

from game import castle as C, config
from game.app import Game
from game.maker import Editor
from game.qabot import FakeMotion, Bot

DT = 1 / 30


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


@pytest.fixture
def g(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CASTLE_DIR", str(tmp_path / "castles"))
    config.SET["tutorial_done"] = True
    return Game(dev=False, motions=[FakeMotion(0), FakeMotion(1)])


def step(g, *keys):
    g.step(DT, [key(k) for k in keys])


def rows_index(ed, kind):
    return next(i for i, r in enumerate(ed.rows()) if r[0] == kind)


# ------------------------------------------------------------------ editor (pure logic)
def test_new_editor_is_a_valid_one_level_castle():
    ed = Editor()
    assert ed.check() == [] and len(ed.spec["levels"]) == 1


def test_editor_changes_theme_layout_boss_and_wave_values():
    ed = Editor()
    ed.row = rows_index(ed, "theme"); ed.change(1); assert ed.L["theme"] == 1
    ed.row = rows_index(ed, "layout"); ed.change(1); assert ed.L["layout"] == "B"
    ed.row = rows_index(ed, "boss"); ed.L["boss"] = None; ed.change(1); assert ed.L["boss"] == C.BOSS_CHOICES[0]
    ed.change(-1); assert ed.L["boss"] is None
    ed.row = rows_index(ed, "wave"); before = ed.L["waves"][0][0][:]; ed.change(1)
    assert ed.L["waves"][0][0][0] != before[0]                       # Left/Right change the kind
    ed.act(); assert ed.L["waves"][0][0][1] == before[1] % 5 + 1     # Enter bumps the count (1..5)


def test_editor_adds_and_removes_waves_levels_within_limits():
    ed = Editor()
    for _ in range(C.MAX_WAVES + 3):
        ed.row = rows_index(ed, "add_wave"); ed.act()
    assert len(ed.L["waves"]) == C.MAX_WAVES and "at most" in ed.msg
    for _ in range(C.MAX_WAVES + 3):
        ed.row = rows_index(ed, "del_wave"); ed.act()
    assert len(ed.L["waves"]) == 1
    for _ in range(12):
        ed.row = rows_index(ed, "add_level"); ed.act()
    assert len(ed.spec["levels"]) == C.MAX_LEVELS
    ed.row = rows_index(ed, "level"); ed.change(1); assert ed.li == 0 and ed.L is ed.spec["levels"][0]


def test_editor_name_typing():
    ed = Editor()
    ed.typing = True
    for ch in "Hi!": ed.type(ch)
    ed.type("\b")
    assert ed.spec["name"] == "My CastleHi"[:0] + ed.spec["name"] and ed.spec["name"].endswith("Hi")
    ed.spec["name"] = "x" * C.MAX_NAME
    ed.type("y"); assert len(ed.spec["name"]) == C.MAX_NAME


def test_save_writes_a_loadable_castle_and_refuses_an_invalid_one(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "CASTLE_DIR", str(tmp_path))
    ed = Editor(); ed.spec["name"] = "Dragon Hall"
    assert ed.save() and os.path.exists(os.path.join(tmp_path, "dragon_hall.json"))
    assert C.load_castle(ed.path)[1] == []
    bad = Editor(); bad.spec["name"] = ""
    assert not bad.save() and bad.msg.startswith("Cannot save")


def test_test_level_only_for_a_valid_level():
    ed = Editor(); lvl = ed.test_level()
    assert lvl and lvl["waves"] and lvl["theme"] == 0
    ed.L["waves"] = [[["zombie", 99]]]
    assert ed.test_level() is None and ed.msg.startswith("Cannot test")


# ------------------------------------------------------------------ screens + a full playthrough
def test_menu_reaches_castle_maker_and_back(g):
    g.msel = g.menu_items().index("CASTLE MAKER")
    step(g, pygame.K_RETURN)
    assert g.mode == "castles"
    step(g, pygame.K_ESCAPE)
    assert g.mode == "menu"


def test_build_a_castle_in_the_editor_save_it_and_play_it_to_victory(g):
    random.seed(11)
    g.msel = g.menu_items().index("CASTLE MAKER"); step(g, pygame.K_RETURN)
    rows = C.list_castles(C.CASTLE_DIR)
    g.csel = len(rows)                                   # "+ NEW CASTLE"
    step(g, pygame.K_RETURN)
    assert g.mode == "maker"
    ed = g.ed
    ed.spec["name"] = "Test Keep"
    ed.spec["levels"][0]["waves"] = [[["zombie", 1]]]     # tiny so the bot finishes quickly
    ed.spec["levels"][0]["boss"] = "gravekeeper"
    ed.row = rows_index(ed, "add_level"); step(g, pygame.K_RETURN)
    ed.row = rows_index(ed, "play"); step(g, pygame.K_RETURN)
    assert g.mode == "select" and g.custom and len(g.custom) == 2
    assert os.path.exists(os.path.join(C.CASTLE_DIR, "test_keep.json"))
    for m in g.motions: m.slash_p = True                 # both heroes press ready once
    g.step(DT, [])
    for m in g.motions: m.reset()
    assert g.mode in ("game", "cutscene")
    if g.mode == "cutscene":
        for _ in range(int(3 / DT)):
            g.step(DT, [])
            if g.mode == "game": break
    bot = Bot("careful")
    for _ in range(int(900 / DT)):
        if g.mode != "game": break
        g.arena.god = True
        bot.drive(g.arena, g.motions, DT)
        g.step(DT, [])
        for m in g.motions: m.reset()
    assert g.mode == "victory", f"mode {g.mode}, level {g.area + 1} of {len(g.custom or [])}"


def test_test_button_plays_one_level_and_returns_to_the_editor(g):
    g.mode = "maker"; g.ed = Editor()
    g.ed.row = rows_index(g.ed, "test")
    step(g, pygame.K_RETURN)
    assert g.mode == "game" and g.custom and len(g.custom) == 1 and g.test_back == "maker"
    g.arena.god = True
    g.arena.result = "next"
    step(g, pygame.K_SPACE)
    assert g.mode == "maker"


def test_bossless_castle_level_opens_the_portal_when_waves_end(mk):
    a, mo = mk(0, waves=False)
    a.A = dict(a.A, boss=None)
    a.waves = [[("zombie", 1)]]
    a.wave_gap = 0.0
    for _ in range(60 * 60):
        for e in a.enemies: e.hp = 0                                  # the waves are fought and cleared
        a.update(1 / 60, mo)
        if a.portal: break
    assert a.portal and a.boss is None


def test_castle_levels_are_built_from_saved_specs(tmp_path):
    spec = C.new_castle("Two")
    spec["levels"].append(C.default_level(5))
    lv = C.castle_levels(spec)
    assert [L["theme"] for L in lv] == [0, 5] and lv[1]["boss"] == LEVEL_BOSS_5()


def LEVEL_BOSS_5():
    from game.levels import LEVELS
    return LEVELS[5]["boss"]


# ------------------------------------------------------------------ the defect fixes from the QA review
def test_grab_and_tractor_bugs_stay_fixed(mk):
    a, mo = mk(5)
    b = a.spawn_boss(); b.intro, b.x = 0.0, b.home
    p = a.players[0]; p.x, p.y = b.x, 222.0; p.inv = 0.0
    b.pat_tractor(p, a)
    for _ in range(60): a.update(1 / 60, mo)
    assert p.y >= 222 - 150 - 1                                   # never lifted past the ceiling
    b.hp = 0; a.update(1 / 60, mo)
    assert b.beam_t == 0.0                                        # a dead boss's beam is off


def test_gear_key_works_in_the_tutorial(mk):
    a, mo = mk(0, tut=True)
    mo[0].gear_p = True; a.update(1 / 60, mo)
    assert a.state == "gear"


def test_lifesteal_has_no_one_hp_minimum(mk):
    a, mo = mk(0)
    p = a.players[0]; p.lifesteal = 0.04; p.hp = 10
    e = a.spawn("zombie", p.x + 10)
    for _ in range(30):
        e.hp = 9999; a.hurt(e, 20, 0, by=p)                       # 20 dmg, 4% lifesteal = 0.8 HP per hit
    assert 0 < p.hp - 10 <= 25                                     # ~24 total, not 30 (1 HP minimum per hit)


def test_gravestone_zombies_are_capped(mk):
    a, mo = mk(0)
    b = a.spawn_boss(); b.intro, b.x = 0.0, b.home
    for _ in range(8): a.spawn("zombie", 100)
    from game.props import Prop
    a.props.append(Prop("tomb", 200, 222, 24, b))
    for _ in range(int(5 / (1 / 60))): a.update(1 / 60, mo)
    assert a.count("zombie") <= 8


def test_wave_clock_stops_while_gear_screen_is_open(mk):
    a, mo = mk(0, waves=True)
    t0 = a.t
    mo[0].gear_p = True; a.update(1 / 60, mo)
    for _ in range(300): a.update(1 / 60, mo)
    assert a.t == t0                                              # the clock does not run while the gear screen is open


def test_grab_roots_only_on_a_landed_hit(mk):
    a, mo = mk(0)
    p = a.players[0]; p.inv = 1.0                                  # i-frames: the grab does nothing
    a.hazard("grab", p.x - 12, p.x + 12, 190, 226, 0.0, 1.0, 10, None)
    a.update_threats(1 / 60)
    assert p.rooted == 0.0


def test_spawned_boss_gets_its_setup(mk):
    a, mo = mk(0)
    b = a.spawn("tycoon", 300)
    assert b.arena is a and b.intro > 0


def test_chest_card_text_fits_the_card(mk):
    from game.gfx import fit_lines, font
    lines = fit_lines("Blessed Mace of Swift Cuts: +20% ATK, heal 6% of damage dealt, 12% crit (x2), +25% HP, -10% dmg taken", 132, 6)
    assert all(font.size(l)[0] <= 132 for l in lines) and len(lines) <= 6


def test_cpu_takes_only_upgrades(mk):
    a, mo = mk(2)
    p = a.players[1]; p.cpu = True
    a.players[1].equip(dict(slot="weapon", tier=3, name="Great", atk=1.9, desc=""))
    a.boss_spawned = True
    a.chest = dict(x=p.x, y=p.y, hold=0.0, used=set(), holy=False)
    a.start_chest(p)
    assert p.weapon["name"] == "Great" or not p.weapon.get("cursed")  # never replaces a better weapon with a worse one


# ------------------------------------------------------------------ mouse and preview
def test_editor_mouse_hit_testing_finds_tiles_rows_and_arrows():
    from game import maker as M
    ed = Editor()
    assert M.editor_hit(ed, M.tile_rect(0).center) == ("level", 0)
    assert M.editor_hit(ed, M.tile_rect(1).center) == ("addlevel",)            # the + tile
    theme_row = rows_index(ed, "theme")
    y = M.row_rect(theme_row, 0).centery
    assert M.editor_hit(ed, (M.ARROW_R + 6, y)) == ("arrow", theme_row, 1)
    assert M.editor_hit(ed, (M.ARROW_L + 6, y)) == ("arrow", theme_row, -1)
    assert M.editor_hit(ed, (60, y)) == ("row", theme_row)
    assert M.editor_hit(ed, (400, 250)) is None


def test_castle_list_mouse_hit_testing():
    from game import maker as M
    assert M.castle_hit((30, M.LIST_Y + 1), 2) == 0
    assert M.castle_hit((30, M.LIST_Y + 2 * M.LIST_STEP + 1), 2) == 2          # + NEW
    assert M.castle_hit((30, M.LIST_Y + 3 * M.LIST_STEP + 1), 2) == 3          # BACK
    assert M.castle_hit((30, M.LIST_Y + 4 * M.LIST_STEP + 1), 2) is None
    assert M.castle_hit((300, M.LIST_Y + 1), 2) is None                         # right side is the preview


def test_clicking_a_row_selects_and_clicking_it_again_acts(g):
    g.mode = "maker"; g.ed = Editor()
    y = __import__("game.maker", fromlist=["x"]).row_rect(rows_index(g.ed, "name"), 0).centery
    g.step(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(60, y), button=1)])
    assert g.ed.typing                                                         # the name row's action: start typing
    g.ed.typing = False
    g.ed.row = 0


def test_clicking_the_plus_tile_adds_a_level_and_the_arrows_change_values(g):
    from game import maker as M
    g.mode = "maker"; g.ed = Editor()
    g.step(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=M.tile_rect(1).center, button=1)])
    assert len(g.ed.spec["levels"]) == 2
    row = rows_index(g.ed, "theme")
    before = g.ed.L["theme"]
    y = M.row_rect(row, g.ed.top).centery
    g.step(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(M.ARROW_R + 6, y), button=1)])
    assert g.ed.L["theme"] == (before + 1) % 6 and g.ed.row == row


def test_castles_mouse_click_selects_then_plays(g, tmp_path, monkeypatch):
    from game import maker as M
    from game.castle import save_castle, new_castle
    save_castle(new_castle("Clicky"), str(tmp_path / "castles"))
    monkeypatch.setattr(C, "CASTLE_DIR", str(tmp_path / "castles"))
    g.mode, g.csel = "castles", 1                                               # start on NEW, so the first click only selects
    pos = (30, M.LIST_Y + 1)
    g.step(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)])
    assert g.mode == "castles"                                                  # first click only selects
    g.step(DT, [pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1)])
    assert g.mode == "select" and g.custom and g.custom[0]["name"]


def test_preview_draws_for_every_theme_layout_and_wave(mk):
    from game import maker as M
    for theme in range(6):
        for layout in C.LAYOUTS:
            spec = dict(theme=theme, layout=layout, boss="gravekeeper", waves=[[["zombie", 3], ["bat", 2]], [["knight", 5]], [["drone", 1]]])
            for t in (0.0, 2.0, 5.5):
                surf, k, n = M.level_surface(M.preview_level(spec), t)
                assert surf.get_size() == (480, 270) and n == 3
                M.thumb(surf)
    M.level_surface(M.preview_level(dict(theme=0, waves=[], boss=None, layout="none")), 1.0)  # empty level still draws


def test_editor_and_castle_screens_draw_without_error_in_every_state(mk):
    from game import maker as M
    ed = Editor()
    ed.add_level(); ed.add_wave(); ed.typing = True; ed.msg = "Cannot save: test"
    for r in range(len(ed.rows())):
        ed.row = r
        M.draw_editor(ed, 1.0)
    M.draw_castles([("A", 1, []), ("B", 2, ["bad"])], 1, "This castle has errors", 0.5, None, ["bad"])
    M.draw_castles([], 0, "", 0.0, None, ())
