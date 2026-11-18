"""Hand controller logic, tested with synthetic sample streams (no hardware needed).
Sample layout: (accelX, accelY, accelZ, b1, b2, jx, jy, jsw)."""
import pygame
import pytest

from game import padbridge as P
from game.inputs import make_motions, Motion
from game.qabot import FakeMotion

REST = (640, 260, 16632, 0, 0, 512, 512, 0)  # what the real board reads at rest


@pytest.fixture(autouse=True)
def no_display(monkeypatch):
    """PadMotion reads the keyboard through pygame; there is no window in tests, so no keys are pressed."""
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: [False] * 512)


def calibrated(t0=0.0):
    st = P.PadState()
    for k in range(P.CALIB_SAMPLES): st.feed(REST, t0 + k * 0.05)
    return st, t0 + P.CALIB_SAMPLES * 0.05


def run(st, samples, t, dt=0.05):
    for smp in samples:
        st.feed(smp, t); t += dt
    return t


def pressed(st):
    held, pulses, axis = st.snapshot()
    return held, pulses, axis


# ------------------------------------------------------------------ parsing
def test_parse_accepts_a_good_line_and_rejects_bad_ones():
    assert P.parse_line(b"640,260,16632,0,1,512,900,0\r\n") == (640, 260, 16632, 0, 1, 512, 900, 0)
    for bad in (b"", b"1,2,3", b"a,b,c,d,e,f,g,h", b"1,2,3,4,5,6,7,8,9", b"640,260,16632,2,0,512,512,0",
                b"640,260,16632,0,0,2000,512,0", b"99999,0,0,0,0,0,0,0", b"\xff\xfe,,,"):
        assert P.parse_line(bad) is None, bad


def test_reader_counts_bad_lines_and_state_survives_them():
    st, t = calibrated()
    assert P.parse_line("garbage") is None
    t = run(st, [REST], t)                                   # a good sample still works afterwards
    assert st.samples == P.CALIB_SAMPLES + 1


# ------------------------------------------------------------------ calibration
def test_nothing_fires_during_calibration_and_ready_is_announced():
    st = P.PadState()
    for k in range(P.CALIB_SAMPLES - 1):
        st.feed((640, 260, 16632, 1, 1, 900, 0, 1), k * 0.05)  # buttons held during calibration: no presses
    assert st.base is None and not st.pulses
    st.feed(REST, 1.0)
    assert st.base is not None
    assert any("Ready" in m for m in st.drain_log())
    assert abs(st.base[2] - 16632) < 1e-6 or st.base[2] > 0


# ------------------------------------------------------------------ joystick and buttons
def test_joystick_up_jumps_once_and_is_held_while_up():
    st, t = calibrated()
    up = (640, 260, 16632, 0, 0, 512, 900, 0)
    t = run(st, [up, up, up], t)
    held, pulses, _ = pressed(st)
    assert "joy_up" in held and pulses.get("joy_up") is True
    t = run(st, [up, up], t)
    held, pulses, _ = pressed(st)
    assert "joy_up" in held and "joy_up" not in pulses       # held, but no repeat pulses
    assert "JUMP" in " ".join(st.drain_log())


def test_jump_release_has_hysteresis_so_it_does_not_chatter():
    st, t = calibrated()
    up = (640, 260, 16632, 0, 0, 512, 900, 0)
    just_under = (640, 260, 16632, 0, 0, 512, P.JOY_UP - P.JOY_HYST + 5, 0)  # inside the hysteresis band: stays up
    t = run(st, [up, up, just_under, just_under, just_under], t)
    assert "joy_up" in pressed(st)[0]
    t = run(st, [(640, 260, 16632, 0, 0, 512, 500, 0)] * 2, t)
    assert "joy_up" not in pressed(st)[0]


def test_joystick_down_drops_and_left_right_walk_and_pulse_for_menus():
    st, t = calibrated()
    t = run(st, [(640, 260, 16632, 0, 0, 512, 100, 0)] * 3, t)
    held, pulses, _ = pressed(st)
    assert "joy_down" in held and pulses.get("joy_down") is True
    t = run(st, [(640, 260, 16632, 0, 0, 100, 512, 0)] * 2, t)
    held, pulses, axis = pressed(st)
    assert axis == -1 and pulses.get("left") is True
    t = run(st, [(640, 260, 16632, 0, 0, 512, 512, 0)] * 2, t)
    assert pressed(st)[2] == 0


def test_button_debounce_ignores_a_one_sample_glitch():
    st, t = calibrated()
    glitch = (640, 260, 16632, 1, 0, 512, 512, 0)
    t = run(st, [glitch, REST, REST, REST], t)
    assert "btn1" not in pressed(st)[1] and "btn1" not in pressed(st)[0]


def test_button_press_is_one_clean_pulse_with_the_debounce_delay():
    st, t = calibrated()
    b1 = (640, 260, 16632, 1, 0, 512, 512, 0)
    t = run(st, [b1, b1], t)                                 # needs DEBOUNCE_SAMPLES samples to count
    held, pulses, _ = pressed(st)
    assert pulses.get("btn1") is True and "btn1" in held
    t = run(st, [b1, b1, b1], t)
    assert "btn1" not in pressed(st)[1]                       # still held, no second pulse
    t = run(st, [REST, REST], t)
    assert "btn1" not in pressed(st)[0]


def test_stick_click_is_a_boost_pulse():
    st, t = calibrated()
    click = (640, 260, 16632, 0, 0, 512, 512, 1)
    t = run(st, [click, click], t)
    assert pressed(st)[1].get("joy_click") is True and "BOOST" in " ".join(st.drain_log())


