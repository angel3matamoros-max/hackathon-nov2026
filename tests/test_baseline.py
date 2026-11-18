"""Characterization: deterministic bot runs must match results recorded from the original monolith."""
import json
import os
import random

import pytest

from helpers import run_bot
from game.arena import Arena
from game.levels import AREAS
from game.player import Player

GOLDEN = json.load(open(os.path.join(os.path.dirname(__file__), "golden_baseline.json")))


@pytest.mark.parametrize("area", range(len(AREAS)))
def test_area_simulation_matches_original(area):
    random.seed(1000 + area)
    a = Arena(area, [Player(0, "Knight", 80), Player(1, "Mage", 110)])
    run_bot(a, 25)
    got = dict(t=round(a.t, 2), kills=a.kills, enemies=len(a.enemies), queue=len(a.queue), portal=a.portal,
               hp=[p.hp for p in a.players], pos=[round(p.x, 1) for p in a.players], state=a.state, result=a.result)
    assert got == GOLDEN[str(area)]
