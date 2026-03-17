# Raspberry Pi Pico 1&2 Setup Guide

A step-by-step guide for run inferences on Raspberry Pi Pico (RP2040) and Raspberry Pi pico 2 (RP2350).

---

## 1. Install Pico SDK

```bash
# Clone the SDK
git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk
git submodule update --init

# Set the environment variable
export PICO_SDK_PATH=$(pwd)
```

To make this permanent, add to your `~/.zshrc`:
```bash
echo 'export PICO_SDK_PATH=/path/to/pico-sdk' >> ~/.zshrc
source ~/.zshrc
```

---

## 2. Install Pico Extras

```bash
git clone https://github.com/raspberrypi/pico-extras.git
export PICO_EXTRAS_PATH=$(pwd)/pico-extras
```

Add to `~/.zshrc` to persist:
```bash
echo 'export PICO_EXTRAS_PATH=/path/to/pico-extras' >> ~/.zshrc
source ~/.zshrc
```

---

## 5. Build the Project

[build_picos.sh](./build_picos.sh) will build all the examples for the pico and pico 2 in
`build_pico1/examples` and `build_pico2/examples`


The build output will be in:
```
build/build_pico1/examples/your_example/your_example.uf2
``` 
or 
```
build/build_pico1/examples/your_example/your_example.uf2
```

---

## 6. Flash the Board

### Step 1 — Enter bootloader mode
Hold the **BOOTSEL** button on the Pico, then plug in the USB cable. Release the button after plugging in.

The Pico will mount as a USB drive named **RP2040** or **RP2350**.

### Step 2 — Copy the .uf2 file
example code flashing person detection to RP2350
```bash
cp build/build_pico2/examples/person_detection/person_detection.uf2 /Volumes/RP2350/
```

The drive will automatically eject and the Pico will reboot into your program. **This ejection is normal and expected.**

---

## 7. Detect the Board

After flashing, verify the Pico is enumerated as a serial device:

```bash
ls /dev/cu.*
```

You should see something like:
```
/dev/cu.usbmodem101
```

If it does **not** appear:
- Wait 3–5 seconds and try again
- Unplug and replug the cable

---

## 8. Monitor Serial Output

```bash
screen /dev/cu.usbmodem101 115200
```

To exit `screen`: press `Ctrl+A` then `K`, confirm with `Y`.

### Tip: Open the monitor before flashing
To avoid missing early output, open the monitor first, then flash in a second terminal:

```bash
# Terminal 1
screen /dev/cu.usbmodem101 115200

# Terminal 2
cp micro_speech_small.uf2 /Volumes/RP2350/
```

---

## 9. Reset the Board

### Using the RUN button (recommended)
Connect the **RUN** pin with any of the **GND** pin using a jumper wire on the Pico board to reset and rerun the program from the beginning — no unplugging needed. Use this if:
- The screen is connected but not printing
- You want to re-trigger startup output
- The program appears to be stuck

### Using picotool
```bash
picotool reboot
```

Install picotool via Homebrew if not already installed:
```bash
brew install picotool
```

### Manual reset
Unplug and replug the USB cable (without holding BOOTSEL).

---