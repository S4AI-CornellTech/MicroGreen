#ifndef WIRELESS_TEST_H
#define WIRELESS_TEST_H

#include <Arduino.h>
#include "../../include/config.h"

// Platform detection macros
#if defined(ARDUINO_NANO33BLE) || defined(ARDUINO_ARCH_NRF52840) || defined(TARGET_NANO33BLE)
    #define PLATFORM_NANO33BLE 1
#else
    #define PLATFORM_NANO33BLE 0
#endif

#if defined(ARDUINO_RASPBERRY_PI_PICO_W) || defined(ARDUINO_ARCH_RP2040) || defined(ARDUINO_ARCH_RP2350)
    #define PLATFORM_PICO 1
#else
    #define PLATFORM_PICO 0
#endif

#if defined(ESP32)
    #define PLATFORM_ESP32 1
#else
    #define PLATFORM_ESP32 0
#endif

// Platform-specific includes
#if PLATFORM_NANO33BLE
#include <ArduinoBLE.h>
#elif PLATFORM_PICO
// #include <WiFi.h>
#include <BTstackLib.h>
#include <ble/att_server.h>
#include <btstack_event.h>
#elif PLATFORM_ESP32
// #include <WiFi.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>
#endif

// Constants
namespace WirelessTestConstants
{
    constexpr int PHASE_DURATION_MS = 30000;
    constexpr int BLE_MAX_PACKET_SIZE = 244;  
    constexpr int BLE_TRANSMISSION_INTERVAL_MS = 33; // Found through trial and error
}

enum class WirelessMode
{
    WIFI,
    BLE
};

class WirelessTest
{
public:
    WirelessTest();
    ~WirelessTest() = default;

    void runPhase1_Idle();
    void runPhase2_AntennaIdle(WirelessMode mode);
    void runPhase3_DataTransmission(WirelessMode mode);
    void runPhase4_AntennaCycling();

    bool initializeWireless();
    void shutdownWireless();
    bool isClientConnected();
    bool sendDataPacket(const unsigned char *data, size_t length);

    const char *getWirelessType() const;
    const char *getDeviceName() const { return _deviceName; }

#if PLATFORM_PICO
    static hci_con_handle_t bleConnectionHandle;
    static bool bleClientConnected;
    static WirelessTest* bleInstance;
    static btstack_packet_callback_registration_t hci_event_callback_registration;
    void onCanSendNow();
#endif

private:
    void printPhaseHeader(int phase, const char *description);
    void printPhaseComplete(int phase, const char *summary = nullptr);
    void maintainWireless();

#if PLATFORM_NANO33BLE
    void cleanupService();  // Add missing cleanupService declaration
#endif

    bool initializeBLE();
    void shutdownBLE();
    bool sendBLEDataPacket(const unsigned char* data, size_t length);
    bool isBLEClientConnected();

    void generateStaticPacket(unsigned char* buffer, size_t length, unsigned char pattern = 0x55);
    bool waitForClientConnection();
    void printConnectionStatus();

    WirelessMode currentMode;
    const char *_deviceName;

#if PLATFORM_NANO33BLE
    BLEService *dataService;
    BLECharacteristic *dataChar;
    BLECharacteristic *rxChar;

#elif PLATFORM_PICO
   
    bool bleInitialized;
    uint16_t picoTxHandle;
    uint16_t picoRxHandle;


    bool bleSendPending;
    const unsigned char* pendingData;
    size_t pendingLength;

#elif PLATFORM_ESP32

    BLEServer *bleServer;
    BLEService *bleService;
    BLECharacteristic *bleCharacteristic;
    BLECharacteristic *bleRxCharacteristic;
    bool bleClientConnected;
#endif
};

#endif 