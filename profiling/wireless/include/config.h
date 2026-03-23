#pragma once

#ifndef SERIAL_BAUD
#define SERIAL_BAUD 115200
#endif

#ifndef DEVICE_NAME
#define DEVICE_NAME "Device"
#endif

// Board LED definitions
#if defined(ARDUINO_NANO33BLE) || defined(ARDUINO_ARCH_NRF52840) || defined(TARGET_NANO33BLE)
    #ifndef LED_BUILTIN
    #define LED_BUILTIN LEDB  // Use blue LED on Nano 33 BLE
    #endif
#elif defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_ARCH_RP2040) || defined(ARDUINO_ARCH_RP2350)
    #ifndef LED_BUILTIN
    #define LED_BUILTIN 25    // Pico W/2W onboard LED
    #endif
#elif defined(ESP32)
    #ifndef LED_BUILTIN
    #define LED_BUILTIN 22    // TinyPICO onboard LED
    #endif
#else
    #ifndef LED_BUILTIN
    #define LED_BUILTIN 25    // Fallback
    #endif
#endif
