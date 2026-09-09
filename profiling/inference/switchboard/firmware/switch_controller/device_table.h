// This file is just a table of wiring. The control logic in
// switch_controller.ino uses this table.
//
// Fields
//   name          : token used in the SEL command (case-sensitive, no spaces)
//   relayPin      : Arduino digital pin wired to the MEASUREMENT relay's IN
//                   line -- the one that puts PPK2 VOUT on the device's load
//   jumperPin     : Arduino digital pin wired to an optional SECOND relay that
//                   restores the board's own supply path so it can be flashed
//                   without the PPK2 (see the STM32 note below). NO_PIN if the
//                   board has no such jumper.
//   muxChannel    : mux channel (C#) carrying that device's inference marker
//                   into the PPK2 logic common line
//   bootMarginMs  : how long that particular device takes to boot up and be
//                   ready to run inference after it gets power

#pragma once
#include <Arduino.h>

#define NO_PIN 0xFF

struct Device {
  const char* name;
  uint8_t     relayPin;
  uint8_t     jumperPin;
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
//   PPK2 VOUT -> the COM pins of the MEASUREMENT relays (the power bus)
//   K_n NO    -> exactly one DUT power input (3V3 / VSYS). NC left empty.
//   PPK2 GND  -> shared DUT ground bus, NOT through the relay.
// EXCEPTION -- K2 (nrf52840 jumper relay). Its COM goes to P22 pin A, the 
// board's own supply side, which is also tied to PPK2 VIN. 

static const Device DEVICES[] = {
  { "pico2",       9, NO_PIN, 7, 400 },  // Pico 2 — RP2350, marker GP15
  { "pico",        8, NO_PIN, 0, 400 },  // Pico W — RP2040, marker GP15
  { "esp32c6",     7, NO_PIN, 1, 500 },  // marker GPIO4 -> mux C1; bootMargin TUNE
  { "esp32s3",     6, NO_PIN, 2, 500 },  // marker GPIO4 -> mux C2; bootMargin TUNE
  { "esp32",       5, NO_PIN, 3, 500 },  // marker GPIO4 -> mux C3; bootMargin TUNE
  { "nrf52840",    3, 4,      6, 500 },  // K1 measure / K2 flash across P22; marker P0.03 -> mux C6; bootMargin TUNE

  // NOT WIRED
  // { "stm32f411ve", 0, 0, 0, 500 },  // marker PE6; was on K1/K2 before nrf52840 took them
  // { "coralmicro",  0, 0, 0, 6000 }, // marker J9/J10; boots in seconds
};

static const uint8_t DEVICE_COUNT = sizeof(DEVICES) / sizeof(DEVICES[0]);
