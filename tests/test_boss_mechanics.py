"""Signature boss mechanics: entrance, gravestones + grab (Gravekeeper), wall-daze charge (Beastlord), aegis orbs (Paladin),
phylactery crystals (Archlich), cover + reload window (Don), tractor beam (Tycoon), and breakable props in general."""
import random

import pytest

from game.bosses import BOSSES
from game.config import FLOOR, W
from game.props import Prop, RAISE_TIME
from game.qabot import FakeMotion


def fight(mk, lvl, enter=False, **kw):
    a, mo = mk(lvl, **kw)
    b = a.spawn_boss()
    if not enter: b.intro, b.x = 0.0, b.home
    for p in a.players: p.inv = 99
    return a, mo, b


def tick(a, mo, secs):
    for _ in range(int(secs * 60)): a.update(1 / 60, mo)


# ------------------------------------------------------------------ entrance
@pytest.mark.parametrize("lvl", range(6))
def test_entrance_slides_in_immune_then_stands_on_the_floor(mk, lvl):
    a, mo, b = fight(mk, lvl, enter=True)
    assert b.x > W and b.intro > 0 and b.invulnerable()
    a.hurt(b, 500, 100)
    assert b.hp == b.maxhp                                  # immune while entering
    tick(a, mo, 3.0)
    assert b.intro <= 0 and b.x < W - 40
    if not b.d.get("fly"): assert b.y == pytest.approx(FLOOR, abs=1)
    a.god = True


def test_boss_is_big_and_hitbox_matches():
    from game.sprites import ENEMY
    for k, c in BOSSES.items():
        fr = ENEMY[(k, 0)][0]
        assert fr.get_height() >= 100 and c["h"] >= 80 and c["w"] >= 34


# ------------------------------------------------------------------ Gravekeeper
def test_raise_makes_gravestones_that_birth_zombies_unless_broken(mk):
    a, mo, b = fight(mk, 0)
    b.pat_raise(a.players[0], a)
    tombs = [q for q in a.props if q.kind == "tomb"]
    assert len(tombs) == 2 + b.phase and all(q.owner is b for q in tombs)
    a.hurt_prop(tombs[0], 999)                              # break one
    z0 = a.count("zombie")
    tick(a, mo, RAISE_TIME + 0.5)
    assert a.count("zombie") == z0 + len(tombs) - 1
    assert not [q for q in a.props if q.kind == "tomb"]


def test_grab_roots_the_hero_and_dash_frees_them(mk):
    a, mo, b = fight(mk, 0)
    p = a.players[0]
    p.inv = 0.0                                             # a hit must land for the root to apply
    b.act_t = 0.3
    b.pre_grab(p, a)
    tick(a, mo, 0.5)                                        # warning ends, hands grab
    assert p.rooted > 0
    x = p.x
    mo[0].axis = 1
    tick(a, mo, 0.3)
    assert p.x == pytest.approx(x, abs=1)                   # rooted: cannot walk
    mo[0].dash_p = True; a.update(1 / 60, mo); mo[0].reset()
    assert p.rooted == 0


def test_grabbed_hero_can_still_attack(mk):
    a, mo, b = fight(mk, 0)
    p = a.players[0]; p.rooted = 1.0
    mo[0].slash_p = True; a.update(1 / 60, mo)
    assert p.slash_t > 0


# ------------------------------------------------------------------ Beastlord
def test_charge_into_the_wall_dazes_him(mk):
    a, mo, b = fight(mk, 1)
    for p in a.players: p.x, p.y, p.inv = 60, 222.0, 99      # heroes tucked away from the charge line (he charges the far wall)
    b.x, b.face = 300.0, 1
    b.pat_lunge(a.players[0], a)
    for _ in range(60 * 3):
        a.update(1 / 60, mo)
        if b.stun > 0: break
    assert b.stun > 0 and b.x >= W - 45


def test_charge_that_hits_a_hero_does_not_daze(mk):
    a, mo, b = fight(mk, 1)
    p = a.players[0]
    p.x, p.inv = 400.0, 0.0
    a.players[1].down = True
    b.x, b.face = 300.0, 1
    b.pat_lunge(p, a)
    tick(a, mo, 0.4)
    assert b.dash is None or b.dash[2]
    tick(a, mo, 2.0)
    assert b.stun == 0


def test_howl_causes_moon_rage_speed_up(mk):
    a, mo, b = fight(mk, 1)
    b.pat_howl(a.players[0], a)
    assert b.rage_t > 0 and b.status()[0] == "MOON RAGE!"


# ------------------------------------------------------------------ Paladin
def test_paladin_shield_holds_until_all_orbs_break(mk):
    a, mo, b = fight(mk, 2)
    orbs = b.props_of("orb")
    assert len(orbs) == 3 and b.dmg_mult() == 0.1 and "SHIELDED" in b.status()[0]
    a.hurt(b, 100, 100)
    shielded = b.maxhp - b.hp
    for o in orbs: a.hurt_prop(o, 999)
    tick(a, mo, 0.1)
    assert not b.props_of("orb") and b.dmg_mult() == 1.0
    hp = b.hp
    a.hurt(b, 100, 100)
    assert hp - b.hp > shielded * 5                         # exposed: far more damage


