// This file is just a table of wiring. The control logic in 
// switch_controller.ino uses this table.
//
// Fields
//   name          : token used in the SEL command (case-sensitive, no spaces)
//   mosfetPin     : Arduino digital pin wired to that device's MOSFET IN line
//   muxChannel    : mux channel (C#) carrying that device's inference marker
//                   into the PPK2 logic common line
//   bootMarginMs  : how long that particular device takes to boot up and be 
//                   ready to run inference after it gets power

#pragma once
#include <Arduino.h>

struct Device {
  const char* name;
  uint8_t     mosfetPin;
  uint8_t     muxChannel;
  uint16_t    bootMarginMs;
};

// CONFIRMED wiring
//   pico2:   Arduino ~9 -> MOSFET IN8 -> OUT1(+3V3/-GND); marker GP15  -> mux C7
//   pico:    Arduino  8 -> MOSFET IN7 -> OUT2(+3V3/-GND); marker GP15  -> mux C6
//   esp32:   Arduino ~5 -> MOSFET IN4 -> OUT5(+3V3/-GND); marker GPIO4 -> mux C3
//   esp32s3: Arduino  4 -> MOSFET IN3 -> OUT6(+3V3/-GND); marker GPIO4 -> mux C2
//   esp32c6: Arduino  3 -> MOSFET IN2 -> OUT7(+3V3/-GND); marker GPIO4 -> mux C1
static const Device DEVICES[] = {
  { "pico2",   9, 7, 400 },
  { "pico",    8, 6, 400 },   // Pico W — RP2040, marker GP15
  { "esp32",   5, 3, 500 },   // bootMargin 500ms — TUNE: ESP32 boot + TFLite init
  { "esp32s3", 4, 2, 500 },   // bootMargin 500ms — TUNE: ESP32-S3 boot + TFLite init
  { "esp32c6", 3, 1, 500 },   // bootMargin 500ms — TUNE: ESP32-C6 boot + TFLite init

  // TODO: fill in as each device is physically wired 
  //   MOSFET IN pin (Arduino pin) | mux channel (marker) | boot margin (ms)
  // { "stm32f411ve", 0, 0, 0 },   // marker PB0
  // { "nrf52840",    0, 0, 0 },   // marker P0.03; see HARDWARE.md re: VDD/GND tie
  // { "coralmicro",  0, 0, 6000 },// marker J9/J10; boots in seconds
};

static const uint8_t DEVICE_COUNT = sizeof(DEVICES) / sizeof(DEVICES[0]);
