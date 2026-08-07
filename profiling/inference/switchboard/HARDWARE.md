# Relay Switch Board + Mux Controller — Wiring Reference & Implementation Notes

> Physical build notes for the fleet selector. The firmware in
> [firmware/switch_controller/](firmware/switch_controller/) encodes some of these
> facts (trigger polarity, mux width, device table) — keep the two in sync.
>
> **The MOSFET switch board was replaced with an 8-channel relay module.** §2 and
> the timing notes in §3 changed with it; the relay switches only the high side,
> where the MOSFET board switched both rails.

## 1. Confirmed wiring

### Power / measurement chain
| From | Pin | To | Pin |
|---|---|---|---|
| PPK2 | VOUT | Relay board | COM — **all** channels (the relay power bus) |
| PPK2 | GND | Shared DUT ground bus | (not through the relay) |
| PPK2 | D0 (logic port channel 0) | Analog/Digital mux | SIG (signal/common) |
| PPK2 | Logic port VCC | pico2 | 3V3 |
| PPK2 | Logic port GND | pico2 | GND |

Relay contact convention: each `K_n NO` goes to exactly one DUT power input
(3V3 / VSYS). **`NC` is left unconnected** on every channel.

### Control chain (Arduino Uno R3 = "Some MCU")
| From | Pin | To | Pin |
|---|---|---|---|
| Arduino | 5V | Relay board | VCC |
| Arduino | GND | Relay board | GND |
| Arduino | 3 | Relay board | IN1 |
| Arduino | 4 | Relay board | IN2 |
| Arduino | ~5 | Relay board | IN3 |
| Arduino | ~6 | Relay board | IN4 |
| Arduino | 7 | Relay board | IN5 |
| Arduino | 8 | Relay board | IN7 |
| Arduino | ~9 | Relay board | IN8 |
| Arduino | 12 / 11 / 10 | Mux | S0 / S1 / S2 |
| Arduino | 3V3 | Mux | VCC |
| Arduino | GND | Mux | GND |

> **IN6 is not wired** — no Arduino pin drives it, so relay K6 is unusable until a
> wire is added. Don't assign a device to K6.

### Per-device (confirmed only)
| Device | Inference marker pin | Relay link | Mux channel |
|---|---|---|---|
| pico2 | GP15 | Arduino ~9 → IN8 → `K8 NO` → pico2 3V3 | `C7` ← GP15 |
| pico (pico W) | GP15 | Arduino 8 → IN7 → `K7 NO` → pico 3V3 | `C0` ← GP15 |
| esp32c6 | GPIO4 | Arduino 7 → IN5 → `K5 NO` → esp32c6 3V3 | `C1` ← GPIO4 |
| esp32s3 | GPIO4 | Arduino ~6 → IN4 → `K4 NO` → esp32s3 3V3 | `C2` ← GPIO4 (**unverified**) |
| esp32 | GPIO4 | Arduino ~5 → IN3 → `K3 NO` → esp32 3V3 | `C3` ← GPIO4 |
| nrf52840 | **P0.03** | two relays across P22, see §1.1 | `C6` ← P0.03 |

> Relay wiring and mux channel are independent facts — the mux only routes the
> marker signal, so re-doing the power side never changes a mux channel (and
> vice versa). Keep them in separate columns when transcribing.

> **The marker pin is whatever the FIRMWARE drives, not what a wiring doc says.**
> This table claimed the STM32 marker was `PB0` for a long time; the firmware
> actually drove **PE6** (`MARKER_PIN`/`MARKER_GPIO_PORT` in `stm32/src/main.h`),
> and `GPIOB` appeared nowhere in that project. The wire sat on PB0, the marker
> read permanently idle, and the capture looked exactly like a board that had
> failed to boot — it cost a full debugging cycle. The nRF52840's `P0.03` was
> checked against `nrf52/src/main.cpp` (`MARKER_PORT`/`MARKER_BIT`) *before*
> wiring, and read 15 clean pulses first try. Check the firmware header before
> trusting any row in this column.

### 1.1 nrf52840 — two relays across the P22 current header

The nRF52840 DK has no supply pin to switch. Its MCU is fed through the P22
current-measurement header, so it needs two relays that must never close together:

