# Hand controller (ELEGOO MEGA 2560 + GY-521): how it works and how to tune it

Status: **built and reading from the real board** (the firmware sends 20 lines a second and every line parses). Gesture thresholds are
first guesses: tune them with `main.py --pad-monitor` (see below). The board has an accelerometer only (no gyro), so gestures use
accelerometer changes and posture, not rotation rate.

## Hardware (what the firmware expects)

| Part | Where |
|---|---|
| GY-521 (MPU-6050), I2C address 0x68 | Mega pins 20 (SDA) and 21 (SCL) |
| Button 1 | Mega pin 2, INPUT_PULLUP, reads 1 when pressed |
| Button 2 | Mega pin 3, INPUT_PULLUP, reads 1 when pressed |
| Stick click | Mega pin 4, INPUT_PULLUP, reads 1 when clicked |
| Joystick X / Y | analog A0 / A1, resting near 512 |

## Wire format

One newline-terminated CSV line about every 50 ms at 115200 baud over USB:

```
accelX,accelY,accelZ,b1,b2,jx,jy,jsw
```

Raw 16-bit accelerometer values, button bits 0/1, joystick 0..1023. [game/padbridge.py](../game/padbridge.py) `parse_line` rejects anything else (partial reads, wrong field count, out-of-range values); the reader counts them and carries on.

## What it does in the game

| Control | Game action (player 1) |
|---|---|
| Joystick left / right | walk |
| Joystick up | jump (press again for a double jump; hold for a higher jump) |
| Joystick down | drop through a platform |
| Stick click | dash (boost) |
| Button 1 | skill 1 |
| Button 2 | skill 2 |
| Swing (a quick jerk of the pad) | attack, in the direction of the swing |
| Hold the pad up (tilted toward vertical) | shield / block, while held |
| Shove (a sharp push along the board's Z axis) | interact (opening chests, looting), held for about 0.6 s |

In menus the stick moves the cursor, left/right change values, and button 1 confirms. Esc on the keyboard still goes back.

The keyboard keeps working alongside the pad, and player 2 is still on the keyboard (or the CPU in solo mode).

## How it is built (why it looks like this)

- A **reader thread** reads the port and turns each sample into held controls and one-frame pulses. Nothing is sent to the operating
  system as fake key presses, so it needs no macOS accessibility permission and cannot type into another window.
- The logic is a **pure state machine** (`PadState`), tested with recorded sample streams (`tests/test_padbridge.py`).
- `PadMotion` maps those pulses onto the same `Motion` fields the keyboard fills, so gameplay code is unchanged.
- Buttons and the stick click need **2 consecutive samples** to count (debounce). That is about 50 ms of added latency. Joystick up/down
  use hysteresis instead, so jumping is immediate.
- A **swing** is followed by a return jerk. Opposite-direction swings are ignored for 0.6 s after a swing, and swings have a 0.3 s cooldown.

## Start-up

1. The game finds the board: `/dev/cu.usbmodem1301`, or the first `/dev/cu.usbmodem*` or `/dev/ttyACM*`. Set `ROGUE_PAD_PORT` to pick another, or `ROGUE_PAD=0` to turn it off.
2. It prints `Hand controller on ... Calibrating... keep it level for about one second.`, then `Ready!`.
3. While you play it prints each gesture and press: `JUMP`, `BOOST`, `ABILITY 1`, `SWING! (left)`, `SHIELD up (hold)`, `SHOVE! (interact)`.
4. If the board is unplugged it prints one message and keeps retrying. The keyboard keeps working.

## Tuning (all in the CONFIGURATION block at the top of game/padbridge.py)

Run `.venv/bin/python main.py --pad-monitor` first. It prints the raw values and the held controls every quarter second.

| Setting | What it does | Tune it when... |
|---|---|---|
| `JOY_UP`, `JOY_DOWN` (800 / 200) | when a joystick push counts as jump / drop | jumping on its own, or not jumping |
| `JOY_LEFT`, `JOY_RIGHT` (250 / 750) | when a push counts as walking | walking drifts when the stick rests |
| `JOY_HYST` (60) | how far back a push must return before it releases | the same jump registers twice |
| `SWING_DELTA` (8000) | how much the accelerometer must change between two samples to count as a swing | swings do nothing, or walking shakes trigger attacks |
| `SHOVE_DELTA` (8000) | the same for the Z axis (shove) | shoves do nothing, or swings count as shoves |
| `SHIELD_TILT` (12000) | how far the pose must tilt from the start-up baseline | the shield comes on too easily or never |
| `SHIELD_SIGN` (-1) | which way "held up" moves accelY | holding up releases the shield; set it to +1 |
| `SHIELD_HOLD` (0.15 s) | how long the pose must last | the shield flickers |
| `DEBOUNCE_SAMPLES` (2) | samples a button must hold before it counts | presses feel late (1 = no debounce) or double up |
| `CALIB_SAMPLES` (20) | samples averaged for the level baseline | the baseline is off when you start |

The button and stick-click pins, and the joystick pins, are fixed by the firmware. The board is wired per the table above.

## Remapping

`MAP` in game/padbridge.py says which control drives which action. Controls: `joy_up`, `joy_down`, `joy_click`, `btn1`, `btn2`, `shield`,
`attack` (swing), `shove`. For example, to make button 1 the dash: `boost="btn1"`.

## Known limits

- No gyro, so there is no rotation-based gesture. Swing and shove detection work on acceleration changes only.
- Calibration assumes the pad is level for the first second. Start with it still.
- This was tested against the real board's data stream, but the gesture thresholds have not been tuned with a human hand yet.
- The GY-521 gesture set in the earlier plan (a 100 Hz gyro sketch) is replaced by this firmware. The firmware in use is the source of truth.

## PS2 controller (alternative to the accelerometer pad)

Firmware: [arduino_ps2/arduino_ps2.ino](../arduino_ps2/arduino_ps2.ino). Wiring: DATA = pin 12, CMD = 11, ATT = 10, CLK = 13, power **3.3V**, GND. It speaks the PS2 protocol by bit-banging, so the Mega's SPI pins are not needed, and it puts the pad in analog mode.

Wire format, about 50 lines a second at 115200 baud (the reader tells it apart from the other pad by the leading `P`):

```
P,b1,b2,rx,ry,lx,ly
```

`b1` bits (1 = pressed): SELECT, L3, R3, START, UP, RIGHT, DOWN, LEFT. `b2` bits: L2, R2, L1, R1, TRIANGLE, CIRCLE, CROSS, SQUARE. Sticks 0..255, centre 128 (`l*` left stick, `r*` right stick; the game uses the left).

Default mapping (`PS2_MAP`, `PS2_DEADZONE`, `PS2_MENU_OK`, `PS2_MENU_BACK` in game/padbridge.py):

| Control | Game action |
|---|---|
| Left stick / D-pad left, right | walk |
| Left stick / D-pad down | drop through a platform |
| Cross (X) | jump |
| Square | attack, aimed by the stick or D-pad |
| Circle | dash |
| L1 / R1 | skill 1 / skill 2 |
| L2 | block (held) |
| Triangle | interact (chests, loot; held) |
| Menus | stick / D-pad move, Start or X confirm, Select or Circle back |

To remap, change a right-hand side of `PS2_MAP`, e.g. `jump="CIRCLE"`. Names: UP DOWN LEFT RIGHT, CROSS CIRCLE SQUARE TRIANGLE, L1 R1 L2 R2, L3 R3, START SELECT. The game has no pause key, so Start only confirms in menus. The right stick is read but not used.