# ------------------------------------------------------------------ gestures
def test_a_swing_is_an_attack_with_a_direction_and_a_cooldown():
    st, t = calibrated()
    t = run(st, [(640 + 9000, 260, 16632, 0, 0, 512, 512, 0)], t)          # out: a swing to the right
    held, pulses, _ = pressed(st)
    assert pulses.get("attack") == "right" and "SWING! (right)" in " ".join(st.drain_log())
    t = run(st, [REST], t)                                                  # the return jerk is not a second attack
    assert "attack" not in pressed(st)[1]
    t = run(st, [(640 + 9000, 260, 16632, 0, 0, 512, 512, 0), REST], t)     # same direction, inside the cooldown: ignored
    assert "attack" not in pressed(st)[1]
    t = run(st, [(640 - 9000, 260, 16632, 0, 0, 512, 512, 0)], t + 1.2)     # later, a real swing the other way works
    assert pressed(st)[1].get("attack") == "left"


def test_a_vertical_swing_reports_up_or_down():
    st, t = calibrated()
    t = run(st, [(640, 260 + 9000, 16632, 0, 0, 512, 512, 0)], t)
    assert pressed(st)[1].get("attack") == "up"


def test_a_shove_on_z_is_interact_held_for_a_moment():
    st, t = calibrated()
    t = run(st, [(640, 260, 16632 + 9000, 0, 0, 512, 512, 0)], t)
    held, pulses, _ = pressed(st)
    assert pulses.get("shove") is True and "shove" in held and "SHOVE" in " ".join(st.drain_log())
    t = run(st, [REST] * int(P.SHOVE_HOLD / 0.05 + 3), t)
    assert "shove" not in pressed(st)[0]


def test_shield_turns_on_after_the_pose_is_held_and_off_when_released():
    st, t = calibrated()
    up_pose = (640, 260 - P.SHIELD_TILT - 500, 16632, 0, 0, 512, 512, 0)   # accelY falls: tipped up (SHIELD_SIGN = -1)
    t = run(st, [up_pose], t)
    assert "shield" not in pressed(st)[0]                      # not yet: needs SHIELD_HOLD
    t = run(st, [up_pose] * 5, t)
    assert "shield" in pressed(st)[0]
    t = run(st, [REST] * 2, t)
    assert "shield" not in pressed(st)[0]


def test_a_brief_tilt_does_not_raise_the_shield():
    st, t = calibrated()
    up_pose = (640, 260 - P.SHIELD_TILT - 500, 16632, 0, 0, 512, 512, 0)
    t = run(st, [up_pose, REST, up_pose, REST], t)
    assert "shield" not in pressed(st)[0]


# ------------------------------------------------------------------ mapping onto the game's Motion fields
class FakeReader:
    def __init__(s, state): s.state = state


def test_pad_motion_fills_the_motion_fields_the_game_reads():
    st, t = calibrated()
    m = P.PadMotion(0, FakeReader(st))
    t = run(st, [(640, 260, 16632, 0, 0, 512, 900, 0)], t)   # jump
    m.update([], 1 / 60)
    assert m.jump_p and m.jump_h
    m.update([], 1 / 60)
    assert not m.jump_p and m.jump_h                          # held carries over, the pulse does not
    t = run(st, [(640, 260, 16632, 1, 0, 512, 512, 0)] * 2, t)
    m.update([], 1 / 60)
    assert m.cast_p
    t = run(st, [(640, 260, 16632, 0, 1, 512, 512, 0)] * 2, t)
    m.update([], 1 / 60)
    assert m.cast2_p
    t = run(st, [(640 + 9000, 260, 16632, 0, 0, 512, 512, 0)], t)
    m.update([], 1 / 60)
    assert m.slash_p and m.flick and m.swing == "right"
    t = run(st, [(640, 260, 16632, 0, 0, 100, 512, 0)] * 2, t)
    m.update([], 1 / 60)
    assert m.axis == -1


def test_keyboard_still_works_alongside_the_pad(monkeypatch):
    st, _ = calibrated()
    m = P.PadMotion(0, FakeReader(st))
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: [False] * 512)
    key = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)  # P1 slash on the keyboard
    m.update([key], 1 / 60)
    assert m.slash_p


def test_pad_menu_keys_drive_the_menus(monkeypatch):
    st, t = calibrated()
    m = P.PadMotion(0, FakeReader(st))
    t = run(st, [(640, 260, 16632, 0, 0, 512, 900, 0)], t)
    m.update([], 1 / 60)
    assert pygame.K_UP in m.menu_keys()
    t = run(st, [(640, 260, 16632, 1, 0, 512, 512, 0)] * 2, t)
    m.update([], 1 / 60)
    assert pygame.K_RETURN in m.menu_keys()
    m.update([], 1 / 60)
    assert m.menu_keys() == []


def test_make_motions_keyboard_is_unchanged_and_auto_falls_back(monkeypatch):
    assert all(type(x) is Motion for x in make_motions("keyboard"))
    monkeypatch.setenv("ROGUE_PAD", "0")
    assert all(type(x) is Motion for x in make_motions("auto"))


def test_game_menus_take_pad_keys():
    from game.app import Game
    st, t = calibrated()
    pm = P.PadMotion(0, FakeReader(st))
    g = Game(dev=False, motions=[pm, FakeMotion(1)])
    g.mode = "menu"
    g.msel = 0
    t = run(st, [(640, 260, 16632, 0, 0, 512, 900, 0)], t)  # stick up = menu up
    g.step(1 / 30, [])
    assert g.msel == len(g.menu_items()) - 1                 # wrapped up from START
