"""Castle Maker data model: validation, building levels, saving / loading, tiers."""
import copy
import json
import os
import pytest

from game import castle as C
from game.levels import LEVELS


def good(n=2):
    c = C.new_castle("Test Castle")
    for i in range(1, n): c["levels"].append(C.default_level(i % 6))
    return c


def test_new_and_default_castles_are_valid():
    assert C.validate_castle(C.new_castle()) == []
    assert all(C.validate_castle(dict(name="x", levels=[C.default_level(t)])) == [] for t in range(6))


@pytest.mark.parametrize("mutate,needle", [
    (lambda c: c.update(name=""), "name"),
    (lambda c: c.update(levels=[]), "at least 1 level"),
    (lambda c: c.update(levels=[C.default_level(0)] * 11), "too many levels"),
    (lambda c: c["levels"][0].update(theme=9), "theme"),
    (lambda c: c["levels"][0].update(layout="Z"), "layout"),
    (lambda c: c["levels"][0].update(boss="nope"), "boss"),
    (lambda c: c["levels"][0].update(waves=[]), "wave"),
    (lambda c: c["levels"][0].update(waves=[[["zombie", 0]]]), "bad entry"),
    (lambda c: c["levels"][0].update(waves=[[["dragon", 2]]]), "bad entry"),
    (lambda c: c["levels"][0].update(waves=[[["zombie", 15]]]), "max"),
    (lambda c: c["levels"][0].update(waves=[[["zombie", 1]]] * 9), "too many waves"),
    (lambda c: c["levels"][0].update(waves=[[["zombie", True]]]), "bad entry"),
    (lambda c: c["levels"][0].update(waves=[[]]), "empty"),
])
def test_invalid_castles_are_rejected_with_a_reason(mutate, needle):
    c = good(1)
    mutate(c)
    errs = C.validate_castle(c)
    assert errs and any(needle in e for e in errs), errs


def test_garbage_is_rejected_not_crashed():
    for bad in (None, [], "x", 5, {"name": "a", "levels": "x"}, {"name": "a", "levels": [5]}, {"name": "a", "levels": [{"theme": 0, "waves": [5]}]}):
        assert C.validate_castle(bad)


def test_build_level_has_every_key_the_arena_needs():
    for t in range(6):
        L = C.build_level(dict(theme=t, layout="B", waves=[[["zombie", 2], ["bat", 1]]], boss="don"))
        for k in ("name", "tag", "sky", "floor", "top", "plat", "plats", "waves", "boss", "tint", "amb", "bg"):
            assert k in L, k
        assert L["plats"] == C.LAYOUTS["B"] and L["boss"] == "don" and L["waves"] == [[("zombie", 2), ("bat", 1)]] and L["style"] == "wave"
        assert "length" not in L and "pits" not in L                      # a custom level is a one-screen arena
    assert C.build_level(dict(theme=2, waves=[[["knight", 1]]], boss="paladin"))["chest"] is True
    assert C.build_level(dict(theme=2, waves=[[["knight", 1]]], boss="don"))["chest"] is False
    assert LEVELS[0]["plats"] != C.LAYOUTS["none"]                         # the template itself was not modified
    assert C.build_level(dict(theme=0, waves=[[["zombie", 1]]], boss=None, name="Mine"))["name"] == "Mine"


def test_save_and_load_roundtrip(tmp_path):
    c = good(3)
    path = C.save_castle(c, str(tmp_path))
    assert os.path.basename(path) == "test_castle.json"
    spec, errs = C.load_castle(path)
    assert errs == [] and spec == c
    assert [r[1:] for r in C.list_castles(str(tmp_path))] == [("Test Castle", 3, [])]


def test_saving_an_invalid_castle_raises_and_writes_nothing(tmp_path):
    c = good(1); c["levels"][0]["boss"] = "nope"
    with pytest.raises(ValueError): C.save_castle(c, str(tmp_path))
    assert os.listdir(tmp_path) == []


def test_corrupt_and_invalid_files_are_listed_with_errors(tmp_path):
    (tmp_path / "broken.json").write_text("{not json")
    (tmp_path / "wrong.json").write_text(json.dumps({"name": "W", "levels": [{"theme": 99}]}))
    C.save_castle(good(1), str(tmp_path))
    rows = {os.path.basename(r[0]): r for r in C.list_castles(str(tmp_path))}
    assert rows["broken.json"][3] and rows["wrong.json"][3] and not rows["test_castle.json"][3]
    assert C.load_castle(str(tmp_path / "nope.json"))[0] is None


def test_slug_is_filesystem_safe():
    assert C.slug("My Castle!! ../x") == "my_castle_x" and C.slug("???") == "castle"


def test_tier_spreads_long_castles_over_0_to_5():
    assert [C.tier_for(i, 6) for i in range(6)] == [0, 1, 2, 3, 4, 5]
    assert [C.tier_for(i, 3) for i in range(3)] == [0, 1, 2]
    t = [C.tier_for(i, 10) for i in range(10)]
    assert t[0] == 0 and t[-1] == 5 and t == sorted(t) and C.tier_for(0, 1) == 0
    assert copy.deepcopy(good(10))["levels"].__len__() == 10
