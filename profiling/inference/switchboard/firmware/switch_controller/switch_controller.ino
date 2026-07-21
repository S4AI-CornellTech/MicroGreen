// switch_controller.ino — Arduino Uno R3 fleet power/marker selector.
//
// Purpose: pick exactly one DUT at a time by (a) powering it through the MOSFET
// switch board and (b) routing its inference-marker pin through the mux into the
// PPK2 SIG line. Enforces break-before-make so two devices are never powered at
// once.
//
// This sketch is measurement-harness infrastructure ONLY. It knows nothing about
// workloads, energy targets, accuracy floors, or MAP-Elites/OpenEvolve. It ACKs
// when the electrical switch is done, NOT when a device has booted; boot-
// readiness lives in the Python controller / per-device knowledge files.
//
// Serial protocol (115200 baud, newline-terminated, ASCII):
//   PING            -> PONG
//   LIST            -> one line per device: "<name> <muxChannel> <bootMarginMs>",
//                      then "OK"
//   STATUS          -> "<name>" if a device is selected, else "OFF"
//   SEL <name>      -> break-before-make switch; "OK <name>" or "ERR unknown <name>"
//   OFF             -> de-energize all channels; "OK OFF"
//   (anything else) -> "ERR bad-command"
//
// See HARDWARE.md for wiring, the mux part-number question, and — critically —
// the MOSFET jumper polarity that MOSFET_ACTIVE_HIGH below must match.

#include "device_table.h"

// ===== Build-time hardware facts — MUST match the physical rig ==============

// MOSFET board jumper polarity. 0 = active-LOW 
#define MOSFET_ACTIVE_HIGH 0

// Mux address width: 4 for CD74HC4067 (16ch), 3 for CD74HC4051 (8ch).
// CONFIRM the part from the silkscreen/datasheet, not the board name.
#define MUX_ADDR_BITS 4

// Arduino pins driving mux address lines S0..S3. Only the first MUX_ADDR_BITS
// are used. TODO: transcribe from HARDWARE.md once these are physically wired.
// (Tie the mux EN pin active on the board — do not sequence it from here.)
static const uint8_t MUX_ADDR_PINS[4] = { 2, 3, 4, 5 };

// Settle times — deliberately two different timescales (see HARDWARE.md):
//   power-off: rail discharge through DUT bulk caps, tens–hundreds of ms
//   mux:       propagation is ~ns, only a token debounce delay is needed
static const uint16_t POWER_OFF_SETTLE_MS = 150;
static const uint16_t MUX_SETTLE_MS       = 2;

// ===== State ================================================================

static int8_t g_current = -1;  // index into DEVICES, or -1 for "all off"

// ===== Low-level helpers ====================================================

// Drive one MOSFET IN line to the requested logical state, honoring polarity.
static inline void mosfetWrite(uint8_t pin, bool on) {
#if MOSFET_ACTIVE_HIGH
  digitalWrite(pin, on ? HIGH : LOW);
#else
  digitalWrite(pin, on ? LOW : HIGH);
#endif
}

// Force every known channel OFF. The fail-safe primitive; safe to call anytime.
static void powerOffAll() {
  for (uint8_t i = 0; i < DEVICE_COUNT; i++) {
    mosfetWrite(DEVICES[i].mosfetPin, false);
  }
  g_current = -1;
}

// Point the mux common at the given channel.
static void setMux(uint8_t channel) {
  for (uint8_t b = 0; b < MUX_ADDR_BITS; b++) {
    digitalWrite(MUX_ADDR_PINS[b], (channel >> b) & 0x1);
  }
}

// Break-before-make: OFF current -> settle -> repoint mux -> settle -> ON new.
static void selectDevice(int8_t idx) {
  powerOffAll();                     // never two devices powered at once
  delay(POWER_OFF_SETTLE_MS);        // let the old rail discharge
  setMux(DEVICES[idx].muxChannel);   // repoint marker into PPK2 SIG
  delay(MUX_SETTLE_MS);
  mosfetWrite(DEVICES[idx].mosfetPin, true);
  g_current = idx;
}

static int8_t findDevice(const char* name) {
  for (uint8_t i = 0; i < DEVICE_COUNT; i++) {
    if (strcmp(DEVICES[i].name, name) == 0) return (int8_t)i;
  }
  return -1;
}

// ===== Serial command handling ==============================================

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
    Serial.println(g_current < 0 ? "OFF" : DEVICES[g_current].name);

  } else if (strcmp(line, "SEL") == 0) {
    if (!arg) { Serial.println("ERR missing-arg"); return; }
    int8_t idx = findDevice(arg);
    if (idx < 0) { Serial.print("ERR unknown "); Serial.println(arg); return; }
    selectDevice(idx);               // ACKs on physical completion, below
    Serial.print("OK ");
    Serial.println(DEVICES[idx].name);

  } else if (strcmp(line, "OFF") == 0) {
    powerOffAll();
    Serial.println("OK OFF");

  } else if (line[0] != '\0') {
    Serial.println("ERR bad-command");
  }
}

// ===== Arduino entry points =================================================

void setup() {
  // Drive everything to the fail-safe OFF state BEFORE anything else, so we
  // don't energize the fleet during the pin-undefined window (see HARDWARE.md).
  for (uint8_t i = 0; i < DEVICE_COUNT; i++) {
    pinMode(DEVICES[i].mosfetPin, OUTPUT);
    mosfetWrite(DEVICES[i].mosfetPin, false);
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
    if (c == '\r') continue;
    if (c == '\n') {
      buf[len] = '\0';
      handleLine(buf);
      len = 0;
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = c;
    } else {
      len = 0;            // overflow: drop the runaway line, resync on next \n
    }
  }
}
