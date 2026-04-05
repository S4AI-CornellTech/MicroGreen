#include "WirelessTest.h"

#if PLATFORM_PICO
hci_con_handle_t WirelessTest::bleConnectionHandle = HCI_CON_HANDLE_INVALID;
bool WirelessTest::bleClientConnected = false;
WirelessTest *WirelessTest::bleInstance = nullptr;
btstack_packet_callback_registration_t WirelessTest::hci_event_callback_registration;

void WirelessTest::onCanSendNow()
{
    if (bleSendPending && isBLEClientConnected() && picoTxHandle != 0)
    {
        att_server_notify(bleConnectionHandle, picoTxHandle, 
                         (uint8_t*)pendingData, pendingLength);
        bleSendPending = false;
    }
}

// BLE packet handler for connection
static void ble_packet_handler(uint8_t packet_type, uint16_t channel, uint8_t *packet, uint16_t size)
{
    if (packet_type != HCI_EVENT_PACKET)
        return;

    switch (hci_event_packet_get_type(packet))
    {
    case HCI_EVENT_LE_META:
        switch (hci_event_le_meta_get_subevent_code(packet))
        {
        case HCI_SUBEVENT_LE_CONNECTION_COMPLETE:
        {
            WirelessTest::bleConnectionHandle = hci_subevent_le_connection_complete_get_connection_handle(packet);
            WirelessTest::bleClientConnected = true;
            Serial.println("BLE client connected");
            break;
        }
        }
        break;

    case HCI_EVENT_DISCONNECTION_COMPLETE:
        WirelessTest::bleConnectionHandle = HCI_CON_HANDLE_INVALID;
        WirelessTest::bleClientConnected = false;
        Serial.println("BLE client disconnected");
        break;

    case ATT_EVENT_CAN_SEND_NOW:         
        if (WirelessTest::bleInstance) {
            WirelessTest::bleInstance->onCanSendNow();
        }
        break;

    default:
        break;
    }
}
#endif

WirelessTest::WirelessTest()
{
    // device name based on board type
#if PLATFORM_NANO33BLE
    _deviceName = "Arduino Nano 33 BLE";
    dataService = nullptr;
    dataChar = nullptr;
    rxChar = nullptr;
    currentMode = WirelessMode::BLE; // Nano 33 BLE is always BLE
#elif PLATFORM_PICO
    _deviceName = "Raspberry Pi Pico W";
    // tcpConnected = false;
    bleInitialized = false;
    picoTxHandle = 0;
    picoRxHandle = 0;
    currentMode = WirelessMode::BLE; // Default to BLE
#elif PLATFORM_ESP32
    _deviceName = "TinyPICO ESP32";
    // tcpConnected = false;
    bleServer = nullptr;
    bleService = nullptr;
    bleCharacteristic = nullptr;
    bleRxCharacteristic = nullptr;
    bleClientConnected = false;
    currentMode = WirelessMode::BLE; // Default to BLE
#else
    _deviceName = "Unknown Device";
    currentMode = WirelessMode::BLE;
#endif
}

#if PLATFORM_NANO33BLE
void WirelessTest::cleanupService()
{
    if (dataService)
    {
        delete dataService;
        dataService = nullptr;
    }
    if (dataChar)
    {
        delete dataChar;
        dataChar = nullptr;
    }
    if (rxChar)
    {
        delete rxChar;
        rxChar = nullptr;
    }
}
#endif

void WirelessTest::printPhaseHeader(int phase, const char *description)
{
    Serial.print("Phase ");
    Serial.print(phase);
    Serial.print(": ");
    Serial.println(description);
}

void WirelessTest::printPhaseComplete(int phase, const char *summary)
{
    Serial.println();
    Serial.print("Phase ");
    Serial.print(phase);
    Serial.print(" complete");
    if (summary)
    {
        Serial.print(" - ");
        Serial.print(summary);
    }
    Serial.println();
    Serial.println();
}

void WirelessTest::runPhase1_Idle()
{
    Serial.println("=== PHASE 1: BASELINE ===");
    printPhaseHeader(1, "Idle state - 30 seconds (wireless off)");

    unsigned long startTime = millis();
    while (millis() - startTime < WirelessTestConstants::PHASE_DURATION_MS)
    {
        delay(1000);
        Serial.print(".");
    }
}

