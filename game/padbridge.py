"""ELEGOO MEGA 2560 hand controller -> the game's Motion fields. Player 1 uses the pad (the keyboard still works alongside it).

Firmware: one newline-terminated CSV line about every 50 ms at 115200 baud:
    accelX,accelY,accelZ,b1,b2,jx,jy,jsw
  accel*: raw 16-bit GY-521 (MPU-6050) values, one axis per direction
  b1, b2, jsw: 1 while pressed (button 1, button 2, stick click)
  jx, jy: joystick 0..1023, resting near 512

Design: the serial port is read on a background thread (PadReader). The thread turns raw samples into held controls and one-frame
pulses (PadState, pure logic, no I/O, tested with recorded sample streams). PadMotion then maps those onto the Motion fields the game
already reads, so gameplay code does not change. Nothing is sent to the operating system as key presses.

Try it first:   .venv/bin/python main.py --pad-monitor     (prints the raw values and every gesture; use it to tune the numbers below)

Everything you are likely to want to change is in the CONFIGURATION block at the top of this file."""
import glob
import os
import threading
import time

import pygame

from .inputs import Motion

# ============================================================ CONFIGURATION (tune and remap here)
PORT = "/dev/cu.usbmodem1301"          # first port to try; if it is not there, the first /dev/cu.usbmodem* or /dev/ttyACM* is used
BAUD = 115200
CALIB_SAMPLES = 20                     # samples averaged at start-up (about 1 s) to find the "held level" baseline
JOY_UP, JOY_DOWN = 800, 200            # jy above JOY_UP = up (jump), below JOY_DOWN = down (drop through)
JOY_LEFT, JOY_RIGHT = 250, 750         # jx below JOY_LEFT = walk left, above JOY_RIGHT = walk right
JOY_HYST = 60                          # a control releases this far back toward centre, so it does not chatter
DEBOUNCE_SAMPLES = 2                   # a button / stick click must read the same new value this many samples in a row (joystick up/down: 1, it has hysteresis instead)
REVERSE_LOCKOUT = 0.6                  # after a swing, a swing the other way is ignored this long (a swing is followed by a return jerk)
SWING_DELTA = 8000                     # change in the accel vector between two samples that counts as a swing (attack)
SHOVE_DELTA = 8000                     # change along Z that counts as a shove (interact); wins over a swing
GESTURE_COOLDOWN = 0.3                 # seconds between two swings (or two shoves)
SHIELD_TILT = 12000                    # tilt from the baseline (raw accel units) that counts as "held up"
SHIELD_SIGN = -1                       # -1: tipping up makes accelY fall. Use +1 if your board is mounted the other way round
SHIELD_HOLD = 0.15                     # the pose must last this long before the shield turns on
SHOVE_HOLD = 0.6                       # a shove holds the interact key for this long (opening a chest needs a hold)

# Which control drives which game action. Controls: joy_up, joy_down, joy_click, btn1, btn2, shield (tilt up), attack (swing),
# shove (the thrust gesture). Change a right-hand side to remap, e.g. boost="btn1" to make button 1 the dash.
MAP = dict(
    jump="joy_up",         # jump (held = jump higher, edge = jump)
    down="joy_down",       # drop through a platform / fast-fall
    boost="joy_click",     # dash (the game's "boost")
    ability1="btn1",       # skill 1
    ability2="btn2",       # skill 2
    block="shield",        # block (held)
    slash="attack",        # attack (swing gesture; the direction is passed on too)
    interact="shove",      # open chests / loot (held for SHOVE_HOLD after a shove gesture)
)
INTERACT_CONTROL = "shove"  # the gesture name used for the "interact" control
BUTTON_CONTROLS = ("joy_up", "joy_down", "joy_click", "btn1", "btn2")
PRINT_EVENTS = True         # print each gesture / button press to the terminal ("Calibrating...", "Ready!", "SWING!", ...)
# ============================================================