| Relay | Arduino | Role | COM | NO |
|---|---|---|---|---|
| **K1** | 3 → IN1 | measure | PPK2 **VOUT** | P22 pin B (MCU side) |
| **K2** | 4 → IN2 | flash | P22 pin A (supply side) | P22 pin B |

Plus `P22 pin A → PPK2 VIN` and `PPK2 GND → board GND`. The physical P22 jumper
stays **off** — K2 is what re-makes it.

- `SEL nrf52840` closes K1: `pin A → VIN → shunt → VOUT → K1 → pin B`, and the
  PPK2 meters MCU current in **ampere mode** while the board runs on its own USB.
- `FLASH nrf52840` closes K2: pin A bridges to pin B, the MCU runs on the board
  supply, and J-Link can program it.
- Neither closed → P22 open → MCU unpowered. This is the rest state, which is why
  the board is dark until a mode is selected, and why flashing has to happen
  *after* the selector opens in `run_measurement()` — see `ARDUINO_FLASH_JUMPER`.

The interlock is structural: both paths call `powerOffAll()` first, so at most one
contact is ever made. **`pin A → VIN` is the wire to double-check** — without it
the ammeter has no input side and reads exactly `0.000 mA` while source mode still
works, a confusing pair of symptoms that cost a debugging cycle on the previous
board in this slot.

> **This slot previously held stm32f411ve** on identical wiring (JP2 instead of
> P22, marker PE6 instead of P0.03, ST-Link/OpenOCD instead of J-Link). It was
> swapped out because the desktop cannot build STM32 firmware — PlatformIO's
> registry is DNS-sinkholed by the network whitelist, so the `ststm32` platform
> cannot be installed and binaries had to be built on another machine and staged.
> `nordicnrf52` **is** installed, so the nRF52840 builds and flashes locally in
> ~5 s with no staging step. The STM32 rows already in `results_summary.csv` were
> taken on that earlier wiring.

> **The nRF52840 is the only board measured in ampere mode.** Its rows in
> `results_summary.csv` are MCU current through P22 with the rest of the board
> live on USB; every other board is source mode, measuring the whole 3V3 rail.
> Nothing in the summary CSV records which mode produced a row, so don't compare
> nrf52 (or the older stm32 rows) against pico/ESP energy figures without
> accounting for that.

**The ESP boards read ~0 mA unless their USB hub port is cut first.** Their
onboard LDO holds the 3V3 rail up from USB 5V, so the PPK2 sources nothing and
the capture looks like a dead board. Measured with USB still on: esp32s3
`0.000 mA`, esp32c6 `0.026 mA`. With hub port 1 cut, esp32c6 reads
`6.968 mA avg / 0.643 min / 41.538 max` with the marker toggling. The pipeline
handles this automatically — both are in `HUB_OFF_FOR_MEASURE` — but any
hand-run measurement must cut the port too. The picos differ here: they read
the same with USB on or off, so this trap is ESP-specific.

### Everything else — still open (TODO)
These need the same three links each, physically wired and then uncommented in
`firmware/switch_controller/device_table.h`:
`relay IN_x ↔ Arduino pin`, `relay K_x NO ↔ device 3V3`,
`mux C_y ↔ device inference-marker pin`.

**No relay channel is free.** K1/K2 are the nRF52840 pair (§1.1), K3/K4/K5 the
ESPs, K7/K8 the picos. K6 is the only one left and it is dead — no Arduino pin is
wired to IN6. To add another board, run a wire from a spare Arduino pin (pin 2 is
free) to IN6 and add it to `RELAY_IN_PINS`.

| Device | Inference marker pin | Relay link | Mux link |
|---|---|---|---|
| stm32f411ve | PE6 | was K1/K2; displaced by nrf52840 | was `C6` |
| coral dev micro | J9/J10 | TODO — needs K6 wired | TODO |

An earlier note here claimed the nRF52840 needed three wires into the mux (marker
signal, GND reference, VDD reference) and flagged the VDD tie as unconfirmed.
**That turned out not to be needed.** A single `P0.03 → mux C6` line reads 15
clean marker pulses, with only `PPK2 GND → board GND` and `P22 pin A → PPK2 VIN`
on the power side. Nothing is wired into a mux channel except the marker itself.

## 1.2 udev rules — required, and easy to lose

