import pytest

from game.config import FLOOR
from game.enemies import ESTATS
from game.bosses import BOSSES
from game.qabot import run_bot

PLAIN = [k for k in ESTATS if k != "dummy" and k not in BOSSES]


@pytest.mark.parametrize("kind", PLAIN)
def test_every_enemy_runs_against_players_without_error(mk, kind):
    a, mo = mk(0)
    a.spawn(kind, x=300, dscale=1.0)
    run_bot(a, 6)
    a.draw()
    e = [x for x in a.enemies if x.kind == kind]
    assert all(0 <= x.x <= 480 and -50 < x.y <= FLOOR + 1 for x in e)


def test_flyers_hover_above_ground(mk):
    a, _ = mk(0)
    for k in ("bat", "drone", "alien"):
        a.spawn(k, x=300, dscale=1.0)
    run_bot(a, 3)
    assert all(e.y < FLOOR for e in a.enemies)


def test_difficulty_scales_enemy_damage_dealt(mk):
    seen = {}
    for tier in (0, 3):
        a, mo = mk(0, tier=tier)
        hits = []
        orig = a.players[0].take
        a.players[0].take = lambda dmg, sx, arena, src, h=hits, o=orig: (h.append(dmg), o(dmg, sx, arena, src))
        a.players[1].down = True
        e = a.spawn("skeleton", x=a.players[0].x + 15, dscale=1.0)
        e.state, e.st, e.act = "wind", 0.01, "melee"
        e.face = -1
        for _ in range(10): a.update(1 / 60, mo)
        seen[tier] = hits[0]
    assert seen[3] == pytest.approx(seen[0] * 1.25 ** 3)


def test_enemy_damage_taken_reduced_per_level_and_floor_of_one(mk):
    a0, _ = mk(0, tier=0)
    a5, _ = mk(5, tier=5)
    e0, e5 = a0.spawn("brute", x=200), a5.spawn("brute", x=200)
    a0.hurt(e0, 40, 0); a5.hurt(e5, 40, 0)
    assert e0.maxhp - e0.hp == 40
    assert e5.maxhp - e5.hp == int(40 * 0.75 ** 5)
    e = a5.spawn("skeleton", x=100)
    a5.hurt(e, 1, 0)
    assert e.maxhp - e.hp == 1  # regression: int() truncation used to turn tiny hits into 0 damage


def test_training_dummy_ignores_difficulty(mk):
    a, _ = mk(5, tier=5)
    d = a.spawn("dummy", x=300)
    a.hurt(d, 40, 0)
    assert a.dummy_hits == 1 and d.hp == 9999


def test_holy_knight_shield_blocks_front_not_back_not_windup(mk):
    a, _ = mk(2, tier=0)
    k = a.spawn("knight", x=300)
    k.face, k.state = -1, "walk"                    # facing left; attacker on the left => kb > 0
    a.hurt(k, 100, 170); assert k.maxhp - k.hp == 30
    k.hp = k.maxhp; a.hurt(k, 100, -170); assert k.maxhp - k.hp == 100          # from behind
    k.hp = k.maxhp; k.state = "wind"; a.hurt(k, 100, 170); assert k.maxhp - k.hp == 100  # shield drops while attacking
    k.hp = k.maxhp; k.state, k.stun = "walk", 1.0; a.hurt(k, 100, 170); assert k.maxhp - k.hp == 100  # stunned


def test_cat_beast_sidesteps_first_hit_then_cooldown(mk):
    a, _ = mk(1, tier=0)
    c = a.spawn("catman", x=300)
    c.state, x0 = "walk", c.x
    a.hurt(c, 30, 170)
    assert c.hp == c.maxhp and c.x != x0 and c.dodge_cd > 0
    a.hurt(c, 30, 170)
    assert c.hp < c.maxhp


def test_gunman_keeps_distance_and_fires_blockable_bullets(mk):
    a, mo = mk(4, classes=("Knight", "Mage"))
    a.players[1].down = True
    g = a.spawn("gunman", x=280, dscale=1.0)
    g.cd = 0.0
    for _ in range(120): a.update(1 / 60, mo)
    assert a.eprojs or a.players[0].hp < a.players[0].maxhp
    assert abs(g.x - a.players[0].x) > 60


def test_lich_summons_skeletons_up_to_cap(mk):
    a, mo = mk(3)
    l = a.spawn("lich", x=350, dscale=1.0)
    l.cd2 = 0.0
    for _ in range(60 * 30):
        a.players[0].inv = a.players[1].inv = 99  # keep the test about the lich, not about player survival
        a.update(1 / 60, mo)
    assert 1 <= a.count("skeleton") <= 2


def test_wolf_lunge_hits_once_and_goes_on_cooldown(mk):
    a, mo = mk(1, classes=("Tank", "Knight"))
    a.players[1].down = True
    w = a.spawn("wolf", x=a.players[0].x + 70, dscale=1.0)
    w.cd = 0.0
    hp0 = a.players[0].hp
    for _ in range(90): a.update(1 / 60, mo)
    assert a.players[0].hp < hp0
    assert w.cd > 0 or w.state in ("rest", "walk")


def test_stunned_and_frozen_enemies_do_nothing(mk):
    a, mo = mk(0)
    e = a.spawn("skeleton", x=a.players[0].x + 10, dscale=1.0)
    e.stun = 5
    hp = a.players[0].hp
    for _ in range(120): a.update(1 / 60, mo)
    assert a.players[0].hp == hp