void WirelessTest::runPhase2_AntennaIdle(WirelessMode mode)
{
    currentMode = mode;

    // For Nano33BLE, always use BLE
#if PLATFORM_NANO33BLE
    if (mode == WirelessMode::WIFI)
    {
        Serial.println("WARNING: Nano 33 BLE only supports BLE mode. Using BLE instead.");
    }
    currentMode = WirelessMode::BLE;
#endif
    if (currentMode == WirelessMode::BLE)
    {
        printPhaseHeader(2, "Antenna idle - 30 seconds - BLE Mode");
    }
    else
    {
        printPhaseHeader(2, "Antenna idle - 30 seconds - WiFi Mode");
    }

    if (!initializeWireless())
    {
        Serial.println("Failed to initialize wireless!");
        return;
    }

    Serial.print(getWirelessType());

    unsigned long startTime = millis();
    unsigned long lastPrint = millis();
    while (millis() - startTime < WirelessTestConstants::PHASE_DURATION_MS)
    {
        maintainWireless();

        if (millis() - lastPrint >= 1000)
        {
            Serial.print(".");
            lastPrint = millis();
        }
        delay(10);
    }

    char summary[50];
    if (currentMode == WirelessMode::BLE)
    {
        snprintf(summary, sizeof(summary), "BLE antenna idle power measured");
    }
    else
    {
        snprintf(summary, sizeof(summary), "WiFi antenna idle power measured");
    }
    printPhaseComplete(2, summary);
}

void WirelessTest::runPhase3_DataTransmission(WirelessMode mode)
{
    currentMode = mode;

    // For Nano 33 BLE, always use BLE
#if PLATFORM_NANO33BLE
    if (mode == WirelessMode::WIFI)
    {
        Serial.println("WARNING: Nano 33 BLE only supports BLE mode. Using BLE instead.");
    }
    currentMode = WirelessMode::BLE;
#endif

    // Print mode-specific header
    Serial.println("=== PHASE 3: DATA TRANSMISSION ===");
    if (currentMode == WirelessMode::BLE)
    {
        printPhaseHeader(3, "Maximum BLE data transmission");
    }
    else
    {
        printPhaseHeader(3, "Maximum WiFi data transmission");
    }

    Serial.println("Initializing wireless for data transmission...");
    if (!initializeWireless())
    {
        Serial.println("Failed to initialize wireless!");
        printPhaseComplete(3, "FAILED - Wireless initialization failed");
        return;
    }

    Serial.print(getWirelessType());
    Serial.println(" initialized successfully");

    if (!waitForClientConnection())
    {
        Serial.println("No client connected - cannot perform data transmission test");
        printPhaseComplete(3, "FAILED - No client connection");
        return;
    }

    printConnectionStatus();

    size_t maxPacketSize;
    int transmissionInterval;
    if (currentMode == WirelessMode::BLE)
    {
        maxPacketSize = WirelessTestConstants::BLE_MAX_PACKET_SIZE;
        transmissionInterval = WirelessTestConstants::BLE_TRANSMISSION_INTERVAL_MS;
    }

    Serial.print("Packet size: ");
    Serial.print(maxPacketSize);
    Serial.println(" bytes");
    Serial.print("Transmission interval: ");
    Serial.print(transmissionInterval);
    Serial.println("ms");

    unsigned char *packetBuffer = new unsigned char[maxPacketSize];
    if (!packetBuffer)
    {
        Serial.println("Failed to allocate packet buffer!");
        printPhaseComplete(3, "FAILED - Memory allocation");
        return;
    }

    generateStaticPacket(packetBuffer, maxPacketSize, 0x55);

    delay(10);

    Serial.println("\n=== 30-SECOND DATA TRANSMISSION TEST STARTING ===");

    unsigned long phaseStartTime = millis();
    unsigned long lastTransmission = 0;
    unsigned long lastStatusPrint = millis();
    int packetCounter = 0;
    int successfulTransmissions = 0;
    int failedTransmissions = 0;

    // Main transmission loop - 30 seconds
    while (millis() - phaseStartTime < WirelessTestConstants::PHASE_DURATION_MS)
    {
        maintainWireless();

        if (!isClientConnected())
        {
            Serial.println("\nERROR: Client disconnected during transmission!");
            break;
        }

        if (millis() - lastTransmission >= (unsigned long)transmissionInterval)
        {
            bool success = sendDataPacket(packetBuffer, maxPacketSize);
            if (success)
            {
                successfulTransmissions++;
            }
            else
            {
                failedTransmissions++;
            }

            packetCounter++;
            lastTransmission = millis();
        }

        // Print status every 5 seconds during the test
        if (millis() - lastStatusPrint >= 5000)
        {
            unsigned long elapsed = millis() - phaseStartTime;
            float throughputKbps = (successfulTransmissions * maxPacketSize * 8.0) / elapsed;

            Serial.print("Test progress: ");
            Serial.print(elapsed / 1000);
            Serial.print("s - Packets: ");
            Serial.print(successfulTransmissions);
            Serial.print(" (");
            Serial.print(failedTransmissions);
            Serial.print(" failed) - Throughput: ");
            Serial.print(throughputKbps, 1);
            Serial.println(" kbps");

            lastStatusPrint = millis();
        }

        // delay(1);
        #if PLATFORM_PICO
        for (int i = 0; i < 5; i++) {
            BTstack.loop();
            delay(1);
        }
        #else
                delay(1);
        #endif
    }

    delete[] packetBuffer;

    // Calculate final stats
    unsigned long totalTestTime = millis() - phaseStartTime;
    float avgThroughputKbps = (successfulTransmissions * maxPacketSize * 8.0) / totalTestTime;

    Serial.println("=== STATISTICS ===");
    Serial.print("Test duration: ");
    Serial.print(totalTestTime / 1000.0, 1);
    Serial.println(" seconds");
    Serial.print("Total packets attempted: ");
    Serial.println(packetCounter);
    Serial.print("Successful transmissions: ");
    Serial.println(successfulTransmissions);
    Serial.print("Failed transmissions: ");
    Serial.println(failedTransmissions);
    Serial.print("Success rate: ");
    if (packetCounter > 0)
    {
        Serial.print((float)successfulTransmissions / packetCounter * 100.0, 1);
    }
    else
    {
        Serial.print("0.0");
    }
    Serial.println("%");
    Serial.print("Average throughput: ");
    Serial.print(avgThroughputKbps, 1);
    Serial.println(" kbps");
    Serial.print("Total data transmitted: ");
    Serial.print((successfulTransmissions * maxPacketSize) / 1024.0, 1);
    Serial.println(" KB");
    Serial.print("Transmission rate: ");
    Serial.print((float)successfulTransmissions / (totalTestTime / 1000.0), 1);
    Serial.println(" packets/second");

    char summary[100];
    snprintf(summary, sizeof(summary), "%.1f kbps avg, %lu packets, %.1f%% success",
             avgThroughputKbps, successfulTransmissions,
             packetCounter > 0 ? (float)successfulTransmissions / packetCounter * 100.0 : 0.0);

    printPhaseComplete(3, summary);
}

