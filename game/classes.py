"""Hero classes."""
from .config import *


CLASSES = {
    "Knight": dict(
        spec=None, bonus=.08, hp=8, atk=6, df=7, cd=6, cd2=10,
        role="Vanguard / Support",
        skill="Holy Charge",
        sdesc="Dash forward slashing foes. Invulnerable while charging.",
        skill2="Aegis Banner",
        s2desc="Plant a radiant banner: heals nearby allies (+25 HP) and knocks back foes.",
        pdesc="Passive: +8% score in every loot mini-game."
    ),
    "Tank": dict(
        spec="parry", bonus=.15, hp=10, atk=4, df=10, cd=8, cd2=9,
        role="Juggernaut / Crowd Control",
        skill="Earthquake Slam",
        sdesc="Smash the ground: heavy AoE damage and STUNS nearby foes for 1.5s.",
        skill2="Iron Taunt",
        s2desc="Roar to pull enemies toward you and gain a 30 HP barrier for 4s.",
        pdesc="Passive: +15% score in the Parry mini-game."
    ),
    "Fighter": dict(
        spec="slash", bonus=.15, hp=7, atk=9, df=4, cd=7, cd2=5,
        role="Relentless Bruiser",
        skill="Whirlwind",
        sdesc="Spin for 0.7s, rapidly slicing everything around you while moving.",
        skill2="Blade Wave",
        s2desc="Launch a piercing crescent wave that cuts through every enemy in a line.",
        pdesc="Passive: +15% score in the Slash mini-game."
    ),
    "Mage": dict(
        spec="dice", bonus=.15, hp=4, atk=10, df=2, cd=5, cd2=8,
        role="Arcane Artillery",
        skill="Fireball",
        sdesc="Hurl an explosive firebolt that detonates on impact for huge AoE damage.",
        skill2="Frost Nova",
        s2desc="Blast an icy ring around you: damages and FREEZES nearby foes for 2.0s.",
        pdesc="Passive: +15% score in the Dice Roll mini-game."
    ),
    "Rogue": dict(
        spec="lock", bonus=.15, hp=5, atk=8, df=3, cd=6, cd2=5,
        role="Mobile Assassin",
        skill="Shadow Step",
        sdesc="Blink behind the nearest enemy and deliver a 2.4x backstab.",
        skill2="Fan of Knives",
        s2desc="Leap back slightly and throw 3 fast daggers in a wide spread.",
        pdesc="Passive: +15% score in the Lock Pick mini-game."
    ),
}
CLASS_NAMES = list(CLASSES)


def bonus_for(cls, kind):
    d = CLASSES[cls]
    return d["bonus"] if d["spec"] in (None, kind) else 0.0