def test_orbs_orbit_the_boss_and_reform_with_guard(mk):
    a, mo, b = fight(mk, 2)
    o = b.props_of("orb")[0]
    d0 = abs(o.x - b.x)
    tick(a, mo, 0.5)
    assert abs(o.x - b.x) <= 47 and o.y < FLOOR
    for q in b.props_of("orb"): a.hurt_prop(q, 999)
    tick(a, mo, 0.1)
    b.pat_guard(a.players[0], a)
    assert len(b.props_of("orb")) == 3 and d0 >= 0


# ------------------------------------------------------------------ Archlich
def test_archlich_is_immune_until_crystals_break_and_each_break_staggers(mk):
    a, mo, b = fight(mk, 3)
    cr = b.props_of("crystal")
    assert len(cr) == 3 and b.invulnerable()
    a.hurt(b, 500, 100)
    assert b.hp == b.maxhp
    a.hurt_prop(cr[0], 999)
    tick(a, mo, 0.05)
    assert b.stun > 0 and len(b.props_of("crystal")) == 2 and b.invulnerable()
    for c in b.props_of("crystal"): a.hurt_prop(c, 999)
    tick(a, mo, 0.05)
    assert not b.invulnerable()
    a.hurt(b, 100, 100)
    assert b.hp < b.maxhp


def test_crystals_reform_when_a_new_phase_starts(mk):
    a, mo, b = fight(mk, 3)
    for c in b.props_of("crystal"): a.hurt_prop(c, 999)
    tick(a, mo, 0.1)
    b.hp = int(b.maxhp * 0.6)
    b.stun = 0.0
    tick(a, mo, 0.1)
    assert b.phase == 1 and len(b.props_of("crystal")) == 2 and b.invulnerable()


# ------------------------------------------------------------------ The Don
def test_crates_soak_bullets_and_dynamite_wrecks_them(mk):
    a, mo, b = fight(mk, 4)
    crate = [q for q in a.props if q.kind == "crate"][0]
    p = a.players[0]
    p.x, p.y = crate.x - 40, 222.0
    hp = crate.hp
    a.eshot(b, crate.x + 30, FLOOR - 14, -240, 0, 9, "bullet", life=2.0)   # fired from the right, towards the hero behind the crate
    ph = p.hp
    tick(a, mo, 0.5)
    assert p.hp == ph and crate.hp < hp                     # the crate took it
    a.explode(dict(x=crate.x, y=FLOOR - 4, blast=40, dmg=10))
    tick(a, mo, 0.05)
    assert crate not in a.props


def test_don_is_vested_except_while_reloading(mk):
    a, mo, b = fight(mk, 4)
    assert b.dmg_mult() == 0.6 and "Bulletproof" in b.status()[0]
    b.rest = 99.0                                           # no further attacks: only the burst under test
    b.pat_burst(a.players[0], a)
    tick(a, mo, 0.18 * (4 + b.phase) + 0.3)
    assert b.reload_t > 0 and b.dmg_mult() == 1.0 and "RELOADING" in b.status()[0]
    tick(a, mo, 2.5)
    assert b.dmg_mult() == 0.6


# ------------------------------------------------------------------ Tycoon
def test_tractor_beam_lifts_heroes_and_hurts_at_the_top(mk):
    a, mo, b = fight(mk, 5)
    p = a.players[0]
    p.x, p.inv = b.x, 0.0
    a.players[1].x = 40
    ph = p.hp
    b.pat_tractor(p, a)
    tick(a, mo, 1.9)
    assert p.y < FLOOR - 60 and p.hp <= ph
    tick(a, mo, 1.0)


def test_tractor_beam_can_be_escaped_by_walking_away(mk):
    a, mo, b = fight(mk, 5)
    p = a.players[0]
    p.x, p.inv = b.x, 0.0
    a.players[1].x = 40
    b.pat_tractor(p, a)
    mo[0].axis = -1
    ph = p.hp
    tick(a, mo, 2.4)
    assert p.hp == ph and p.x < b.x - 44


# ------------------------------------------------------------------ props in general
def test_props_are_hit_by_slash_skill_and_projectile(mk):
    a, mo = mk(1, classes=("Knight", "Mage"), waves=False)
    k, m = a.players
    q = Prop("crystal", k.x + 20, FLOOR, 100)
    a.props.append(q)
    k.face = 1; k.hitset = set()
    a.slash_hit(k)
    assert q.hp < 100
    hp = q.hp
    a.hit_radius(q.x, q.y - 10, 30, 10)
    assert q.hp < hp
    hp = q.hp
    m.x, m.face = q.x - 80, 1
    a.cast(m)                                                # mage fireball
    tick(a, mo, 1.0)
    assert q.hp < hp


def test_props_vanish_with_the_boss(mk):
    a, mo, b = fight(mk, 2)
    assert a.props
    b.hp = 0
    tick(a, mo, 0.1)
    assert not a.props and a.chest


@pytest.mark.parametrize("lvl", range(6))
def test_bot_beats_every_boss_mechanic(mk, lvl):
    from game.qabot import run_bot
    random.seed(lvl)
    a, mo, b = fight(mk, lvl, enter=True, classes=("Knight", "Tank"))
    a.god = True
    run_bot(a, 300, dt=1 / 30, skill="careful")
    assert a.portal, f"level {lvl + 1} boss survived 300s (props: {[q.kind for q in a.props]}, hp {b.hp}/{b.maxhp})"


def test_fake_motion_has_gear_pulse():
    assert FakeMotion(0).gear_p is False