bool WirelessTest::initializeWireless()
{
    return initializeBLE();
}

bool WirelessTest::initializeBLE()
{
    Serial.println("Initializing BLE...");

#if PLATFORM_PICO
#if defined(ARDUINO_RASPBERRY_PI_PICO_2W) || defined(ARDUINO_ARCH_RP2350) || defined(PICO_RP2350)
    Serial.println("Setting up Pico 2W BLE...");
    const char *deviceName = "Pico2NUS";
    const char *readyMessage = "Pico2Ready";
#else
    Serial.println("Setting up Pico W BLE...");
    const char *deviceName = "PicoNUS";
    const char *readyMessage = "PicoReady";
#endif

    // Initialize BTstack
    BTstack.setup();
    Serial.println("BTstack setup complete");

    // Set up packet handler for connection tracking
    bleInstance = this;

    // Properly register the callback with BTstack
    hci_event_callback_registration.callback = &ble_packet_handler;
    hci_add_event_handler(&hci_event_callback_registration);
    Serial.println("BLE event handler registered");

    // Create Nordic UART Service UUIDs
    static UUID serviceUUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    static UUID txCharUUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E");
    static UUID rxCharUUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E");

    // Add the Nordic UART Service
    BTstack.addGATTService(&serviceUUID);
    Serial.println("Nordic UART Service added");

    // Add TX characteristic (for sending data to client)
    static uint8_t txBuffer[WirelessTestConstants::BLE_MAX_PACKET_SIZE + 3];
    strncpy((char *)txBuffer, readyMessage, sizeof(txBuffer) - 1);
    txBuffer[sizeof(txBuffer) - 1] = '\0';

    uint16_t txHandle = BTstack.addGATTCharacteristic(&txCharUUID,
                                                      ATT_PROPERTY_READ | ATT_PROPERTY_NOTIFY,
                                                      txBuffer, sizeof(txBuffer));
    Serial.print("TX Characteristic added (handle: 0x");
    Serial.print(txHandle, HEX);
    Serial.println(")");

    // Add RX characteristic (for receiving data from client)
    static uint8_t rxBuffer[WirelessTestConstants::BLE_MAX_PACKET_SIZE] = {0};
    uint16_t rxHandle = BTstack.addGATTCharacteristic(&rxCharUUID,
                                                      ATT_PROPERTY_WRITE_WITHOUT_RESPONSE,
                                                      rxBuffer, sizeof(rxBuffer));
    Serial.print("RX Characteristic added (handle: 0x");
    Serial.print(rxHandle, HEX);
    Serial.println(")");

    // Store the characteristic handles for later use
    picoTxHandle = txHandle;
    picoRxHandle = rxHandle;

    // Create advertisement data with device-specific name
    uint8_t adv_data[32];
    uint8_t nameLen = strlen(deviceName);
    uint8_t pos = 0;

    // Flags
    adv_data[pos++] = 0x02; // Length
    adv_data[pos++] = 0x01; // Type: Flags
    adv_data[pos++] = 0x06; // General discoverable, BR/EDR not supported

    // Complete Local Name
    adv_data[pos++] = nameLen + 1; // Length (name + type byte)
    adv_data[pos++] = 0x09;        // Type: Complete Local Name
    memcpy(&adv_data[pos], deviceName, nameLen);
    pos += nameLen;

    BTstack.setAdvData(pos, adv_data);
    BTstack.startAdvertising();
    Serial.print("BLE advertising started as: ");
    Serial.println(deviceName);

    // Give BLE stack time to initialize properly
    Serial.print("Initializing BLE stack");
    for (int i = 0; i < 30; i++)
    {
        BTstack.loop();
        delay(100);
        if (i % 10 == 0)
            Serial.print(".");
    }
    Serial.println(" Done!");

    // Set initialization flags
    bleInitialized = true;
    bleClientConnected = false;

    Serial.print("Pico BLE ready for connections as: ");
    Serial.println(deviceName);
    Serial.println("Service UUID: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    return true;

#elif PLATFORM_NANO33BLE
    // Nano 33 BLE Implementation using ArduinoBLE
    Serial.println("Setting up Nano 33 BLE...");

    if (!BLE.begin())
    {
        Serial.println("Failed to initialize BLE");
        return false;
    }
    Serial.println("BLE initialized");

    // Clean up any existing services
    cleanupService();

    // Create Nordic UART Service
    dataService = new BLEService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    if (!dataService)
    {
        Serial.println("Failed to create service");
        return false;
    }

    // Create TX characteristic (Nano TX -> Client RX)
    dataChar = new BLECharacteristic("6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
                                     BLERead | BLENotify, WirelessTestConstants::BLE_MAX_PACKET_SIZE);
    if (!dataChar)
    {
        Serial.println("Failed to create TX characteristic");
        return false;
    }

    // Create RX characteristic (Client TX -> Nano RX)
    rxChar = new BLECharacteristic("6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
                                   BLEWrite | BLEWriteWithoutResponse, WirelessTestConstants::BLE_MAX_PACKET_SIZE);
    if (!rxChar)
    {
        Serial.println("Failed to create RX characteristic");
        return false;
    }

    // Add characteristics to service
    dataService->addCharacteristic(*dataChar);
    dataService->addCharacteristic(*rxChar);

    // Add service to BLE
    BLE.addService(*dataService);
    Serial.println("Nordic UART Service added");

    // Set device properties for better discoverability
    BLE.setLocalName("NanoBLE");
    BLE.setDeviceName("NanoBLE");
    BLE.setAdvertisedService(*dataService);

    // Set connection parameters for stable connection
    BLE.setConnectionInterval(6, 12); // 7.5ms to 15ms intervals

    // Set initial TX characteristic value
    dataChar->writeValue("NanoReady");

    // Clear any pending RX data
    if (rxChar && rxChar->written())
    {
        rxChar->value(); // Read and discard
    }

    // Start advertising
    BLE.advertise();
    Serial.println("BLE advertising started");

    return true;

#elif PLATFORM_ESP32
    // ESP32 Implementation using ESP32 BLE Arduino
    Serial.println("Setting up ESP32 BLE...");

    // Initialize BLE device
    BLEDevice::init("ESP32-NUS");
    Serial.println("BLE device initialized");

    // Create BLE Server
    bleServer = BLEDevice::createServer();
    if (!bleServer)
    {
        Serial.println("Failed to create BLE server");
        return false;
    }

    // Add connection callbacks for tracking client connections
    class MyServerCallbacks : public BLEServerCallbacks
    {
    private:
        WirelessTest *wirelessTest;

    public:
        MyServerCallbacks(WirelessTest *wt) : wirelessTest(wt) {}

        void onConnect(BLEServer *pServer)
        {
            wirelessTest->bleClientConnected = true;
            Serial.println("BLE client connected");
        }

        void onDisconnect(BLEServer *pServer)
        {
            wirelessTest->bleClientConnected = false;
            Serial.println("BLE client disconnected");
            // Restart advertising for next connection
            pServer->getAdvertising()->start();
        }
    };

    bleServer->setCallbacks(new MyServerCallbacks(this));
    Serial.println("Connection callbacks set");

    // Create Nordic UART Service
    bleService = bleServer->createService("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    if (!bleService)
    {
        Serial.println("Failed to create service");
        return false;
    }
    Serial.println("Nordic UART Service created");

    // Create TX characteristic (ESP32 TX -> Client RX) with notifications
    bleCharacteristic = bleService->createCharacteristic(
        "6E400003-B5A3-F393-E0A9-E50E24DCCA9E",
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
    if (!bleCharacteristic)
    {
        Serial.println("Failed to create TX characteristic");
        return false;
    }

    // Add notification descriptor
    BLE2902 *ble2902 = new BLE2902();
    ble2902->setNotifications(true);
    bleCharacteristic->addDescriptor(ble2902);
    Serial.println("TX characteristic with notification descriptor created");

    // Create RX characteristic (Client TX -> ESP32 RX)
    bleRxCharacteristic = bleService->createCharacteristic(
        "6E400002-B5A3-F393-E0A9-E50E24DCCA9E",
        BLECharacteristic::PROPERTY_WRITE | BLECharacteristic::PROPERTY_WRITE_NR);
    if (!bleRxCharacteristic)
    {
        Serial.println("Failed to create RX characteristic");
        return false;
    }
    Serial.println("RX characteristic created");

    // Set initial value for TX characteristic
    bleCharacteristic->setValue("ESP32Ready");

    // Start the service
    bleService->start();
    Serial.println("Service started");

    // Configure and start advertising
    BLEAdvertising *pAdvertising = bleServer->getAdvertising();
    if (pAdvertising)
    {
        pAdvertising->addServiceUUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
        pAdvertising->setScanResponse(true);
        pAdvertising->setMinPreferred(0x06); // Minimum connection interval
        pAdvertising->setMaxPreferred(0x12); // Maximum connection interval
        pAdvertising->start();
        Serial.println("BLE advertising started");
    }
    else
    {
        Serial.println("Failed to get advertising instance");
        return false;
    }

    bleClientConnected = false;
    Serial.println("ESP32 BLE ready for connections");
    Serial.println("Device Name: ESP32-NUS");
    Serial.println("Service UUID: 6E400001-B5A3-F393-E0A9-E50E24DCCA9E");
    return true;

#else
    Serial.println("ERROR: BLE not supported on this platform");
    return false;
#endif
}

const char *WirelessTest::getWirelessType() const
{
    if (currentMode == WirelessMode::BLE)
    {
#if PLATFORM_ESP32
        return "Bluetooth Low Energy (ESP32)";
#elif PLATFORM_PICO
        return "Bluetooth Low Energy (Pico W Arduino-BTstack)";
#elif PLATFORM_NANO33BLE
        return "Bluetooth Low Energy (Nano 33)";
#else
        return "Bluetooth Low Energy (Unknown)";
#endif
    }
    else
    {
#if PLATFORM_ESP32
        return "WiFi (ESP32)";
#elif PLATFORM_PICO
        return "WiFi (Pico W)";
#else
        return "WiFi (802.11)";
#endif
    }
}

void WirelessTest::maintainWireless()
{
#if PLATFORM_PICO
    if (currentMode == WirelessMode::BLE)
    {
        BTstack.loop();
    }
#endif
}

void WirelessTest::shutdownWireless()
{
    if (currentMode == WirelessMode::BLE)
    {
        shutdownBLE();
    }
}

void WirelessTest::shutdownBLE()
{
#if PLATFORM_PICO
    // BTstack shutdown using HCI power control
    Serial.println("Shutting down BLE");

    // Stop advertising first
    BTstack.stopAdvertising();
    hci_power_control(HCI_POWER_OFF);
    bleInitialized = false;
    Serial.println("BLE powered off completely");

#elif PLATFORM_NANO33BLE
    // Nano 33 BLE shutdown
    BLE.stopAdvertise();
    cleanupService();
    BLE.end();
    Serial.println("Nano 33 BLE turned off");

#elif PLATFORM_ESP32
    // ESP32 BLE shutdown
    if (bleServer)
    {
        bleServer->getAdvertising()->stop();
    }
    BLEDevice::deinit(false);
    bleServer = nullptr;
    bleService = nullptr;
    bleCharacteristic = nullptr;
    bleRxCharacteristic = nullptr;
    bleClientConnected = false;
    Serial.println("ESP32 BLE turned off");
#endif
    delay(50);
}

bool WirelessTest::sendDataPacket(const unsigned char *data, size_t length)
{
    return sendBLEDataPacket(data, length);
}

bool WirelessTest::isClientConnected()
{
    return isBLEClientConnected();
}

bool WirelessTest::isBLEClientConnected()
{
#if PLATFORM_NANO33BLE
    BLEDevice central = BLE.central();
    return (central && central.connected());

#elif PLATFORM_ESP32
    return bleClientConnected;

#elif PLATFORM_PICO
    return WirelessTest::bleClientConnected && (WirelessTest::bleConnectionHandle != HCI_CON_HANDLE_INVALID);

#else
    return false;
#endif
}

bool WirelessTest::sendBLEDataPacket(const unsigned char *data, size_t length)
{
#if PLATFORM_NANO33BLE
    if (dataChar && isBLEClientConnected())
    {
        dataChar->writeValue(data, length);
        return true;
    }
    return false;

#elif PLATFORM_ESP32
    if (bleCharacteristic && bleClientConnected)
    {
        bleCharacteristic->setValue((uint8_t *)data, length);
        bleCharacteristic->notify();
        return true;
    }
    return false;

#elif PLATFORM_PICO
    if (bleInitialized && isBLEClientConnected() && picoTxHandle != 0)
    {
        pendingData = data;
        pendingLength = length;
        bleSendPending = true;
        att_server_request_can_send_now_event(bleConnectionHandle);
        return true;  // request queued — not a failure
    }
    return false;

#else
    return false;
#endif
}

void WirelessTest::generateStaticPacket(unsigned char *buffer, size_t length, unsigned char pattern)
{
    // Fill buffer with alternating pattern (0x55 = 01010101)
    for (size_t i = 0; i < length; i++)
    {
        buffer[i] = pattern;
    }
}

bool WirelessTest::waitForClientConnection()
{
    Serial.print("Waiting for client connection");

    unsigned long lastPrint = millis();

#if !PLATFORM_NANO33BLE // Only compile WiFi code for non-Nano platforms
    unsigned long lastTcpAttempt = 0;
    const unsigned long TCP_RETRY_INTERVAL = 3000; // Try TCP connection every 3 seconds
#endif

    while (true)
    {
        maintainWireless();

#if !PLATFORM_NANO33BLE // Only compile WiFi code for non-Nano platforms
#endif

        if (isClientConnected())
        {
            Serial.println(" Connected!");
            return true;
        }

        // Print dots every second
        if (millis() - lastPrint >= 1000)
        {
            Serial.print(".");
            lastPrint = millis();
        }

        delay(100);
    }

    return false;
}

void WirelessTest::printConnectionStatus()
{
    if (currentMode == WirelessMode::BLE)
    {
        Serial.print("BLE Status: ");
        if (isBLEClientConnected())
        {
            Serial.println("Client connected");
#if PLATFORM_PICO
            Serial.print("Connection handle: 0x");
            Serial.println(bleConnectionHandle, HEX);
#endif
        }
        else
        {
            Serial.println("No client connected");
        }
    }
}