def parse_line(line):
    """Return the 8 integers of one CSV line, or None if the line is malformed (partial reads, noise, a wrong number of fields)."""
    try:
        if isinstance(line, bytes): line = line.decode("ascii", "ignore")
        parts = line.strip().split(",")
        if len(parts) != 8: return None
        v = tuple(int(p) for p in parts)
    except ValueError:
        return None
    ax, ay, az, b1, b2, jx, jy, jsw = v
    if not all(-32768 <= a <= 32767 for a in (ax, ay, az)): return None
    if b1 not in (0, 1) or b2 not in (0, 1) or jsw not in (0, 1): return None
    if not (0 <= jx <= 1023 and 0 <= jy <= 1023): return None
    return v


class PadState:
    """All the controller logic. feed() takes one parsed sample and the current time; snapshot() gives the held controls and the
    pulses since the last call. Thread-safe (the reader thread feeds, the game reads)."""

    def __init__(s):
        s.lock = threading.Lock()
        s.calib, s.base, s.prev = [], None, None
        s.level, s.stable = {}, {}          # debounced button / stick-click state, and the samples they disagree with
        s.axis = 0
        s.pose_since, s.shield_on, s.shove_until = None, False, 0.0
        s.last = {}                          # cooldown timestamps for gestures
        s.held, s.pulses, s.log = set(), {}, []
        s.raw, s.bad, s.samples = None, 0, 0

    # ---------------------------------------------------------------- input
    def feed(s, sample, now):
        with s.lock:
            s._feed(sample, now)

    def _say(s, msg):
        if PRINT_EVENTS: s.log.append(msg)

    def _debounce(s, name, raw, need=DEBOUNCE_SAMPLES):
        st = s.stable.setdefault(name, [raw, 0])
        if raw == st[0]: st[1] = 0
        else:
            st[1] += 1
            if st[1] >= need: st[0], st[1] = raw, 0
        return st[0]

    def _button(s, name, raw, say=None, need=DEBOUNCE_SAMPLES):
        v = s._debounce(name, raw, need)
        if name not in s.level:
            s.level[name] = v  # first reading: no edge
        elif v and not s.level[name]:  # rising edge
            s.pulses[name] = True
            if say: s._say(say)
        s.level[name] = v
        return v

    def _feed(s, sample, now):
        ax, ay, az, b1, b2, jx, jy, jsw = sample
        s.raw, s.samples = sample, s.samples + 1
        if s.base is None:  # calibration: the first second, nothing fires; the buttons' readings are remembered as their starting state
            s.calib.append((ax, ay, az))
            for name, raw in (("btn1", bool(b1)), ("btn2", bool(b2)), ("joy_click", bool(jsw)), ("joy_up", jy > JOY_UP), ("joy_down", jy < JOY_DOWN)):
                s.level[name] = raw
                s.stable[name] = [raw, 0]
            if len(s.calib) >= CALIB_SAMPLES:
                n = len(s.calib)
                s.base = tuple(sum(c[i] for c in s.calib) / n for i in range(3))
                s.calib = []
                s._say("Ready!  Gestures are live. (baseline set)")
            s.prev = (ax, ay, az)
            return

        # joystick up / down (jump, drop) with hysteresis, then debounced like the buttons
        up_raw = jy > (JOY_UP - JOY_HYST if s.level.get("joy_up") else JOY_UP)
        dn_raw = jy < (JOY_DOWN + JOY_HYST if s.level.get("joy_down") else JOY_DOWN)
        s._button("joy_up", up_raw, "JUMP", need=1)
        s._button("joy_down", dn_raw, "DROP", need=1)
        s._button("btn1", bool(b1), "ABILITY 1")
        s._button("btn2", bool(b2), "ABILITY 2")
        s._button("joy_click", bool(jsw), "BOOST")

        # joystick left / right: a walk axis, and a swing-like pulse on each change (menus read it as left / right)
        lo = JOY_LEFT + (JOY_HYST if s.axis == -1 else 0)
        hi = JOY_RIGHT - (JOY_HYST if s.axis == 1 else 0)
        ax_raw = -1 if jx < lo else (1 if jx > hi else 0)
        if ax_raw != s.axis:
            s.axis = ax_raw
            if ax_raw: s.pulses["left" if ax_raw < 0 else "right"] = True

        # "held up" posture -> shield (sustained, with hysteresis so it does not flicker at the edge)
        tilt = (ay - s.base[1]) * SHIELD_SIGN
        pose = tilt >= (SHIELD_TILT * 0.6 if s.shield_on else SHIELD_TILT)
        if pose:
            if s.pose_since is None: s.pose_since = now
            if not s.shield_on and now - s.pose_since >= SHIELD_HOLD:
                s.shield_on = True
                s._say("SHIELD up (hold)")
        else:
            if s.shield_on: s._say("shield down")
            s.pose_since, s.shield_on = None, False

        # swings (attack) and shoves (interact) from the change since the last sample
        if s.prev is not None:
            dx, dy, dz = ax - s.prev[0], ay - s.prev[1], az - s.prev[2]
            mag = (dx * dx + dy * dy + dz * dz) ** 0.5
            if abs(dz) >= SHOVE_DELTA and abs(dz) >= max(abs(dx), abs(dy)) and now - s.last.get("shove", -9.0) >= GESTURE_COOLDOWN:
                s.last["shove"] = now
                s.pulses[INTERACT_CONTROL] = True
                s.shove_until = now + SHOVE_HOLD
                s._say("SHOVE! (interact)")
            elif mag >= SWING_DELTA and now - s.last.get("swing", -9.0) >= GESTURE_COOLDOWN and not s._reverse(dx, dy, now):
                if abs(dx) >= abs(dy): d = "right" if dx > 0 else "left"
                else: d = "up" if dy > 0 else "down"
                s.last["swing"], s.last["swing_vec"] = now, (dx, dy)
                s.pulses["attack"] = d
                s._say(f"SWING! ({d})")
        s.prev = (ax, ay, az)

        s.held = {n for n in BUTTON_CONTROLS if s.level.get(n)}
        if s.shield_on: s.held.add("shield")
        if now < s.shove_until: s.held.add(INTERACT_CONTROL)

    def _reverse(s, dx, dy, now):
        """True if this change undoes the last swing (the return jerk), shortly after it."""
        v = s.last.get("swing_vec")
        return bool(v) and now - s.last.get("swing", -9.0) < REVERSE_LOCKOUT and dx * v[0] + dy * v[1] < 0

    # ---------------------------------------------------------------- output
    def snapshot(s):
        """(held controls, pulses since the last snapshot). Pulses are cleared."""
        with s.lock:
            held, pulses = set(s.held), dict(s.pulses)
            s.pulses = {}
            return held, pulses, s.axis

    def drain_log(s):
        with s.lock:
            out, s.log = s.log, []
            return out


