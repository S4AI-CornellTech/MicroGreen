# Wireless Power Test

A PlatformIO project for measuring BLE wireless data transimission rate and power consumption across multiple embedded platforms (Raspberry Pi Pico W, Pico 2W, Arduino Nano 33 BLE, ESP32).

---

## Prerequisites

- [PlatformIO](https://platformio.org/install/cli) installed
- A computer with Bluetooth support

### If PlatformIO is installed but not found in PATH

```bash
export PATH="$HOME/.platformio/penv/bin:$PATH"
```

To make this permanent (zsh):

```bash
echo 'export PATH="$HOME/.platformio/penv/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Project Setup

```bash
cd /PATH_TO_MICROGREEN/profiling/wireless
pio init
```

---

## Supported Platforms

| Environment | Board |
|---|---|
| `pico` | Raspberry Pi Pico W | 
| `pico2` | Raspberry Pi Pico 2W | 
| `tinypico` | TinyPICO ESP32 |
| `nano33ble` | Arduino Nano 33 BLE | 

---

## Selecting a Test Phase

Before compiling, open `src/main.cpp` and uncomment the phase you want to run. Only one phase should be active at a time.

```cpp
// powerTest.runPhase1_Idle();               // Phase 1: Baseline — wireless off, 30s idle
// powerTest.runPhase2_AntennaIdle(WirelessMode::BLE);  // Phase 2: BLE on, no data transfer
powerTest.runPhase3_DataTransmission(WirelessMode::BLE); // Phase 3: Active BLE data transmission
```

| Phase | Description |
|---|---|
| Phase 1 | Baseline idle — wireless completely off |
| Phase 2 | Antenna on and advertising, no data sent |
| Phase 3 | Maximum throughput BLE data transmission |

---

## Compiling & Flashing

```bash
pio run -e pico -t upload        # Pico W
pio run -e pico2 -t upload       # Pico 2W
pio run -e tinypico -t upload    # TinyPICO ESP32
pio run -e nano33ble -t upload   # Arduino Nano 33 BLE
```


---

## Monitoring Serial Output

After flashing, monitor the board over USB serial to see phase progress and statistics:

```bash
screen /dev/cu.usbmodem1101 115200
```

> The device path may vary. Run `ls /dev/cu.*` to find the correct port.

To exit `screen`: press `Ctrl+A` then `Ctrl+K`, then confirm with `y`.

---

## Running the BLE Monitor (Host Side)

Then run in the MicroGreen Python virtual environment:

```bash
python ble_connect.py
```

The script will scan for the device (`PicoNUS`, `Pico2NUS`, `NanoBLE`, `ESP32-NUS`, or `BTstack`), connect automatically, and print live throughput statistics.
