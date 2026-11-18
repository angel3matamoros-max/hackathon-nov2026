# Custom controller plan: Elegoo UNO + GY-521 (MPU-6050)

Status: **design only, not built yet.** The game is keyboard-only today. Everything the game needs from a controller is the
`Motion` object in [game/inputs.py](../game/inputs.py); the controller work later replaces only that file's backend.
`make_motions()` in the same file is the one place a new backend is registered. A test
(`tests/test_cutscenes_input.py::test_game_code_reads_only_motion_fields`) fails if gameplay code starts reading the keyboard directly,
so the seam stays clean.

## What the game reads from `Motion` (per player)

| Field | Kind | Used for | Gyro idea |
|---|---|---|---|
| `axis` (-1/0/1), `tilt` (-1..1) | held | walking, lock-pick mini-game | roll the controller left/right |
| `jump_h`, `down_h`, `block_h`, `interact_h` | held | jump height, fast-fall, block, loot | buttons |
| `jump_p`, `down_p`, `dash_p`, `cast_p`, `cast2_p`, `skip_p` | one-frame pulse | jump, drop, dash, skills, skip | buttons |
| `slash_p`, `flick` | one-frame pulse | **sword hit**, parry, mash | **swoosh gesture** |
| `swing` ("left"/"right"/"up"/"down"/None) | one-frame | slash-the-loot mini-game, menus, chest choice | direction of the swoosh |
| `shake` (0..1) | continuous | dice mini-game | shake energy |

## Hardware (Elegoo UNO R3 kit)

| GY-521 pin | UNO pin |
|---|---|
| VCC | 5V (the module has its own regulator) |
| GND | GND |
| SDA | A4 |
| SCL | A5 |
| AD0 | GND (I2C address 0x68) |

Kit push buttons: one pin each to D2..D7, other side to GND, use `INPUT_PULLUP`. Suggested mapping: D2 jump, D3 dash, D4 block (held), D5 skill 1, D6 skill 2, D7 loot / skip. The kit's joystick module can drive walking as an alternative to roll.

## Serial protocol (UNO to PC, USB, 115200 baud, ~100 Hz)

One ASCII line per sample, newline terminated: `ax,ay,az,gx,gy,gz,btns` where the six IMU values are the raw 16-bit MPU-6050 readings (accel +-2g = 16384 LSB/g, gyro +-500 deg/s = 65.5 LSB/deg/s) and `btns` is a bitmask of the six buttons (bit0 = D2 ... bit5 = D7). Example: `120,-340,16280,15,-22,3,5`.

Reference sketch outline (untested on hardware; written from the MPU-6050 datasheet register map):

```cpp
#include <Wire.h>
const int MPU = 0x68;
void setup() {
  Serial.begin(115200); Wire.begin();
  Wire.beginTransmission(MPU); Wire.write(0x6B); Wire.write(0); Wire.endTransmission(true);   // wake up
  Wire.beginTransmission(MPU); Wire.write(0x1B); Wire.write(0x08); Wire.endTransmission(true); // gyro +-500 deg/s
  for (int p = 2; p <= 7; p++) pinMode(p, INPUT_PULLUP);
}
void loop() {
  Wire.beginTransmission(MPU); Wire.write(0x3B); Wire.endTransmission(false);
  Wire.requestFrom(MPU, 14, true);
  int16_t ax = Wire.read() << 8 | Wire.read(), ay = Wire.read() << 8 | Wire.read(), az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read();                                                                    // temperature, ignored
  int16_t gx = Wire.read() << 8 | Wire.read(), gy = Wire.read() << 8 | Wire.read(), gz = Wire.read() << 8 | Wire.read();
  uint8_t b = 0; for (int p = 2; p <= 7; p++) b |= (!digitalRead(p)) << (p - 2);
  Serial.print(ax); Serial.print(','); Serial.print(ay); Serial.print(','); Serial.print(az); Serial.print(',');
  Serial.print(gx); Serial.print(','); Serial.print(gy); Serial.print(','); Serial.print(gz); Serial.print(','); Serial.println(b);
  delay(10);
}
```

## PC side (to build later)

1. `pyserial` reader thread pushes parsed samples into a lock-protected deque (never block the game loop).
2. `GyroMotion(Motion)` overrides `update()`: copies the newest sample into the `Motion` fields every frame and clears the pulse fields like `Motion.reset()` does.
3. Complementary filter (alpha ~0.98) fuses accel + gyro into roll; `axis = sign(roll)` past a dead zone of ~12 deg, `tilt = roll / 45` clamped.
4. **Swoosh detector**, written as a pure function `classify(window) -> gesture | None` so it can be unit tested from recorded CSV files:
   - angular speed `w = |gyro|` over the last ~120 ms; a swoosh is `w > ~250 deg/s` followed by a fall below ~80 deg/s, with a 300 ms refractory period;
   - direction from the dominant gyro axis and its sign: upward swoosh gives `swing="up"`, sideways gives left/right, downward chop gives `down`;
   - every detected swoosh sets `slash_p = flick = True` plus its `swing`; shake energy (rolling RMS of accel minus 1 g) feeds `shake`.
5. 1 s "hold still" calibration at start to measure the gyro bias.
6. The keyboard stays active as a fallback; P2 stays on the keyboard until a second controller exists. Register the backend in `make_motions("gy521")`.

## Test plan for the later stage

Record raw CSV of each gesture (10 reps each of up, down, left, right swoosh, idle, walking, shaking); assert `classify` finds >= 9/10 of the intended gestures and < 1 false trigger per minute of idle/walking data; replay a CSV through `GyroMotion` with a fake serial port in pytest.