class PadReader(threading.Thread):
    """Reads the serial port on a background thread. Survives unplugging: it keeps retrying and reports each change once."""

    def __init__(s, port, state=None):
        super().__init__(daemon=True, name="pad-reader")
        s.port, s.state = port, state or PadState()
        s.connected, s.stop_flag, s.report = False, False, None

    def _report(self, msg):
        if PRINT_EVENTS: print(msg, flush=True)

    def run(s):
        import serial  # pyserial is imported here so the game still runs without it (keyboard only)
        while not s.stop_flag:
            try:
                with serial.Serial(s.port, BAUD, timeout=0.5) as ser:
                    s.connected = True
                    if s.report != "ok":
                        s.report = "ok"
                        s._report(f"Hand controller on {s.port}.  Calibrating... keep it level for about one second.")
                    while not s.stop_flag:
                        line = ser.readline()
                        if not line: continue
                        sample = parse_line(line)
                        if sample is None:
                            s.state.bad += 1
                            continue
                        s.state.feed(sample, time.monotonic())
                        for msg in s.state.drain_log(): s._report("  " + msg)
            except Exception as e:  # unplugged, busy, or a driver hiccup: wait and try again
                s.connected = False
                if s.report != "lost":
                    s.report = "lost"
                    s._report(f"Hand controller not responding on {s.port} ({e.__class__.__name__}). Retrying... (keyboard still works)")
                time.sleep(1.0)


