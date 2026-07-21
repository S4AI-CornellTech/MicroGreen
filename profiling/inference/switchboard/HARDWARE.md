# MOSFET Switch Board + Mux Controller — Wiring Reference & Implementation Notes

> Physical build notes for the fleet selector. The firmware in
> [firmware/switch_controller/](firmware/switch_controller/) encodes some of these
> facts (jumper polarity, mux width, device table) — keep the two in sync.

## 1. Confirmed wiring

### Power / measurement chain
| From | Pin | To | Pin |
|---|---|---|---|
| PPK2 | Vout | MOSFET switch board | Vin |
| PPK2 | GND | MOSFET switch board | GND |
| PPK2 | D0 (logic port channel 0) | Analog/Digital mux | SIG (signal/common) |
| PPK2 | Logic port VCC | pico2 | 3V3 |
| PPK2 | Logic port GND | pico2 | GND |

### Control chain (Arduino Uno R3 = "Some MCU")
| From | Pin | To | Pin |
|---|---|---|---|
| Arduino | 5V | MOSFET switch board | VCC |
| Arduino | GND | MOSFET switch board | GND |
| Arduino | ~9 | MOSFET switch board | IN8 |
| Arduino | 3V3 | Mux | VCC |
| Arduino | GND | Mux | GND |

> Mux address lines S0..S3 (and EN) are not yet in the confirmed table. The
> firmware currently assumes Arduino pins `{2,3,4,5}` for S0..S3 and EN tied
> active on-board — update both this table and `MUX_ADDR_PINS` once wired.

### Per-device (confirmed only)
| Device | Inference marker pin | MOSFET board | Mux channel |
|---|---|---|---|
| pico2 | GP15 | `OUT1-`→GND, `OUT1+`→3V3 (driven by Arduino IN8) | `C7` ← GP15 |

### Everything else — still open (TODO)
These need the same three links each, physically wired and then transcribed into
`firmware/switch_controller/device_table.h`:
`MOSFET board IN_x ↔ Arduino pin`, `MOSFET board OUT_x ↔ device power`,
`mux C_y ↔ device inference-marker pin`.

| Device | Inference marker pin | MOSFET link | Mux link |
|---|---|---|---|
| esp32 | GPIO4 | TODO | TODO |
| esp32s3 | GPIO4 | TODO | TODO |
| esp32c6 | GPIO4 | TODO | TODO |
| pico (pico W) | GP15 | TODO | TODO |
| stm32f411ve | PB0 | TODO | TODO |
| nrf52840 | D0 → P0.03 (+ GND→GND, VDD→VDD) | TODO | TODO |
| coral dev micro | J9/J10 | TODO | TODO |

Note the nRF52840 is the odd one out — it needs 3 wires (marker signal, GND
reference, VDD reference) rather than just a signal line into the mux. Worth
double-checking whether the mux channel input can tolerate that VDD tie or
whether it's only there to level-shift the marker signal; don't wire VDD into
the mux channel pin itself unless you've confirmed that's what it's for.

## 2. MOSFET board polarity — jumper decision

Since it's jumper-selectable, here's the reasoning for which way to set it:

**Recommend: ACTIVE-LOW** (IN pin pulled LOW turns the channel ON), if that's
what the jumper supports.

Reasoning: most relay/MOSFET modules ship with an onboard pull-up on each IN line
so the pin's default (floating/disconnected) state reads HIGH. Arduino pins are
undefined for a brief window during power-up and during every reset (including
the DTR-triggered reset that happens each time pyserial opens the port). If the
board is set active-LOW, that undefined-floating-HIGH default corresponds to
**OFF** — the fail-safe direction. If it's set active-HIGH, the same
floating-HIGH default corresponds to **ON**, meaning every reset briefly risks
energizing all channels at once.

Action either way:
- Set the jumper, then verify with a multimeter on one channel (don't trust silkscreen).
- Set `MOSFET_ACTIVE_HIGH` in the sketch to match (`0` = active-LOW).
- Re-verify after any reset-behavior change (e.g. if you add the DTR-suppression
  cap mentioned below) since that changes what "undefined window" even looks like.

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
- **Mux settle vs MOSFET settle are different timescales** — mux propagation is
  ~ns, only need a token delay; power rail discharge (especially anything with
  bulk caps on the DUT) can be tens to hundreds of ms. Don't apply the same delay
  constant to both without thinking about it. (`MUX_SETTLE_MS` vs
  `POWER_OFF_SETTLE_MS`.)

### Firmware / code structure
- Keep the **device table (name, MOSFET pin, mux channel, boot margin) as one data
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