USB probes are `root root` by default on the measurement desktop, so a normal
user cannot open them and **every** tool fails identically with
`LIBUSB_ERROR_ACCESS`. This is a machine-level prerequisite that no amount of
software changes can work around, and it is invisible until something fails
confusingly — chasing it once already cost a debugging cycle on "why can't we
flash the STM32", where the answer had nothing to do with the flashing tool.

`/etc/udev/rules.d/99-microgreen-probes.rules`:

```
# ST-LINK/V2 (STM32F411E-DISCO). Without this, st-flash AND OpenOCD both fail.
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="3748", MODE="0660", GROUP="plugdev", TAG+="uaccess"
# ST-LINK/V2-1 and V3, for a swapped-in board later.
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374b", MODE="0660", GROUP="plugdev", TAG+="uaccess"
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="374f", MODE="0660", GROUP="plugdev", TAG+="uaccess"
# Nordic PPK2. Needed for `usbreset 1915:c00a` to recover it without a replug.
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="c00a", MODE="0660", GROUP="plugdev", TAG+="uaccess"
```

```bash
sudo cp 99-microgreen-probes.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
# then replug the device (or power-cycle its hub port) so it re-enumerates
```

The user must be in `plugdev`. Verify with `ls -l /dev/bus/usb/<bus>/<dev>` —
group should read `plugdev`, not `root`. Pico, J-Link and Coral already have
their own rules (`99-picotool.rules`, `99-jlink.rules`, `99-coral-micro.rules`),
which is exactly why those boards worked while the ST-Link and PPK2 did not.

**The PPK2 rule matters beyond flashing.** The PPK2 can wedge in continuous
streaming mode if a run dies without sending `AVERAGE_STOP`; it then floods the
port with binary samples and every reconnect dies on a UTF-8 decode error inside
`ppk2_api._read_metadata()`. It ignores commands in that state, so the only
recovery is a power cycle — `usbreset 1915:c00a` with this rule in place, or a
physical replug without it.

## 2. Relay board trigger polarity — CONFIRMED ACTIVE-LOW

From the board's input spec (SainSmart-style 8-channel module):

| IN pin voltage | State | Relay |
|---|---|---|
| 0V - 0.5V | LOW | **ON** (COM→NO closed) |
| 2.5V - 5V | HIGH | **OFF** (COM→NO open) |

`RELAY_ACTIVE_HIGH` is set to `0` in the sketch to match.

This is also the fail-safe direction. These modules have an onboard pull-up on
each IN line, so a pin's default (floating/disconnected) state reads HIGH.
Arduino pins are undefined for a brief window during power-up and during every
reset (including the DTR-triggered reset that happens each time pyserial opens
the port). Active-LOW makes that floating-HIGH default mean **OFF**. Active-HIGH
would make it mean **ON**, so every reset would briefly risk energizing all
channels at once.

The firmware follows from this directly:

```c
pinMode(relayPin, OUTPUT);
digitalWrite(relayPin, HIGH);   // OFF — done for every IN pin in setup(), first
...
// select one:
// all relay pins HIGH          // all OFF (powerOffAll)
digitalWrite(selected, LOW);    // selected relay ON
```

`relayWrite(pin, false)` emits HIGH and `relayWrite(pin, true)` emits LOW, so the
sketch reads in device terms while producing exactly the sequence above.

Re-verify after any reset-behavior change (e.g. if you add the DTR-suppression
cap mentioned below) since that changes what the "undefined window" looks like.

### Coil current
Relay coils draw real current (~70-90mA each) where MOSFET gates drew ~none. The
design only ever energizes one channel at a time, so ~90mA off the Uno's 5V pin
is within a USB-powered board's budget — but `powerOffAll()` must stay the only
path that touches multiple channels, and it only ever de-energizes. If the board
has a **JD-VCC / VCC jumper**, consider removing it and feeding JD-VCC from a
separate 5V supply so coil switching noise stays off the Arduino rail.

## 3. Watch-list for writing the code / structuring the project

### Electrical / hardware
- **Confirm mux part number** (CD74HC4067 = 16ch/4 address bits vs CD74HC4051 =
  8ch/3 address bits). This determines whether `S3` exists and needs driving low,
  or doesn't exist at all. Set `MUX_ADDR_BITS` accordingly. Don't guess from the
  SparkFun board name alone — check the actual silkscreen/datasheet.
- **EN pin on the mux**, if present: tie it permanently active on the board rather
  than driving it from Arduino. One less thing to sequence.
