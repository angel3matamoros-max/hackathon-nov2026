import random

import pytest

from game.classes import CLASSES
from game.loot import HOLY, HOLY_ATK, CURSED_ATK, roll_holy
from game.player import Player, apply_gear


def test_chest_roll_is_75_25_over_many_rolls():
    rng = random.Random(2024)
    n = 20000
    cursed = sum(roll_holy("Knight", rng)["cursed"] for _ in range(n))
    assert abs(cursed / n - 0.25) < 0.015


@pytest.mark.parametrize("cls", list(CLASSES))
def test_each_class_has_holy_and_stronger_cursed_weapon(cls):
    assert cls in HOLY
    holy = roll_holy(cls, type("R", (), {"random": lambda s: 0.9})())
    cursed = roll_holy(cls, type("R", (), {"random": lambda s: 0.1})())
    assert not holy["cursed"] and holy["atk"] == HOLY_ATK and holy["name"] == HOLY[cls]["name"]
    assert cursed["cursed"] and cursed["atk"] == CURSED_ATK > holy["atk"] and cursed["curse"] and cursed["curse_text"]
    assert cursed["name"] != holy["name"]


@pytest.mark.parametrize("cls", list(CLASSES))
def test_cursed_weapon_applies_atk_and_its_curse(cls):
    p = Player(0, cls, 80)
    base_atk, base_hp = p.atk, p.maxhp
    w = roll_holy(cls, type("R", (), {"random": lambda s: 0.1})())
    apply_gear(p, w)
    assert p.atk == round(base_atk * 1.7)
    assert (p.dmg_taken, p.cd_mult, p.maxhp) != (1.0, 1.0, base_hp)    # exactly the curse changes something
    apply_gear(p, None)
    assert (p.atk, p.dmg_taken, p.cd_mult, p.maxhp) == (base_atk, 1.0, 1.0, base_hp)


def test_holy_weapon_has_no_curse():
    p = Player(0, "Mage", 80)
    apply_gear(p, roll_holy("Mage", type("R", (), {"random": lambda s: 0.9})()))
    assert (p.dmg_taken, p.cd_mult) == (1.0, 1.0) and p.atk == round((8 + 10 * 2) * 1.25)


def test_curse_effects_are_felt_in_play(mk):
    a, mo = mk(2, classes=("Knight", "Mage"))
    k = a.players[0]
    apply_gear(k, dict(name="x", cursed=True, atk=1.7, curse="Brittle Soul", curse_text="", dmg_taken=1.3))
    f = Player(1, "Knight", 100)
    k.take(40, None, a, None); f.take(40, None, a, None)
    assert k.maxhp - k.hp > f.maxhp - f.hp
    a.cast(k)
    assert k.cast_cd == CLASSES["Knight"]["cd"]


def kill_boss_and_chest(mk):
    a, mo = mk(2)
    a.spawn_boss(); a.boss.hp = 0
    a.update(1 / 60, mo)
    return a, mo


def hold_loot(a, mo, p, secs=1.0):
    p.x, p.y = a.chest["x"], 222.0
    mo[p.i].interact_h = True
    for _ in range(int(secs * 60)): a.update(1 / 60, mo)
    mo[p.i].interact_h = False


def test_chest_modal_take_equips_leave_keeps(mk):
    a, mo = kill_boss_and_chest(mk)
    for p in a.players: p.inv = 99
    random.seed(1)
    hold_loot(a, mo, a.players[0])
    assert a.state == "chest" and a.cm["p"] is a.players[0]
    offer = a.cm["offer"]
    a.draw()                                              # modal renders
    a.update(0.6, mo)                                     # input is ignored for a short moment
    mo[0].reset(); mo[0].swing = "left"; mo[0].slash_p = True
    a.update(1 / 60, mo)
    assert a.state == "play" and a.players[0].weapon == offer and 0 in a.chest["used"]
    # second player leaves theirs
    hold_loot(a, mo, a.players[1])
    assert a.state == "chest"
    a.update(0.6, mo)
    mo[1].reset(); mo[1].swing = "right"; mo[1].slash_p = True
    a.update(1 / 60, mo)
    assert a.state == "play" and a.players[1].weapon is None and 1 in a.chest["used"]
    hold_loot(a, mo, a.players[1])
    assert a.state == "play"                              # a chest can't be rolled twice by the same player


def test_gear_carries_into_next_level(mk):
    from game.arena import Arena
    w = dict(name="Lightbringer", cursed=False, atk=1.25)
    a = Arena(3, [Player(0, "Knight", 80), Player(1, "Mage", 110)], gear=[w, None])
    assert a.players[0].weapon == w and a.players[1].weapon is None and a.players[0].atk == round((8 + 6 * 2) * 1.25)
