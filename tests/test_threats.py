"""Enemy projectiles and boss hazards (Arena.update_threats)."""
import pytest

from game.config import FLOOR


def shot(a, p, **kw):
    pr = dict(x=p.x - 20, y=p.y - 16, vx=200.0, vy=0.0, g=0.0, dmg=20.0, life=2.0, kind="bullet", src=None, blast=0)
    pr.update(kw)
    a.eprojs.append(pr)
    return pr


@pytest.fixture
def one(mk):
    a, mo = mk(4, classes=("Fighter", "Knight"))
    a.players[1].down = True
    p = a.players[0]
    p.face = -1  # facing left, towards the shooter (bullets in these tests travel right, from the left)
    return a, p


def test_bullet_damages_player_and_is_consumed(one):
    a, p = one
    shot(a, p)
    for _ in range(10): a.update_threats(1 / 60)
    assert p.hp < p.maxhp and not a.eprojs


def test_blocking_reduces_bullet_damage(one):
    a, p = one
    p.block, p.block_t = True, 1.0
    shot(a, p, dmg=100.0)
    for _ in range(10): a.update_threats(1 / 60)
    assert 0 < p.maxhp - p.hp < 30


def test_perfect_block_reflects_bullet_back(one):
    a, p = one
    p.block, p.block_t = True, 0.05
    shot(a, p)
    for _ in range(10): a.update_threats(1 / 60)
    assert p.hp == p.maxhp and p.perfects == 1
    assert a.projs and a.projs[0]["vx"] < 0 and not a.eprojs


def test_ground_wave_can_be_jumped(one):
    a, p = one
    p.y = FLOOR - 40
    shot(a, p, kind="wave", y=FLOOR - 6)
    for _ in range(10): a.update_threats(1 / 60)
    assert p.hp == p.maxhp


def test_orphan_projectile_whose_shooter_died_still_works(one):
    a, p = one
    ghost = a.spawn("gunman", x=50)
    ghost.hp = 0
    a.enemies.remove(ghost)
    shot(a, p, src=ghost)
    for _ in range(10): a.update_threats(1 / 60)
    assert p.hp < p.maxhp


def test_lob_explodes_on_ground_with_area_damage(one):
    a, p = one
    pr = dict(x=p.x + 10, y=FLOOR - 30, vx=0.0, vy=200.0, g=0.0, dmg=30.0, life=3.0, kind="dyn", src=None, blast=40)
    a.eprojs.append(pr)
    for _ in range(30): a.update_threats(1 / 60)
    assert p.hp < p.maxhp and not a.eprojs


def test_lob_outside_blast_radius_is_harmless(one):
    a, p = one
    a.eprojs.append(dict(x=p.x + 150, y=FLOOR - 30, vx=0.0, vy=200.0, g=0.0, dmg=30.0, life=3.0, kind="dyn", src=None, blast=40))
    for _ in range(30): a.update_threats(1 / 60)
    assert p.hp == p.maxhp


def test_hazard_warns_then_hits_once(one):
    a, p = one
    a.hazard("pillar", p.x - 12, p.x + 12, 0, FLOOR + 4, 0.5, 0.3, 25.0, None)
    for _ in range(20): a.update_threats(1 / 60)
    assert p.hp == p.maxhp                                   # still warning
    for _ in range(60):
        a.update_threats(1 / 60); p.inv = 0
    lost = p.maxhp - p.hp
    assert lost > 0 and not a.hazards
    assert lost <= 25                                         # hit exactly once, not once per frame


def test_beam_misses_player_standing_above_it(one):
    a, p = one
    a.hazard("beam", 0, 480, FLOOR - 20, FLOOR - 6, 0.0, 0.5, 25.0, None)
    p.y = FLOOR - 60
    for _ in range(30): a.update_threats(1 / 60)
    assert p.hp == p.maxhp


def test_god_mode_blocks_all_threat_damage(one):
    a, p = one
    a.god = True
    shot(a, p)
    a.hazard("pillar", p.x - 12, p.x + 12, 0, FLOOR + 4, 0.0, 0.3, 25.0, None)
    for _ in range(20): a.update_threats(1 / 60)
    assert p.hp == p.maxhp


def test_blocking_does_not_stop_shots_from_behind(one):
    a, p = one
    p.face, p.block, p.block_t = 1, True, 1.0     # facing right, bullet arrives from the left (behind)
    shot(a, p, dmg=100.0)
    for _ in range(10): a.update_threats(1 / 60)
    assert p.maxhp - p.hp > 50
