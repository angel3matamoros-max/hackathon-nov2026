"""PS2 controller logic, tested with synthetic samples (no hardware). Sample: (b1, b2, rx, ry, lx, ly); button bits 1 = pressed."""
import pygame
import pytest

from game import padbridge as P

REST = (0, 0, 128, 128, 128, 128)
CROSS, SQUARE, L1 = (0, 1 << 6), (0, 1 << 7), (0, 1 << 2)
START = (1 << 3, 0)


@pytest.fixture(autouse=True)
def no_display(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: [False] * 512)


def sample(btn=(0, 0), rx=128, ry=128, lx=128, ly=128):
    return (btn[0], btn[1], rx, ry, lx, ly)


def test_parse_accepts_a_good_line_and_rejects_bad_ones():
    assert P.parse_ps2_line(b"P,0,64,128,128,128,128\r\n") == (0, 64, 128, 128, 128, 128)
    for bad in (b"", b"P,1,2,3", b"X,0,0,128,128,128,128", b"P,0,0,128,128,128,300", b"P,a,b,c,d,e,f", b"P,0,0,128,128,128,128,0", b"\xff\xfe"):
        assert P.parse_ps2_line(bad) is None, bad


def test_first_sample_is_a_baseline_and_a_press_pulses_once():
    st = P.Ps2State()
    st.feed(sample(CROSS))                      # already held at start: no pulse
    assert "CROSS" in st.snapshot()[0] and not st.snapshot()[1]
    st.feed(REST); st.feed(sample(CROSS))
    held, pulses, _ = st.snapshot()
    assert "CROSS" in held and pulses.get("CROSS")
    st.feed(sample(CROSS))
    assert "CROSS" not in st.snapshot()[1]      # held, no repeat


def test_stick_and_dpad_both_walk_and_drop():
    st = P.Ps2State(); st.feed(REST)
    st.feed(sample(lx=255)); assert st.snapshot()[2] == 1
    st.feed(sample(lx=0)); assert st.snapshot()[2] == -1
    st.feed(sample(btn=(1 << 7, 0))); assert st.snapshot()[2] == -1      # D-pad left
    st.feed(sample(ly=255)); assert "DOWN" in st.snapshot()[0]
    st.feed(sample(lx=128 + P.PS2_DEADZONE - 1)); assert st.snapshot()[2] == 0   # inside the dead zone


class Reader:
    def __init__(self): self.state, self.ps2 = P.PadState(), P.Ps2State()


def motion():
    r = Reader()
    m = P.PadMotion(0, r)
    r.ps2.feed(REST)
    return m, r.ps2


def test_default_map_drives_the_game_fields():
    m, ps = motion()
    ps.feed(sample(CROSS)); m.update([], 0.016)
    assert m.jump_p and m.jump_h
    ps.feed(REST); m.update([], 0.016)
    for btn, field in ((SQUARE, "slash_p"), (L1, "cast_p"), ((0, 1 << 3), "cast2_p"), ((0, 1 << 5), "dash_p")):
        ps.feed(sample(btn)); m.update([], 0.016)
        assert getattr(m, field), field
        ps.feed(REST); m.update([], 0.016)
    ps.feed(sample((0, 1 << 0))); m.update([], 0.016)
    assert m.block_h
    ps.feed(sample((0, 1 << 4))); m.update([], 0.016)
    assert m.interact_h


def test_attack_is_aimed_by_the_stick():
    m, ps = motion()
    ps.feed(sample(SQUARE, lx=255)); m.update([], 0.016)
    assert m.slash_p and m.swing == "right"


def test_menus_use_dpad_start_and_back_buttons():
    m, ps = motion()
    ps.feed(sample(START)); m.update([], 0.016)
    assert pygame.K_RETURN in m.menu_keys()
    ps.feed(REST); m.update([], 0.016)
    ps.feed(sample((1 << 0, 0))); m.update([], 0.016)       # SELECT
    assert pygame.K_ESCAPE in m.menu_keys()
    ps.feed(REST); m.update([], 0.016)
    ps.feed(sample(ly=0)); m.update([], 0.016)
    assert pygame.K_UP in m.menu_keys()


def test_remapping_changes_the_action(monkeypatch):
    monkeypatch.setitem(P.PS2_MAP, "jump", "CIRCLE")
    m, ps = motion()
    ps.feed(sample(CROSS)); m.update([], 0.016)
    assert not m.jump_p
    ps.feed(REST); m.update([], 0.016)
    ps.feed(sample((0, 1 << 5))); m.update([], 0.016)
    assert m.jump_p
