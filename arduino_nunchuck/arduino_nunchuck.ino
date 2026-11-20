// Wii Nunchuck to Rogue Loot controller
// Connections:
//   Nunchuck SDA (pin 5) → Arduino pin 20
//   Nunchuck SCL (pin 2) → Arduino pin 21
//   Nunchuck VDD (pin 1) → Arduino 5V
//   Nunchuck GND (pin 6) → Arduino GND

#include <Wire.h>

#define NUNCHUK_ADDR 0x52

void setup() {
  Serial.begin(115200);  // Match the game's baud rate
  Wire.begin();

  // Initialize nunchuck
  Wire.beginTransmission(NUNCHUK_ADDR);
  Wire.write(0xF0);
  Wire.write(0x55);
  Wire.endTransmission();
  delay(1);

  Wire.beginTransmission(NUNCHUK_ADDR);
  Wire.write(0xFB);
  Wire.write(0x00);
  Wire.endTransmission();
  delay(100);
}

void loop() {
  // Request 6 bytes from nunchuck
  Wire.beginTransmission(NUNCHUK_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();

  Wire.requestFrom(NUNCHUK_ADDR, 6);

  byte data[6] = {0, 0, 0, 0, 0, 0};
  int bytesRead = 0;

  while (Wire.available() && bytesRead < 6) {
    data[bytesRead++] = Wire.read();
  }

  if (bytesRead == 6) {
    // Parse joystick values (0-255 range → scale to 0-1023)
    int joyX = data[0] << 2;  // 8-bit to 10-bit
    int joyY = data[1] << 2;

    // Parse accelerometer (10-bit)
    int accelX = (data[2] << 2) | ((data[5] >> 2) & 0x03);
    int accelY = (data[3] << 2) | ((data[5] >> 4) & 0x03);
    int accelZ = (data[4] << 2) | ((data[5] >> 6) & 0x03);

    // Convert to signed 16-bit (gyro format expected by padbridge)
    // Map 10-bit (0-1023) to 16-bit signed (-32768 to 32767)
    int16_t ax = (accelX - 512) << 6;
    int16_t ay = (accelY - 512) << 6;
    int16_t az = (accelZ - 512) << 6;

    // Parse buttons: 0=pressed, 1=released (invert for active-high)
    int buttonC = !(data[5] & 0x02);    // C button
    int buttonZ = !(data[5] & 0x01);    // Z button
    int joySwitch = 0;                   // nunchuck doesn't have a stick click

    // Send as CSV: accelX,accelY,accelZ,b1,b2,jx,jy,jsw
    // Map: C=b1, Z=b2, joystick stays as is
    Serial.print(ax);
    Serial.print(",");
    Serial.print(ay);
    Serial.print(",");
    Serial.print(az);
    Serial.print(",");
    Serial.print(buttonC);
    Serial.print(",");
    Serial.print(buttonZ);
    Serial.print(",");
    Serial.print(joyX);
    Serial.print(",");
    Serial.print(joyY);
    Serial.print(",");
    Serial.println(joySwitch);
  }

  delay(50);  // ~20 Hz, matches the game's expectation
}
