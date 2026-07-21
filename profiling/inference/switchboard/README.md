# Switchboard — fleet power/marker selector

Selects exactly one DUT at a time for PPK2 power profiling: powers it through the
MOSFET switch board and routes its inference-marker pin through the mux into the
PPK2 SIG line. Enforces break-before-make so two devices are never powered at once.

- [HARDWARE.md](HARDWARE.md) — wiring, jumper polarity, mux part-number question,
  and the reproducibility notes. **Read this before flashing** — the sketch's
  `MOSFET_ACTIVE_HIGH` and `MUX_ADDR_BITS` must match the physical board.
- [firmware/switch_controller/](firmware/switch_controller/) — Arduino Uno R3 sketch.
  - `device_table.h` — the rig wiring, as data. Add devices here (one row each).
  - `switch_controller.ino` — the dumb serial selector that walks the table.

## Flashing

```
arduino-cli compile --fqbn arduino:avr:uno firmware/switch_controller
arduino-cli upload  --fqbn arduino:avr:uno -p /dev/ttyACM0 firmware/switch_controller
```
(or open `switch_controller.ino` in the Arduino IDE and upload to the Uno.)

## Serial protocol (115200 baud, newline-terminated)

| Send | Reply | Meaning |
|---|---|---|
| `PING` | `PONG` | liveness handshake before trusting state |
| `LIST` | `<name> <muxCh> <bootMs>` per line, then `OK` | enumerate the device table |
| `STATUS` | `<name>` or `OFF` | currently selected device |
| `SEL <name>` | `OK <name>` or `ERR unknown <name>` | break-before-make switch |
| `OFF` | `OK OFF` | de-energize the whole fleet |

`OK` from `SEL` means the **electrical switch is done**, not that the device has
booted. The controller reads each device's `bootMarginMs` from `LIST` and waits
that out itself.

## Quick manual test

```
$ picocom -b 115200 /dev/ttyACM0     # or the Arduino IDE Serial Monitor
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
