// PS2 controller -> Rogue Loot (player 1). Sends "P,b1,b2,rx,ry,lx,ly" (bits: 1 = pressed; sticks 0..255, centre 128) at ~50 Hz, 115200 baud.
// Wiring: DATA=12, CMD=11, ATT=10, CLK=13, power 3.3V, GND.
#define DAT 12
#define CMD 11
#define ATT 10
#define CLK 13

byte xfer(byte out) {
  byte in = 0;
  for (byte i = 0; i < 8; i++) {
    digitalWrite(CMD, (out >> i) & 1);
    digitalWrite(CLK, LOW); delayMicroseconds(10);
    in |= digitalRead(DAT) << i;
    digitalWrite(CLK, HIGH); delayMicroseconds(10);
  }
  delayMicroseconds(20);
  return in;
}

void txrx(const byte *o, byte *r, byte n) {
  digitalWrite(ATT, LOW); delayMicroseconds(20);
  for (byte i = 0; i < n; i++) r[i] = xfer(o[i]);
  digitalWrite(ATT, HIGH); delay(2);
}

void cfgAnalog() {
  byte r[9];
  const byte a[] = {1, 0x43, 0, 1, 0, 0, 0, 0, 0};                    txrx(a, r, 5);
  const byte b[] = {1, 0x44, 0, 1, 3, 0, 0, 0, 0};                    txrx(b, r, 9);
  const byte c[] = {1, 0x43, 0, 0, 0x5A, 0x5A, 0x5A, 0x5A, 0x5A};     txrx(c, r, 9);
}

void setup() {
  Serial.begin(115200);
  pinMode(CMD, OUTPUT); pinMode(ATT, OUTPUT); pinMode(CLK, OUTPUT); pinMode(DAT, INPUT_PULLUP);
  digitalWrite(ATT, HIGH); digitalWrite(CLK, HIGH); digitalWrite(CMD, HIGH);
  delay(500);
  for (byte k = 0; k < 3; k++) { cfgAnalog(); delay(50); }
}

void loop() {
  byte r[9];
  const byte q[] = {1, 0x42, 0, 0, 0, 0, 0, 0, 0};
  txrx(q, r, 9);
  if (r[2] != 0x5A) { cfgAnalog(); delay(100); return; }   // no controller (or it reset): configure again
  byte b1 = ~r[3], b2 = ~r[4];                              // the pad reports 0 for pressed; send 1 for pressed
  bool analog = (r[1] == 0x73);
  Serial.print("P,"); Serial.print(b1); Serial.print(","); Serial.print(b2);
  Serial.print(","); Serial.print(analog ? r[5] : 128); Serial.print(","); Serial.print(analog ? r[6] : 128);
  Serial.print(","); Serial.print(analog ? r[7] : 128); Serial.print(","); Serial.println(analog ? r[8] : 128);
  delay(20);
}
