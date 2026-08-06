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

> Relay wiring and mux channel are independent facts — the mux only routes the
> marker signal, so re-doing the power side never changes a mux channel (and
> vice versa). Keep them in separate columns when transcribing.

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

Free relay channels: **K1** (pin 3), **K2** (pin 4), **K3** (pin 5).
K6 remains unusable — no Arduino pin is wired to IN6.

| Device | Inference marker pin | Relay link | Mux link |
|---|---|---|---|
| esp32 | GPIO4 | TODO | TODO |
| stm32f411ve | PB0 | TODO | TODO |
| nrf52840 | D0 → P0.03 (+ GND→GND, VDD→VDD) | TODO | TODO |
| coral dev micro | J9/J10 | TODO | TODO |

Note the nRF52840 is the odd one out — it needs 3 wires (marker signal, GND
reference, VDD reference) rather than just a signal line into the mux. Worth
double-checking whether the mux channel input can tolerate that VDD tie or
whether it's only there to level-shift the marker signal; don't wire VDD into
the mux channel pin itself unless you've confirmed that's what it's for.

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
