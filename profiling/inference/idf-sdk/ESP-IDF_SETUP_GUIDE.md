# ESP-IDF Setup Guide: Install, Compile & Flash

A step-by-step guide for run inferences on ESP32, ESP32-C6, ESP32-S3

## Step 1 — Clone ESP-IDF

```bash
mkdir -p ~/esp
cd ~/esp
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf
git checkout v5.5
git submodule update --init --recursive
```

> **Note:** The `--recursive` flag is required to also clone submodules.

---

## Step 2 — Install Toolchains

Install the toolchain for your target chip(s). Common options:

```bash
# ESP32 (Xtensa)
./install.sh esp32

# ESP32-C6 (RISC-V)
./install.sh esp32c6

# ESP32-S3
./install.sh esp32s3

# Multiple chips at once
./install.sh esp32,esp32c6,esp32s3

```

> **Disk space:** Each toolchain requires ~500MB–1GB. Make sure you have enough free space before installing.

---

## Step 3 — Set Up the Environment

You must source the export script **every time you open a new terminal**:

```bash
. ~/esp/esp-idf/export.sh
```

To make this permanent, add it to your shell config:

```bash
# For zsh (default on macOS)
echo '. $HOME/esp/esp-idf/export.sh' >> ~/.zshrc

# For bash
echo '. $HOME/esp/esp-idf/export.sh' >> ~/.bashrc
```

Verify the setup:
```bash
idf.py --version
```

The code is developed under v5.5

---

## Step 4 — Set the Target Chip

Tell ESP-IDF which chip you're building for. This must be done **before building** and will generate a fresh `sdkconfig`.

```bash
# ESP32
idf.py set-target esp32

# ESP32-C6
idf.py set-target esp32c6

# ESP32-S3
idf.py set-target esp32s3
```

> **Important:** If you switch targets, always delete the old build and sdkconfig first:
> ```bash
> rm -rf build sdkconfig
> idf.py set-target <chip>
> ```
---

## Step 5 — Build the project

```bash
cd person_detection
idf.py build

cd vww  
idf.py build

cd micro_speech_small
idf.py build

cd micro_speech_large
idf.py build
```

A successful build will output something like:
```
Project build complete. To flash, run:
  idf.py flash
```
---

## Step 8 — Flash

### Find your serial port

**macOS:**
```bash
ls /dev/cu.*
# Typically: /dev/cu.usbmodem1101 or /dev/cu.SLAB_USBtoUART
```

**Linux:**
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Typically: /dev/ttyUSB0 or /dev/ttyACM0
```

**Linux permission fix** (if you get permission denied):
```bash
sudo usermod -aG dialout $USER
# Then log out and back in
```

### Flash the firmware

```bash
# Auto-detect port
idf.py flash

# Specify port explicitly
idf.py -p /dev/cu.usbmodem1101 flash

# Flash at a specific baud rate
idf.py -p /dev/cu.usbmodem1101 -b 460800 flash
```

---

## Step 9 — Monitor Serial Output

```bash
idf.py monitor

# With port specified
idf.py -p /dev/cu.usbmodem1101 monitor
```

To exit the monitor: press **Ctrl+]**

### Build, flash, and monitor in one command:
```bash
idf.py flash monitor
```

---

## Common Issues & Fixes

### Wrong chip error
```
This chip is ESP32-C6, not ESP32. Wrong chip argument?
```
**Fix:** Rebuild for the correct target:
```bash
rm -rf build sdkconfig
idf.py set-target esp32c6
idf.py build flash
```

### RISC-V compiler not found (ESP32-C6/C3/H2)
```
riscv32-esp-elf-gcc is not a full path and was not found in the PATH
```
**Fix:** Install the RISC-V toolchain:
```bash
cd ~/esp/esp-idf
./install.sh esp32c6
. ./export.sh
```

### No space left on device
```
OSError: [Errno 28] No space left on device
```
**Fix:** Free up disk space, then retry:
```bash
rm -rf ~/.espressif/dist/*   # Clear downloaded archives
brew cleanup                  # macOS only
./install.sh esp32c6
```

### kconfgen / sdkconfig error
```
AttributeError: 'NoneType' object has no attribute 'name'
```
**Fix:** Delete stale sdkconfig and rebuild:
```bash
rm -rf build sdkconfig
idf.py build
```

### Port not found or connection refused
- Check the USB cable (data cable, not charge-only)
- Try a different USB port
- Make sure no other application (Arduino IDE, CubeIDE) has the port open
- On Linux, check `sudo usermod -aG dialout $USER`
---

## Further Resources

- [ESP-IDF Programming Guide](https://docs.espressif.com/projects/esp-idf/en/latest/)
- [ESP-IDF GitHub](https://github.com/espressif/esp-idf)
- [Espressif Forum](https://esp32.com/)
