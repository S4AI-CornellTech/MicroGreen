# nRF52840 Setup Guide: Install, Compile & Flash

A step-by-step guide for run inferences on on the Nordic nRF52840-DK board.

## Prerequisites
- [PlatformIO](https://platformio.org/install/cli) installed
- [J-Link drivers](https://www.segger.com/downloads/jlink/) installed
- nRF52840-DK board
- A USB data cable (not charge-only)

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
cd /PATH_TO_MICROGREEN/profiling/inference/nrf52
```

**2. Initialize PlatformIO**
```bash
pio init
```

**3. Clone the TFLite Micro submodule** (if not already present)
```bash
cd ../../..
git submodule add https://github.com/tensorflow/tflite-micro.git profiling/inference/nrf52/tflite-micro
cd profiling/inference/nrf52
```

**4. Generate the TFLite Micro library tree** (if not already present)
```bash
cd tflite-micro
python3 tensorflow/lite/micro/tools/project_generation/create_tflm_tree.py ../lib/tflm_tree
cd ..
```

---

## Build

Compile all environments:
```bash
pio run
```

Compile a specific environment:
```bash
pio run -e kws_large
```

Available environments: `kws_large`, `kws_small`, `person_detection`, `vww`

---

## Flash

Connect the nRF52840-DK via the **J-Link USB port** (top left on the board), then:
```bash
pio run -e kws_large -t upload
```

> **Note:** Make sure to use the J-Link port, not the nRF USB port. The board should show a green power LED when correctly connected.

---

## Monitor Serial Output
```bash
pio device monitor
```

Or flash and monitor in one step:
```bash
pio run -e kws_large -t upload && pio device monitor
```

Baud rate is set to `115200` in `platformio.ini`.

---

## Troubleshooting

**TFLite Micro headers not found**

Re-run the tree generation script:
```bash
cd tflite-micro
python3 tensorflow/lite/micro/tools/project_generation/create_tflm_tree.py ../lib/tflm_tree
```

**Board not detected**
- Confirm you are using the J-Link USB port (top left), not the nRF USB port
- Ensure your cable supports data transfer, not just charging
- Install or reinstall [J-Link drivers](https://www.segger.com/downloads/jlink/)
- Try plugging directly into your computer rather than through a hub or adapter
- Run `lsusb` or check System Report → USB to confirm the board appears as a SEGGER device

**PlatformIO not found**

Add PlatformIO to your PATH (see Prerequisites above).