- **nRF52840's extra VDD/GND tie** — confirm purpose before wiring into the mux
  channel (see above).
- **High side only, GND common.** The relay switches 3V3 through `K_n NO`; GND
  stays connected to every device all the time. The old MOSFET board switched
  both rails. Two consequences to check: (a) an "off" device can still be
  back-powered through its marker line into the powered mux, or through its USB
  port if that's plugged in — confirm the rail actually reads 0V when
  de-selected; (b) leakage through those paths shows up in the PPK2 baseline.
- **Arduino reset glitch**: pyserial opening the port toggles DTR → Uno resets →
  brief pin-undefined window. If the active-LOW fail-safe isn't enough on its own,
  add the standard 10µF+ cap between RESET and GND (or use a DTR-disable jumper on
  boards that have one) to suppress the auto-reset.
- **Shared grounds**: with 8 devices + PPK2 + mux + Arduino all sharing GND through
  the switch board, verify there's no ground-loop noise affecting PPK2's current
  measurement, especially once >1 device's psu ripple is present on the rail even
  when "off."

### Timing / sequencing
- **Break-before-make**, always: power OFF current device → settle delay → repoint
  mux → settle delay → power ON new device. Never let two devices be powered
  simultaneously. (Implemented in `selectDevice()`.)
- **Per-device boot margin varies a lot** (RP2040: ms; Coral Dev Micro: seconds).
  Don't hardcode one global settle time — key it per device (`bootMarginMs`), and
  let the *caller* (Python side) wait it out rather than blocking the Arduino's
  serial responsiveness.
- **Mux settle vs relay settle are different timescales** — mux propagation is
  ~ns, only need a token delay; relay coil travel is ~5-10ms each way, and power
  rail discharge (especially anything with bulk caps on the DUT) can be tens to
  hundreds of ms. Don't apply the same delay constant to all of them.
  (`MUX_SETTLE_MS` vs `RELAY_MAKE_MS` vs `POWER_OFF_SETTLE_MS`.)
- **Relays are mechanical, so ON isn't instant.** `RELAY_MAKE_MS` (20ms) holds
  the ACK until the contact has closed and stopped bouncing — without it the
  Arduino would report "OK" while the DUT is still unpowered, and the Python
  side's `bootMarginMs` countdown would start early. If you see contact bounce
  on the PPK2 current trace at switch-on, raise it.

### Firmware / code structure
- Keep the **device table (name, relay pin, mux channel, boot margin) as one data
  structure**, separate from the control logic that walks it — see
  `device_table.h`. This is what makes the 7 remaining TODOs a one-line-per-device
  fix rather than a code change.
- Keep the **serial protocol dumb and explicit** (`SEL`, `OFF`, `STATUS`, `PING`,
  `LIST`) — no workload/OpenEvolve-specific logic in the sketch. The Arduino knows
  nothing about energy targets, accuracy floors, or MAP-Elites; it's purely a
  device-selector. Matches Phase 2's separation of agent logic from
  measurement/harness logic.
- **ACK on physical completion, not logical readiness.** The Arduino says "OK" the
  instant the electrical switch is done, not after the device has booted —
  boot-readiness belongs in the Python controller / per-device knowledge files.

### Software / serial integration
- **Distinguish the Arduino's own serial port from the DUT ports** exposed through
  the software-controllable USB hub. If enumerating `/dev/ttyUSB*` / `/dev/ttyACM*`
  programmatically, pin the Arduino to a fixed identifier (serial number, or a udev
  rule) so a hub re-enumeration event doesn't hand your controller the wrong port.
- **Handshake before trusting state.** On controller startup, send `PING` and
  expect `PONG` before any `SEL` — don't assume the Arduino resumed in a known
  state, especially if the previous run crashed mid-selection.
- **Explicit `OFF` on controller shutdown/exception**, not just at the end of a
  successful run — every abnormal exit path should de-energize the fleet.

### Reproducibility (Phase 2 artifact concerns)
- Version-control the device table itself (`device_table.h`) alongside the sketch —
  if this board's wiring is redone or copied to another rig, the *values* are what
  someone needs to reproduce the setup, not just the control flow.
- Document the jumper setting (active-high/low) as a physical build note (§2 above)
  next to the code — a hardware fact code alone can't capture, and exactly the kind
  of thing that silently breaks reproducibility if someone rebuilds from the repo
  without the physical context.