class PadMotion(Motion):
    """Player 1 from the hand controller. The keyboard is still read too; the two are merged (either can move, jump, attack...)."""

    def __init__(s, i, reader):
        super().__init__(i)
        s.reader = reader
        s._menu = []

    def update(s, events, dt):
        super().update(events, dt)
        held, pulses, axis = s.reader.state.snapshot()
        h = lambda action: MAP[action] in held
        p = lambda action: MAP[action] in pulses
        if axis: s.axis = axis
        s.jump_h = s.jump_h or h("jump")
        s.down_h = s.down_h or h("down")
        s.block_h = s.block_h or h("block")
        s.interact_h = s.interact_h or h("interact")
        s.jump_p = s.jump_p or p("jump")
        s.down_p = s.down_p or p("down")
        s.dash_p = s.dash_p or p("boost")
        s.cast_p = s.cast_p or p("ability1")
        s.cast2_p = s.cast2_p or p("ability2")
        if p("slash"):
            s.slash_p = s.flick = True
            s.shake = min(1, s.shake + 0.15)
            direction = pulses.get(MAP["slash"])
            if isinstance(direction, str): s.swing = direction
        if "left" in pulses: s.swing = "left"
        if "right" in pulses: s.swing = "right"
        # menus: the stick moves the cursor, button 1 confirms (Esc on the keyboard still goes back)
        m = []
        if "joy_up" in pulses: m.append(pygame.K_UP)
        if "joy_down" in pulses: m.append(pygame.K_DOWN)
        if "left" in pulses: m.append(pygame.K_LEFT)
        if "right" in pulses: m.append(pygame.K_RIGHT)
        if "btn1" in pulses: m.append(pygame.K_RETURN)
        s._menu = m

    def menu_keys(s):
        return s._menu


def find_port():
    """The port to open, or None. Disabled with ROGUE_PAD=0. ROGUE_PAD_PORT overrides the default."""
    if os.environ.get("ROGUE_PAD") == "0": return None
    for c in [os.environ.get("ROGUE_PAD_PORT"), PORT] + sorted(glob.glob("/dev/cu.usbmodem*") + glob.glob("/dev/ttyACM*")):
        if c and os.path.exists(c): return c
    return None


def start(port=None):
    """Start the reader thread for the controller, or return None if there is no controller or pyserial is missing."""
    port = port or find_port()
    if not port: return None
    try:
        import serial  # noqa: F401
    except ImportError:
        print("Hand controller found, but pyserial is not installed (run: uv sync). Using the keyboard.", flush=True)
        return None
    reader = PadReader(port)
    reader.start()
    return reader


def monitor(port=None):
    """Terminal tool: print every raw sample and gesture so the thresholds can be tuned. Ctrl-C to stop."""
    port = port or find_port() or PORT
    print(f"Monitoring {port}. Hold the pad level, then move it. Ctrl-C to stop.", flush=True)
    reader = PadReader(port)
    reader.start()
    try:
        while True:
            time.sleep(0.25)
            st = reader.state
            with st.lock:
                raw, base, held, axis = st.raw, st.base, sorted(st.held), st.axis
            print(f"  connected={reader.connected} samples={st.samples} bad={st.bad} raw={raw} base={tuple(round(b) for b in base) if base else '-'} "
                  f"held={held} walk={axis:+d}", flush=True)
    except KeyboardInterrupt:
        print("stopped", flush=True)
