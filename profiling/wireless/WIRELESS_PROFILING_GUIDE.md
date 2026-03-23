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

| Environment | Board | Flash Command |
|---|---|---|
| `pico` | Raspberry Pi Pico W | `cp firmware.uf2 /Volumes/RPI-RP2` |
| `pico2` | Raspberry Pi Pico 2W | `cp firmware.uf2 /Volumes/RP2350` |
| `tinypico` | TinyPICO ESP32 | flashed via USB/serial |
| `nano33ble` | Arduino Nano 33 BLE | flashed via USB/serial |

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

### Compile

```bash
pio run -e pico        # Pico W
pio run -e pico2       # Pico 2W
pio run -e tinypico    # TinyPICO ESP32
pio run -e nano33ble   # Arduino Nano 33 BLE
```

### Flash (Pico / Pico 2W)

Put the board into bootloader mode by holding **BOOTSEL** while plugging in USB. The board will appear as a mass storage volume.

```bash
# Pico W
cp .pio/build/pico/firmware.uf2 /Volumes/RPI-RP2

# Pico 2W
cp .pio/build/pico2/firmware.uf2 /Volumes/RP2350
```

The board will reboot automatically after flashing. The mass storage volume will disappear — this is expected.

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

### Expected output

```
BLE Connection Monitor
Scanning for target devices...
Found device: Pico2NUS at ...
Connecting to Pico2NUS
Connected in 1.27 seconds
Monitoring data transfer...
[14:43:49] Rate: 4048 B/s, 16.6 msg/s, Total: 50 msgs, 12200 bytes
...
=== SESSION SUMMARY ===
Duration: 30.33 seconds
Average data rate: 6958.68 bytes/second (55.7 kbps)
```

---

## Troubleshooting

**Board not appearing after flash**
The Pico reboots into firmware mode after flashing — the `RPI-RP2` / `RP2350` volume disappearing is normal. Check for `/dev/cu.usbmodem*` instead.

**`cp: Operation not permitted` when copying `.uf2`**
Grant your terminal Full Disk Access in **System Settings → Privacy & Security → Full Disk Access**, or use `sudo cp`.

**BLE device not found by Python script**
Ensure Bluetooth is enabled on your computer. The script scans for 5 seconds — if the board hasn't finished booting, it will retry automatically.