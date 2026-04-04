# STM32F411E-DISCO Setup Guide: Install, Compile & Flash

A step-by-step guide for running inferences on the STM32F411E-DISCO board.

---

## Prerequisites

- [PlatformIO CLI](https://platformio.org/install/cli) installed
- STM32F411E-DISCO board
- A USB Mini **data** cable (not charge-only) for flashing via ST-Link
- A USB-to-TTL serial adapter for reading serial output
- `stlink` tools installed:

```bash
brew install stlink
st-info --probe   # verify your board is detected
```

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

**1. Navigate to the project directory**

```bash
cd /PATH_TO_MICROGREEN/profiling/inference/stm32
```

**2. Initialize PlatformIO**

```bash
pio init
```

---

## Build

Compile all environments:

```bash
pio run
```

Compile a specific environment:

```bash
pio run -e kws_small
```

Available environments: `kws_large`, `kws_small`, `person_detection`, `vww`

---

## Flash

Connect the STM32F411E-DISCO via the **ST-Link USB port**, then:

```bash
st-flash write .pio/build/kws_small/firmware.bin 0x8000000
```

A successful flash ends with: `Flash written and verified! jolly good!`

---

## Monitor Serial Output

### Wiring

Connect your USB-to-TTL adapter to the STM32 as follows:

| Adapter | STM32F411 Pin |
|---------|---------------|
| TX      | RX (PA3)      |
| RX      | TX (PA2)      |
| GND     | GND           |

> ⚠️ TX and RX cross over. Do **not** connect VCC unless your board needs external power.

### Find the serial port

Once the adapter is plugged in:

```bash
ls /dev/cu.*
# e.g. /dev/cu.usbserial-BG0102IT
```

### Open the monitor

```bash
screen /dev/cu.usbserial-XXXXXXXX 115200
```

Replace `XXXXXXXX` with your adapter's serial ID. Baud rate is set to `115200` in `platformio.ini`.

**To exit:** `Ctrl+A` then `K`, then `Y` to confirm.