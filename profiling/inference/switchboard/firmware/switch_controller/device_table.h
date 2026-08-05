// This file is just a table of wiring. The control logic in
// switch_controller.ino uses this table.
//
// Fields
//   name          : token used in the SEL command (case-sensitive, no spaces)
//   relayPin      : Arduino digital pin wired to that device's relay IN line
//   muxChannel    : mux channel (C#) carrying that device's inference marker
//                   into the PPK2 logic common line
//   bootMarginMs  : how long that particular device takes to boot up and be
//                   ready to run inference after it gets power

#pragma once
#include <Arduino.h>

struct Device {
  const char* name;
  uint8_t     relayPin;
  uint8_t     muxChannel;
  uint16_t    bootMarginMs;
};

// Relay board control lines (Arduino -> IN). IN_n drives relay K_n.
//   pin 3 -> IN1 -> K1      pin 6 -> IN4 -> K4      pin 9 -> IN8 -> K8
//   pin 4 -> IN2 -> K2      pin 7 -> IN5 -> K5
//   pin 5 -> IN3 -> K3      pin 8 -> IN7 -> K7
// IN6 / K6 has NO Arduino pin wired to it — that channel is unusable until a
// wire is added. Do not assign a device to K6.
//
// Every Arduino pin above, whether or not a device is assigned to it. The
// firmware drives all of these to OFF so a wired-but-unassigned relay is held
// released instead of floating. Keep in sync with the wiring, not with DEVICES.
static const uint8_t RELAY_IN_PINS[] = { 3, 4, 5, 6, 7, 8, 9 };
static const uint8_t RELAY_IN_COUNT  = sizeof(RELAY_IN_PINS) / sizeof(RELAY_IN_PINS[0]);

// Power path (relay module; only the high side is switched):
//   PPK2 VOUT -> every COM pin (the relay power bus)
//   K_n NO    -> exactly one DUT power input (3V3 / VSYS). NC left empty.
//   PPK2 GND  -> shared DUT ground bus, NOT through the relay.
//
// CONFIRMED wiring
//   pico2:  Arduino ~9 -> IN8 -> K8 NO -> pico2 3V3; marker GP15 -> mux C7
//   pico:   Arduino  8 -> IN7 -> K7 NO -> pico  3V3; marker GP15 -> mux C0
static const Device DEVICES[] = {
  { "pico2",   9, 7, 400 },   // Pico 2 — RP2350, marker GP15
  { "pico",    8, 0, 400 },   // Pico W — RP2040, marker GP15

  // NOT WIRED. Left out of the table on purpose: an entry here makes
  // `SEL <name>` answer "OK" and power nothing, which reads as a dead device
  // mid-run instead of an obvious wiring error. Uncomment one line only after
  // its relay output AND its mux channel are physically connected.
  //
  // Free relay channels: K1(pin 3) K2(pin 4) K3(pin 5) K4(pin 6) K5(pin 7).
  // { "esp32",       5, 3, 500 },  // marker GPIO4; bootMargin TUNE
  // { "esp32s3",     4, 2, 500 },  // marker GPIO4; bootMargin TUNE
  // { "esp32c6",     3, 1, 500 },  // marker GPIO4; bootMargin TUNE
  // { "stm32f411ve", 0, 0, 0 },    // marker PB0
  // { "nrf52840",    0, 0, 0 },    // marker P0.03; see HARDWARE.md re: VDD/GND tie
  // { "coralmicro",  0, 0, 6000 }, // marker J9/J10; boots in seconds
};

static const uint8_t DEVICE_COUNT = sizeof(DEVICES) / sizeof(DEVICES[0]);
