import random

import pytest

from game.bosses import BOSSES, BOSS_HP, BOSS_KINDS, WIND, Boss
from game.config import FLOOR
from game.levels import LEVELS
from game.qabot import run_bot


def boss_arena(mk, level, **kw):
    a, mo = mk(level, **kw)
    a.spawn_boss()
    a.boss.intro, a.boss.x = 0.0, a.boss.home          # skip the entrance
    return a, mo, a.boss


def test_boss_per_level_matches_data(mk):
    for lvl in range(6):
        a, _, b = boss_arena(mk, lvl)
        assert isinstance(b, Boss) and b.kind == LEVELS[lvl]["boss"] and b.hp == b.maxhp == BOSS_HP[lvl] and b in a.enemies
        assert a.boss_spawned and "BOSS" in a.banner[0]


def test_boss_spawns_only_after_all_waves_cleared(mk):
    a, mo = mk(0, waves=True)
    n = len(a.waves)
    assert n >= 3 and not a.boss_spawned
    seen = []
    for _ in range(60 * 90):  # clear each wave the moment it is fully spawned
        a.update(1 / 60, mo)
        if a.boss_spawned: break
        if a.wave_live and not a.queue and a.enemies:
            seen.append(a.wave)
            assert not a.boss_spawned
            for e in list(a.enemies): e.hp = 0
    assert seen == list(range(n))                 # every wave was fought, in order
    assert a.boss_spawned and a.boss.hp > 0 and not a.portal


def test_next_wave_waits_for_the_previous_one_to_be_cleared(mk):
    a, mo = mk(0, waves=True)
    a.god = True                                   # idle heroes must survive the whole wait
    for _ in range(60 * 4): a.update(1 / 60, mo)
    assert a.wave == 0 and a.wave_live
    for _ in range(60 * 20): a.update(1 / 60, mo)  # nobody kills anything, so wave 1 must never start
    assert a.wave == 0 and not a.boss_spawned


@pytest.mark.parametrize("kind", BOSS_KINDS)
@pytest.mark.parametrize("phase", range(3))
def test_every_pattern_in_every_phase_executes(mk, monkeypatch, kind, phase):
    lvl = [i for i, l in enumerate(LEVELS) if l["boss"] == kind][0]
    a, mo, b = boss_arena(mk, lvl)
    b.phase = phase
    b.hp = b.maxhp * (0.9, 0.5, 0.2)[phase]
    for name in BOSSES[kind]["pats"][min(phase, len(BOSSES[kind]["pats"]) - 1)]:
        a.eprojs, a.hazards, b.queue = [], [], []
        b.act, b.rest, b.dash, b.last = None, 0.0, None, None
        monkeypatch.setattr(random, "choice", lambda seq, n=name: n if n in seq else seq[0])
        b.choose(a.players[0], a)
        monkeypatch.undo()
        key = "raise_" if name == "raise" else name
        assert b.act == key and b.state == "wind"      # telegraphed before it hits
        calls = []
        real = getattr(b, "pat_" + name)
        setattr(b, "pat_" + name, lambda t, ar, r=real: (calls.append(1), r(t, ar)))
        for p in a.players: p.inv = 99
        for _ in range(int((WIND[key] + 0.3) * 60)): a.update(1 / 60, mo)
        assert calls, f"{kind}/{name} never executed"
        for _ in range(120): a.update(1 / 60, mo)       # and its effects (queued shots, hazards, minions) resolve cleanly


def test_phases_trigger_at_66_and_33_percent(mk):
    a, mo, b = boss_arena(mk, 0)
    a.update(1 / 60, mo); assert b.phase == 0
    b.hp = b.maxhp * 0.60; a.update(1 / 60, mo); assert b.phase == 1
    assert any(t[2] == "ENRAGED!" for t in a.texts)
    b.hp = b.maxhp * 0.30; a.update(1 / 60, mo); assert b.phase == 2


def test_boss_defeat_opens_portal_clears_threats_and_kills_summons(mk):
    a, mo, b = boss_arena(mk, 0)
    a.spawn("zombie", x=100)
    a.eshot(b, 200, 100, 0, 0, 10, "bullet"); a.hazard("pillar", 0, 10, 0, 10, 1, 1, 1, b)
    a.players[1].down = True
    b.hp = 0
    a.update(1 / 60, mo)
    assert a.portal and not a.eprojs and not a.hazards and not a.players[1].down
    a.update(1 / 60, mo)
    assert not [e for e in a.enemies if e.kind != "dummy"]
    assert any(c["boss"] for c in a.corpses)  # the boss corpse is plain: the boss chest is the reward


def test_every_boss_drops_a_chest_and_only_level3_offers_the_holy_weapon(mk):
    for lvl in range(6):
        a, mo, b = boss_arena(mk, lvl)
        b.hp = 0
        a.update(1 / 60, mo)
        assert a.chest and a.chest["holy"] == (lvl == 2)


def test_portal_waits_for_boss(mk):
    a, mo = mk(0, waves=True)
    a.queue = []
    for e in list(a.enemies): e.hp = 0
    for _ in range(5): a.update(1 / 60, mo)
    for p in a.players: p.x = 470
    for _ in range(5): a.update(1 / 60, mo)
    assert a.result is None                          # boss alive: standing at the exit does nothing


def test_perfect_block_stuns_boss_only_briefly(mk):
    a, mo, b = boss_arena(mk, 0)
    p = a.players[0]
    p.face, p.block, p.block_t = 1, True, 0.05
    b.x = p.x + 20
    p.take(30, b.x, a, b)
    assert 0 < b.stun <= 1.4 * 0.4 + 1e-6


def test_boss_resists_knockback_and_freeze(mk):
    a, mo, b = boss_arena(mk, 0)
    a.hurt(b, 10, 200)
    assert abs(b.kb) < 40
    p = a.players[1]                                   # Mage frost nova
    p.cls = "Mage"; b.x, p.x = 100, 100
    a.cast2(p)
    assert 0 < b.frozen < 1.0


def test_stunned_boss_cancels_its_attack(mk):
    a, mo, b = boss_arena(mk, 0)
    b.rest = 0
    b.choose(a.players[0], a)
    assert b.act
    b.stun = 1.0
    a.update(1 / 60, mo)
    assert b.act is None


def test_flying_boss_hovers_within_reach(mk):
    a, mo, b = boss_arena(mk, 5)
    for _ in range(120): a.update(1 / 60, mo)
    assert FLOOR - 70 < b.y < FLOOR + 1 and BOSSES["tycoon"]["fly"]


def test_boss_can_be_killed_by_player_attacks(mk):
    a, mo, b = boss_arena(mk, 0, classes=("Fighter", "Knight"))
    a.god = True
    run_bot(a, 200, dt=1 / 30, skill="careful")
    assert b.hp <= 0 and a.portal


def test_boss_kind_names_and_alien_name_constant():
    from game import config
    assert config.ALIEN_NAME in BOSSES["tycoon"]["name"]


def test_portal_has_a_grace_period_so_nobody_is_whisked_away_while_looting(mk):
    """Regression: a player standing at the exit when the boss died used to leave the level on the very next frame."""
    a, mo, b = boss_arena(mk, 2)
    for p in a.players: p.x = 465.0
    b.hp = 0
    for _ in range(30): a.update(1 / 60, mo)               # 0.5 s after the kill: portal is open but not yet usable
    assert a.portal and a.result is None
    for _ in range(120): a.update(1 / 60, mo)
    assert a.result == "next"
