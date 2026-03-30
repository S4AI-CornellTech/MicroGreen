# Coral Micro Inference Workloads

This guide walks through how to set up, build, and flash each inference workload onto the Coral Dev Board Micro.

---

## Workloads Overview

| Workload | Hardware | Example Code | Model |
|---|---|---|---|
| KWS-S | w/ TPU | `examples/classify_speech_arduino_kws` | `kws_arduino_og_edgetpu.tflite` |
| KWS-L | w/ TPU | `examples/classify_speech_MLPerfTiny_kws` | `kws_mlperftiny_og_edgetpu.tflite` |
| PPD-S | w/o TPU | `examples/tflm_person_detection_m7` | `person_detect_model.tflite` |
| PPD-L | w/ TPU | `examples/detect_person_vww` | `vww_96_int8_edgetpu.tflite` |
| MobileNetV2 | w/ TPU | `examples/detect_person_MobileNetV2_with_TPU` | `tf2_ssd_mobilenet_v2_coco17_ptq_edgetpu.tflite` |
| MobileNetV2 | w/o TPU | `examples/detect_person_MobileNetV2_without_TPU` | `tf2_ssd_mobilenet_v2_coco17_ptq.tflite` |
| YOLOv8 | w/ TPU | `examples/detect_person_YOLOv8_with_TPU` | `best_full_integer_quant_edgetpu.tflite` |
| YOLOv8 | w/o TPU | `examples/detect_person_YOLOv8_without_TPU` | `best_full_integer_quant.tflite` |

---

## Prerequisites

The Coral Dev Board Micro toolchain is only compatible with macOS and Linux. Windows is not supported.

Install CMake 3.30.5 before building:

```bash
pip install cmake==3.30.5
```

---

## Get the Code

1. Clone the `coralmicro` repository along with all submodules:

```bash
git clone -b microgreen --recurse-submodules -j8 git@github.com:S4AI-CornellTech/coralmicro.git
```
We recommend cloning the repository into ```path_to_microgreen/profiling/inference/```

2. Install the required tools:

```bash
cd coralmicro && bash setup.sh
```

---

## Build the Code

Run the build script from the repository root. This compiles everything into a folder called `build`:

```bash
bash build.sh
```

> You can specify a custom output path with `-b <path>`, but if you do, make sure to pass that same path every time you call `flashtool.py`.

---

## Flash a Workload

Each workload is built and flashed with two commands: `make` to compile the example, and `flashtool.py` to deploy it to the board. Run these from the repository root.

### KWS-S (w/ TPU)

```bash
make -C build/examples/classify_speech_arduino_kws
python3 scripts/flashtool.py -e classify_speech_arduino_kws
```

### KWS-L (w/ TPU)

```bash
make -C build/examples/classify_speech_MLPerfTiny_kws
python3 scripts/flashtool.py -e classify_speech_MLPerfTiny_kws
```

### PPD-S (w/o TPU)

```bash
make -C build/examples/tflm_person_detection_m7
python3 scripts/flashtool.py -e tflm_person_detection_m7
```

### PPD-L (w/ TPU)

```bash
make -C build/examples/detect_person_vww
python3 scripts/flashtool.py -e detect_person_vww
```

### MobileNetV2 — w/ TPU

```bash
make -C build/examples/detect_person_MobileNetV2_with_TPU
python3 scripts/flashtool.py -e detect_person_MobileNetV2_with_TPU
```

### MobileNetV2 — w/o TPU

```bash
make -C build/examples/detect_person_MobileNetV2_without_TPU
python3 scripts/flashtool.py -e detect_person_MobileNetV2_without_TPU
```

### YOLOv8 — w/ TPU

```bash
make -C build/examples/detect_person_YOLOv8_with_TPU
python3 scripts/flashtool.py -e detect_person_YOLOv8_with_TPU
```

### YOLOv8 — w/o TPU

```bash
make -C build/examples/detect_person_YOLOv8_without_TPU
python3 scripts/flashtool.py -e detect_person_YOLOv8_without_TPU
```

---

## Checking Output

You can monitor the board's serial output using `screen`:
 
```
screen /dev/cu.usbmodem2101 115200
```
 
The device name (e.g. `/dev/cu.usbmodem2101` on macOS, `/dev/ttyACM0` on Linux) may vary — run `ls /dev/cu.usbmodem*` or `ls /dev/ttyACM*` to find yours.
 
For a more reliable setup that captures output from boot, use a USB-to-TTL serial cable instead. See the [Coral Dev Board Micro serial console guide](https://gweb-coral-full.uc.r.appspot.com/docs/dev-board-micro/serial-console/#connect-with-linux) for wiring and setup instructions.
 
---

## Documentation

- [Get Started with the Dev Board Micro](https://coral.ai/docs/dev-board-micro/get-started/)