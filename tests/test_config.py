import json

import pytest

from game import config
from game.config import difficulty


def test_difficulty_level_one_is_neutral():
    assert difficulty(0) == (1.0, 1.0)


@pytest.mark.parametrize("lvl", range(6))
def test_difficulty_compounds_25_percent_per_level(lvl):
    taken, dealt = difficulty(lvl)
    assert taken == pytest.approx(0.75 ** lvl)
    assert dealt == pytest.approx(1.25 ** lvl)


def test_difficulty_monotonic_and_never_zero():
    prev = difficulty(0)
    for lvl in range(1, 12):
        cur = difficulty(lvl)
        assert 0 < cur[0] < prev[0] and cur[1] > prev[1]  # a flat +25% would reach 0 damage taken by level 5; compounding must not
        prev = cur


def test_difficulty_clamps_negative_levels():
    assert difficulty(-3) == (1.0, 1.0)


def test_settings_defaults_when_no_file():
    s = config.load_settings()
    assert s["tutorial_done"] is False and len(s["keys"]) == 2


def test_settings_partial_file_keeps_tutorial_flag(tmp_path):
    (tmp_path / "rogue_settings.json").write_text(json.dumps({"tutorial_done": True}))
    assert config.load_settings()["tutorial_done"] is True  # regression: flag used to be lost when "keys" was missing


@pytest.mark.parametrize("raw", ["not json", "[]", "null", "{\"keys\": 5}", ""])
def test_settings_garbage_falls_back_to_defaults(tmp_path, raw):
    (tmp_path / "rogue_settings.json").write_text(raw)
    s = config.load_settings()
    assert s["keys"] == [dict(k) for k in config.DEFAULT_KEYS]


def test_settings_roundtrip(tmp_path):
    config.SET["tutorial_done"] = True
    config.SET["keys"][0]["jump"] = 1234
    config.save_settings()
    s = config.load_settings()
    assert s["tutorial_done"] is True and s["keys"][0]["jump"] == 1234


def test_dev_flag_is_not_persisted(tmp_path):
    config.DEV = True
    try:
        config.save_settings()
        assert "DEV" not in json.loads((tmp_path / "rogue_settings.json").read_text())
    finally:
        config.DEV = False
