"""Everything that draws must draw without error in every state (the QA agent looks at the real screenshots in qa/shots)."""
import pytest

from game.bosses import BOSS_KINDS
from game.enemies import ESTATS
from game.levels import NUM_LEVELS
from game.player import apply_gear
from game.loot import roll_holy


@pytest.mark.parametrize("lvl", range(NUM_LEVELS))
def test_level_draws_with_every_entity_type(mk, lvl):
    a, mo = mk(lvl, classes=("Rogue", "Tank"), waves=True)
    for k in list(ESTATS) + BOSS_KINDS:
        a.spawn(k, x=100 + 40 * len(a.enemies) % 300, dscale=1.0)
    a.eshot(None, 200, 100, 50, 0, 10, "bullet")
    for kind in ("soul", "laser", "wave", "dyn", "rocket"): a.eshot(None, 150, 100, 10, 0, 10, kind)
    a.hazard("pillar", 100, 120, 0, 200, 1.0, 1.0, 5, None); a.hazard("beam", 0, 480, 100, 114, 0.0, 1.0, 5, None)
    a.debug, a.god = True, True
    apply_gear(a.players[0], roll_holy("Rogue", type("R", (), {"random": lambda s: 0.1})()))
    for _ in range(30):
        a.update(1 / 30, mo)
        a.draw()


def test_chest_and_modal_draw_for_every_class(mk):
    for cls in ("Knight", "Tank", "Fighter", "Mage", "Rogue"):
        a, mo = mk(2, classes=(cls, "Knight"))
        a.spawn_boss(); a.boss.hp = 0
        a.update(1 / 60, mo)
        a.draw()
        for r in (0.1, 0.9):
            a.cm = dict(p=a.players[0], offer=roll_holy(cls, type("R", (), {"random": lambda s, v=r: v})()), sel=0, t=1.0)
            a.state = "chest"
            a.draw()
        a.state = "play"


def test_failed_and_loot_states_still_draw(mk):
    a, mo = mk(0)
    for p in a.players: p.down = True
    a.update(0.1, mo)
    a.draw()


def test_looted_corpse_draws_darkened_without_crashing(mk):
    """Regression: a negative tint (looted corpse) used to raise ValueError('invalid color argument') in blit_ent (also in v4)."""
    a, mo = mk(0)
    e = a.spawn("skeleton", x=200)
    e.hp = 0
    a.update(1 / 60, mo)
    a.corpses[0]["looted"] = True
    a.draw()
    from game.gfx import blit_ent
    import pygame
    blit_ent(pygame.Surface((4, 4), pygame.SRCALPHA), 10, 10, False, (-60, 20, -5))
