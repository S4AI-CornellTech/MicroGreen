#include <Arduino.h>
#include "config.h"
#include "WirelessTest.h"

WirelessTest powerTest;

void setup() {

    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, 0); 

    Serial.begin(115200);

    Serial.print("Device: ");
    Serial.println(powerTest.getDeviceName());
    Serial.println();
    // powerTest.runPhase1_Idle();
    // powerTest.runPhase2_AntennaIdle(WirelessMode::BLE);
    powerTest.runPhase3_DataTransmission(WirelessMode::BLE);

}

void loop() {
    digitalWrite(LED_BUILTIN, 1);
    delay(1000);
    digitalWrite(LED_BUILTIN, 0);
    delay(1000);
}
