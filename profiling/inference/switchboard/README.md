# Switchboard: fleet power and marker selector

The switchboard selects exactly one device under test (DUT) at a time for PPK2
power profiling. It powers the selected board through the relay switch board and
routes that board's inference-marker pin through the mux into the PPK2 SIG line.
Switching is break-before-make, so two devices are never powered at once.

An Arduino Uno R3 runs the selector. The host sends short text commands over
serial, and the Arduino drives the relays and the mux.

## Files

- [HARDWARE.md](HARDWARE.md): wiring, relay trigger polarity, mux channel
  assignments, and the USB topology. Read this before flashing, because the
  sketch's `RELAY_ACTIVE_HIGH` and `MUX_ADDR_BITS` values must match the
  physical board.
- [firmware/switch_controller/](firmware/switch_controller/): the Arduino sketch.
  - `device_table.h`: the rig wiring stored as data. Add one row per device.
  - `switch_controller.ino`: the serial command loop that walks the table.

## Serial protocol

115200 baud, newline-terminated ASCII.

| Send | Reply | Meaning |
|---|---|---|
| `PING` | `PONG` | Liveness check before trusting any state. |
| `LIST` | `<name> <muxChannel> <bootMarginMs>` per line, then `OK` | Enumerate the device table. |
| `STATUS` | `<name>`, `<name> FLASH`, or `OFF` | Report the currently selected device. |
| `SEL <name>` | `OK <name>` or `ERR unknown <name>` | Break-before-make switch to one device. |
| `FLASH <name>` | `OK FLASH <name>` or `ERR no-jumper <name>` | Close the device's jumper relay so it runs on its own supply while being flashed. |
| `OFF` | `OK OFF` | De-energize every channel. |

Two details are easy to miss:

- `OK` from `SEL` means the electrical switch is complete, not that the device
  has finished booting. The host reads each device's `bootMarginMs` from `LIST`
  and waits that long itself.
- `FLASH` only works for boards that have a jumper relay in `device_table.h`.
  Boards with a normal supply pin return `ERR no-jumper`, because for them
  "flash mode" would mean running from the PPK2, which is the opposite of what
  the caller wants.

## Quick manual test

```
$ picocom -b 115200 /dev/ttyACM7     # or the Arduino IDE Serial Monitor
PING
> PONG
LIST
> pico2 7 400
> OK
SEL pico2
> OK pico2
STATUS
> pico2
OFF
> OK OFF
```

## Flashing the Arduino

### When to flash

Flash once. The firmware is persistent and survives power cycles, USB replugs,
and the DTR resets the pipeline performs. Reflash only after editing
`switch_controller.ino` or `device_table.h`, for example when wiring a new
device and adding its row. A normal measurement run never requires reflashing.

### Why the measurement desktop cannot compile

The measurement desktop is on a whitelisted network that reaches only
`github.com`, `raw.githubusercontent.com`, and `pypi.org`, and it has no sudo
access. `downloads.arduino.cc`, the PlatformIO registry, and the Ubuntu apt
mirrors are all blocked, so `arduino-cli` cannot be installed and the AVR
toolchain cannot be downloaded.

However, `avrdude` is already installed at `/usr/bin/avrdude`, and `avrdude`
only needs a prebuilt `.hex` file. It compiles nothing. The procedure below
therefore splits the work: compile the `.hex` on any internet-connected machine,
then flash it on the desktop.

This split is safe because the `.hex` is plain ATmega328P machine code and is
not tied to a particular computer. Any machine with `arduino-cli` and the AVR
core produces an identical file.

### Board details

| Item | Value |
|---|---|
| Board | Arduino Uno R3 (ATmega328P, signature `0x1e950f`) |
| USB serial number | `3433031333135121F161` |
| Desktop port | `/dev/ttyACM7`, via `/dev/serial/by-id/usb-Arduino__www.arduino.cc__0043_3433031333135121F161-if00` |
| Bootloader | 115200 baud, `avrdude` programmer `arduino` |

If the Arduino re-enumerates to a different `ttyACMn`, resolve the real path
from the by-id symlink above rather than assuming the number.

### Step 1: compile the .hex

Install the toolchain once. This example uses macOS; on Linux use the
`install.sh` script or your package manager.

```bash
brew install arduino-cli
arduino-cli core update-index
arduino-cli core install arduino:avr
```

Compile, writing the output to a known folder:

```bash
S=path/to/MicroGreen/profiling/inference/switchboard/firmware/switch_controller
arduino-cli compile --fqbn arduino:avr:uno --output-dir /tmp/ard_build "$S"
```

This produces two files. Use `switch_controller.ino.hex`, which contains the
application only. Do not flash `switch_controller.ino.with_bootloader.hex` over
serial, because it is meant for ISP programming and would overwrite the serial
bootloader.

### Step 2: copy the .hex to the desktop

```bash
scp /tmp/ard_build/switch_controller.ino.hex s4ai@10.56.252.43:/tmp/
```

### Step 3: flash with arduino

```bash
ssh s4ai@10.56.252.43
fuser -k /dev/ttyACM7 2>/dev/null; sleep 1    # release the port if held
avrdude -c arduino -p atmega328p -P /dev/ttyACM7 -b 115200 -D \
        -U flash:w:/tmp/switch_controller.ino.hex:i
```

A successful run prints a `flash verified` line followed by
`avrdude done. Thank you.` The `-D` flag skips the full chip erase, which
matches how the Arduino IDE drives the optiboot bootloader.

### Verify

A correctly flashed board answers `PING` with `PONG` within milliseconds:

```bash
~/power-measurement-pipeline/.venv/bin/python - <<'PY'
import time, serial
s = serial.Serial("/dev/ttyACM7", 115200, timeout=1)
time.sleep(2)                      # allow the DTR reset to settle
s.reset_input_buffer()
s.write(b"PING\n")
print("PING ->", s.readline().decode().strip())     # expect: PONG
s.write(b"LIST\n"); time.sleep(0.5)
print("LIST ->", s.read(200).decode().strip())      # expect: pico2 7 400 / OK
s.close()
PY
```

If `PING` hangs or returns nothing while the port still opens, the board is not
running the selector sketch. Reflash it.
