"""Gear / loot system: items have real effects, drops are partial, waves go one after another, loot is lost on defeat."""
import random

from game.enemies import ESTATS, DROP
from game.items import roll_item, describe, power, mods, SLOTS
from game.loot import roll_holy
from game.player import Player


def rolls(n=3000, **kw):
    rng = random.Random(7)
    return [roll_item(rng.random(), rng, **kw) for _ in range(n)]


def test_item_shape_and_description():
    for it in rolls():
        assert it["slot"] in SLOTS and 0 <= it["tier"] <= 2 and it["name"] and it["desc"] == describe(it) != "no effect"


def test_normal_loot_never_legendary_boss_loot_can_be():
    assert max(i["tier"] for i in rolls()) <= 2
    boss = rolls(boss=True, min_tier=2)
    assert min(i["tier"] for i in boss) >= 2 and any(i["tier"] == 3 for i in boss)


def test_higher_tier_is_stronger_per_slot():
    rng = random.Random(1)
    for slot in SLOTS:
        ps = [power(roll_item(1.0, rng, slot=slot, min_tier=t, max_tier=t)) for t in (0, 1, 2)]
        assert ps[0] < ps[1] < ps[2]


def test_slots_stack_and_recompute_keeps_hp_ratio():
    p = Player(0, "Knight", 80)
    base_atk, base_max = p.atk, p.maxhp
    p.hp = p.maxhp // 2
    p.equip(dict(slot="weapon", tier=1, name="w", atk=1.5))
    p.equip(dict(slot="armor", tier=1, name="a", hp=1.5, dmg_taken=0.8, thorns=5))
    p.equip(dict(slot="charm", tier=1, name="c", cd_mult=0.8, crit=0.1, speed=1.1))
    assert p.atk == round(base_atk * 1.5) and p.maxhp == round(base_max * 1.5)
    assert abs(p.hp / p.maxhp - 0.5) < 0.02
    assert (p.dmg_taken, p.cd_mult, p.speed, p.crit, p.thorns) == (0.8, 0.8, 1.1, 0.1, 5)
    p.gear["armor"] = None; p.recompute()
    assert p.maxhp == base_max and p.thorns == 0


def test_mods_of_nothing_is_neutral():
    assert mods([None, None]) == dict(atk=1.0, hp=1.0, dmg_taken=1.0, cd_mult=1.0, speed=1.0, lifesteal=0.0, crit=0.0, thorns=0.0, block_window=0.0)


def test_holy_item_is_a_weapon_with_description():
    w = roll_holy("Mage", type("R", (), {"random": lambda s: 0.9})())
    assert w["slot"] == "weapon" and "ATK" in w["desc"]
    c = roll_holy("Mage", type("R", (), {"random": lambda s: 0.1})())
    assert c["cursed"] and "CURSE" in c["desc"]


def test_give_equips_better_and_bags_worse(mk):
    a, mo = mk(0)
    p = a.players[0]
    assert a.give(p, dict(slot="weapon", tier=2, name="Big", atk=1.3, desc="x")) is True and p.weapon["name"] == "Big"
    assert a.give(p, dict(slot="weapon", tier=0, name="Small", atk=1.05, desc="y")) is False and p.weapon["name"] == "Big"
    assert len(a.pending[0]) == 2 and a.toasts[-1]["equipped"] is False


def test_perks_work_in_combat(mk):
    a, mo = mk(1)
    p = a.players[0]
    p.equip(dict(slot="charm", tier=2, name="c", lifesteal=0.5, desc=""))
    p.hp = 10
    e = a.spawn("zombie", p.x + 20)
    a.hurt(e, 20, 100, by=p)
    assert p.hp > 10
    p.thorns = 5
    e2 = a.spawn("zombie", p.x + 20); hp = e2.hp
    p.inv = 0; p.take(8, e2.x, a, e2)
    assert e2.hp == hp - 5


def test_drops_are_partial_and_elites_drop_more(mk):
    random.seed(3)
    a, _ = mk(0)
    n, got = 400, {"zombie": 0, "brute": 0}
    for kind in got:
        for _ in range(n):
            e = a.spawn(kind, 200); a.kill(e)
            got[kind] += not a.corpses[-1]["looted"]
    assert 0.12 < got["zombie"] / n < 0.40 and 0.45 < got["brute"] / n < 0.75 and got["zombie"] < got["brute"]
    assert all(c["plain"] for c in a.corpses if c["looted"])          # a non-drop is a plain corpse, not a "looted" one
    assert ESTATS["zombie"]["drop"] == DROP["zombie"]


def test_tutorial_and_bosses_always_drop(mk):
    a, _ = mk(0, tut=True)
    for _ in range(30): a.kill(a.spawn("zombie", 200))
    assert not any(c["looted"] for c in a.corpses)


def test_cache_can_appear_between_waves(mk):
    random.seed(5)
    a, mo = mk(0, waves=True)
    a.drop_mult = 99
    for _ in range(60 * 4): a.update(1 / 60, mo)
    for e in list(a.enemies): e.hp = 0
    a.queue = []
    a.update(1 / 60, mo)
    assert any(c["kind"] == "cache" and not c["looted"] for c in a.corpses)


def test_defeat_restores_gear_from_level_start(mk):
    a, mo = mk(0)
    p = a.players[0]
    a.give(p, dict(slot="weapon", tier=2, name="Big", atk=1.3, desc="x"))
    assert p.weapon
    for q in a.players: q.down = True
    a.update(1 / 60, mo)
    assert a.state == "failed" and p.weapon is None and p.atk == Player(0, "Knight", 0).atk


def test_gear_screen_toggles_and_pauses(mk):
    a, mo = mk(0)
    mo[0].gear_p = True; a.update(1 / 60, mo)
    assert a.state == "gear"
    mo[0].reset()
    for _ in range(30): a.update(1 / 60, mo)
    assert a.state == "gear" and a.draw() is None
    mo[1].gear_p = True; a.update(1 / 60, mo)
    assert a.state == "play"


def test_toasts_and_gear_screen_draw_for_both_players(mk):
    a, mo = mk(0)
    a.players[1].cpu = True
    rng = random.Random(2)
    for p in a.players:
        for slot in SLOTS: a.give(p, roll_item(0.9, rng, slot=slot))
    a.draw()
    a.state = "gear"; a.draw()
