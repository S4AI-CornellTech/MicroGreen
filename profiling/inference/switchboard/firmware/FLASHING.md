# Flashing the Arduino selector

How to get `switch_controller.ino` onto the Arduino Uno that drives the MOSFET
switch board + mux. Read this together with [../HARDWARE.md](../HARDWARE.md).

## TL;DR

- You flash the firmware **once** as it is persistent, don't flash it per measurement.
  It survives power cycles, USB replugs, and the pipeline's DTR resets. You only
  reflash when you **edit the sketch** (e.g. add a row to `device_table.h`).
- **You cannot compile/flash on the measurement desktop directly** (see the
  constraint below). Instead: **compile the `.hex` on any internet-connected
  machine, copy it to the desktop, and flash with the desktop's `avrdude`.**

## Why not flash on the desktop directly?

The measurement desktop (`s4ai@10.56.252.43`) is on a **whitelisted network**:
only `github.com`, `raw.githubusercontent.com`, and `pypi.org` are reachable.
`downloads.arduino.cc`, PlatformIO's registry, `objects.githubusercontent.com`,
and the Ubuntu apt mirrors are all blocked, and there is **no sudo**. So:

- `arduino-cli` can't be installed there (binary download blocked), and even if
  it were, `arduino-cli core install arduino:avr` downloads the AVR toolchain
  from `downloads.arduino.cc` — also blocked.
- `apt install gcc-avr` / PlatformIO's `atmelavr` platform — both blocked.
- **But `avrdude` is already installed** on the desktop (`/usr/bin/avrdude`), and
  `avrdude` only needs a prebuilt `.hex`; it compiles nothing.

Hence the split: **compile elsewhere, flash on the desktop with `avrdude`.**

The `.hex` is plain ATmega328P machine code — it is **not tied to any particular
laptop**. Any machine with `arduino-cli` + the AVR core produces an identical
`.hex`, and any machine physically cabled to the Arduino can flash it. The Arduino
lives on the desktop, so the flash step always runs on the desktop.

## Board facts (this rig)

| | value |
|---|---|
| Board | Arduino Uno R3 (ATmega328P, signature `0x1e950f`) |
| USB serial number | `3433031333135121F161` |
| Desktop port | `/dev/ttyACM7` (via `/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_3433031333135121F161-if00`) |
| Bootloader baud | 115200, `avrdude` programmer `arduino` |
| Sketch on desktop | `~/microgreen/profiling/inference/switchboard/firmware/switch_controller/` |

> The `.hex` targets the ATmega328P; the USB serial only matters for *finding the
> port*. If the Arduino re-enumerates to a different `ttyACMn`, resolve the real
> path from the by-id symlink above (or `python -m serial.tools.list_ports -v`).

## Procedure

### 1. Compile the `.hex` (on any internet-connected machine)

Install the toolchain once (macOS example; on Linux use the `install.sh` script
or your package manager):

```bash
brew install arduino-cli          # or: curl -fsSL .../install.sh | sh
arduino-cli core update-index
arduino-cli core install arduino:avr
```

Compile, exporting the binaries to a known folder:

```bash
S=path/to/MicroGreen/profiling/inference/switchboard/firmware/switch_controller
arduino-cli compile --fqbn arduino:avr:uno --output-dir /tmp/ard_build "$S"
# -> /tmp/ard_build/switch_controller.ino.hex   (application only; use THIS one)
# -> /tmp/ard_build/switch_controller.ino.with_bootloader.hex  (do NOT use over serial)
```

Use `switch_controller.ino.hex` (application only). The `.with_bootloader.hex` is
for ISP programming and would overwrite the serial bootloader — don't flash it
via `avrdude -c arduino`.

### 2. Copy the `.hex` to the desktop

```bash
scp /tmp/ard_build/switch_controller.ino.hex s4ai@10.56.252.43:/tmp/
```

### 3. Flash with the desktop's `avrdude`

```bash
ssh s4ai@10.56.252.43
# free the port first in case the pipeline / a probe is holding it:
fuser -k /dev/ttyACM7 2>/dev/null; sleep 1
avrdude -c arduino -p atmega328p -P /dev/ttyACM7 -b 115200 -D \
        -U flash:w:/tmp/switch_controller.ino.hex:i
```

Expect `avrdude done. Thank you.` and a `flash verified` line. The `-D` (no full
chip-erase) matches how the Arduino IDE drives the optiboot bootloader.

## Verify it's running

Send `PING`; a correctly flashed board answers `PONG` in milliseconds. From the
desktop's Python env:

```bash
~/power-measurement-pipeline/.venv/bin/python - <<'PY'
import time, serial
s = serial.Serial("/dev/ttyACM7", 115200, timeout=1)
time.sleep(2)                      # DTR reset settle
s.reset_input_buffer()
s.write(b"PING\n")
print("PING ->", s.readline().decode().strip())     # expect: PONG
s.write(b"LIST\n"); time.sleep(0.5)
print("LIST ->", s.read(200).decode().strip())      # expect: pico2 7 400 / OK
s.close()
PY
```

If `PING` hangs or returns nothing, the board is **not** running the selector
sketch — reflash. (A hung read on an otherwise-openable port is the classic
symptom of the wrong/blank firmware.)

## When to reflash

Only after you **change the firmware** — editing `switch_controller.ino` or
`device_table.h` (e.g. wiring a new device and adding its row). Repeat steps 1–3.
Nothing about a normal measurement run requires reflashing.
