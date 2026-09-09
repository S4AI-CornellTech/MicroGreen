// switch_controller.ino 
//
// Pick exactly one DUT at a time by powering it through the relay
// board and connecting its inference-marker pin through the mux into the
// PPK2 SIG line
//
// Serial protocol (115200 baud, newline-terminated, ASCII):
//   PING            -> PONG
//   LIST            -> one line per device: "<name> <muxChannel> <bootMarginMs>",
//                      then "OK"
//   STATUS          -> "<name>" if a device is selected, else "OFF"
//   SEL <name>      -> break-before-make switch; "OK <name>" or "ERR unknown <name>"
//   FLASH <name>    -> close that device's jumper relay instead of its
//                      measurement relay, so it runs on its own supply while
//                      being flashed; "OK FLASH <name>" or "ERR no-jumper <name>"
//   OFF             -> de-energize all channels; "OK OFF"
//   (anything else) -> "ERR bad-command"

#include "device_table.h"

// Relay board trigger polarity: 0 = active-LOW
#define RELAY_ACTIVE_HIGH 0

// Mux address width (drives only S0-S2 from the Arduino, S3 pin is tied to GND)
#define MUX_ADDR_BITS 3

// Arduino pins driving the mux: S0=12, S1=11, S2=10.
static const uint8_t MUX_ADDR_PINS[4] = { 12, 11, 10, 0xFF };

static const uint16_t POWER_OFF_SETTLE_MS = 150; // waiting for rails to discharge
static const uint16_t RELAY_MAKE_MS       = 20; // contact close + bounce before ACK
static const uint16_t MUX_SETTLE_MS       = 2; // token deounce delay for the mux to settle

static int8_t g_current = -1;  // index of DEVICES, or -1 if "all off"
static bool   g_flashMode = false;  // true if g_current is held via FLASH, not SEL

// Drive one relay IN line to the requested logical state
static inline void relayWrite(uint8_t pin, bool on) {
#if RELAY_ACTIVE_HIGH
  digitalWrite(pin, on ? HIGH : LOW);
#else
  digitalWrite(pin, on ? LOW : HIGH);
#endif
}

// Force every wired channel off
static void powerOffAll() {
  for (uint8_t i = 0; i < RELAY_IN_COUNT; i++) {
    relayWrite(RELAY_IN_PINS[i], false);
  }
  g_current = -1;
  g_flashMode = false;
}

// Point the mux common at the given channel.
static void setMux(uint8_t channel) {
  for (uint8_t b = 0; b < MUX_ADDR_BITS; b++) {
    digitalWrite(MUX_ADDR_PINS[b], (channel >> b) & 0x1);
  }
}

// OFF current -> settle -> repoint mux -> settle -> ON new.
static void selectDevice(int8_t idx) {
  powerOffAll();                     // never two devices powered at once
  delay(POWER_OFF_SETTLE_MS);      // let the old contact open and the rail discharge
  setMux(DEVICES[idx].muxChannel);   // repoint marker into PPK2 SIG
  delay(MUX_SETTLE_MS);
  relayWrite(DEVICES[idx].relayPin, true);
  delay(RELAY_MAKE_MS);              // don't ACK until the contact has actually closed
  g_current = idx;
  g_flashMode = false;
}

// Close a device's jumper relay instead of its measurement relay, so the board
// runs on its own supply (e.g. STM32 JP2 re-made for ST-Link flashing). 
static void flashDevice(int8_t idx) {
  powerOffAll();
  delay(POWER_OFF_SETTLE_MS);
  relayWrite(DEVICES[idx].jumperPin, true);
  delay(RELAY_MAKE_MS);
  g_current = idx;
  g_flashMode = true;
}

static int8_t findDevice(const char* name) {
  for (uint8_t i = 0; i < DEVICE_COUNT; i++) {
    if (strcmp(DEVICES[i].name, name) == 0) return (int8_t)i;
  }
  return -1;
}

// Serial command handling 
static void handleLine(char* line) {
  // Split into command and (optional) argument on the first space.
  char* sp  = strchr(line, ' ');
  char* arg = nullptr;
  if (sp) { *sp = '\0'; arg = sp + 1; }

  if (strcmp(line, "PING") == 0) {
    Serial.println("PONG");

  } else if (strcmp(line, "LIST") == 0) {
    for (uint8_t i = 0; i < DEVICE_COUNT; i++) {
      Serial.print(DEVICES[i].name);   Serial.print(' ');
      Serial.print(DEVICES[i].muxChannel); Serial.print(' ');
      Serial.println(DEVICES[i].bootMarginMs);
    }
    Serial.println("OK");

  } else if (strcmp(line, "STATUS") == 0) {
    if (g_current < 0) {
      Serial.println("OFF");
    } else {
      Serial.print(DEVICES[g_current].name);
      Serial.println(g_flashMode ? " FLASH" : "");
    }

  } else if (strcmp(line, "SEL") == 0) {
    if (!arg) { Serial.println("ERR missing-arg"); return; }
    int8_t idx = findDevice(arg);
    if (idx < 0) { Serial.print("ERR unknown "); Serial.println(arg); return; }
    selectDevice(idx);               // ACKs on physical completion, below
    Serial.print("OK ");
    Serial.println(DEVICES[idx].name);

  } else if (strcmp(line, "FLASH") == 0) {
    if (!arg) { Serial.println("ERR missing-arg"); return; }
    int8_t idx = findDevice(arg);
    if (idx < 0) { Serial.print("ERR unknown "); Serial.println(arg); return; }
    if (DEVICES[idx].jumperPin == NO_PIN) {
      // Refuse rather than fall back to SEL: on a board with no jumper relay,
      // "flash mode" would silently mean "powered from the PPK2", which is the
      // opposite of what the caller asked for.
      Serial.print("ERR no-jumper "); Serial.println(arg); return;
    }
    flashDevice(idx);
    Serial.print("OK FLASH ");
    Serial.println(DEVICES[idx].name);

  } else if (strcmp(line, "OFF") == 0) {
    powerOffAll();
    Serial.println("OK OFF");

  } else if (line[0] != '\0') {
    Serial.println("ERR bad-command");
  }
}

// Arduino entry points
void setup() {
  for (uint8_t i = 0; i < RELAY_IN_COUNT; i++) {
    // Set the level before switching the pin to OUTPUT. On avg every port bit
    // is 0 at reset, so pinMode(OUTPUT) first would drive the IN line low
    relayWrite(RELAY_IN_PINS[i], false);
    pinMode(RELAY_IN_PINS[i], OUTPUT);
  }
  for (uint8_t b = 0; b < MUX_ADDR_BITS; b++) {
    pinMode(MUX_ADDR_PINS[b], OUTPUT);
    digitalWrite(MUX_ADDR_PINS[b], LOW);
  }
  g_current = -1;

  Serial.begin(115200);
  while (!Serial) { /* Uno: returns immediately; harmless elsewhere */ }
}

void loop() {
  static char buf[48];
  static uint8_t len = 0;

  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue; // ignore unexpected or misplaced return character
    if (c == '\n') { // new line
      buf[len] = '\0'; // end of the string marker
      handleLine(buf);
      len = 0;
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = c;
    } else {
      len = 0;            // overflow: drop the runaway line, resync on next \n
    }
  }
}
