# Inference Workload Profiling

This repository provides tools for profiling inference workloads across multiple MCU platforms, covering both runtime and power measurements. Each folder corresponds to a different MCU family.

## Repository Structure

| Folder | Platform | Setup Guide |
|---|---|---|
| `idf-sdk/` | ESP32, ESP32-C3, ESP32-S3 | [ESP-IDF Setup Guide](idf-sdk/ESP-IDF_SETUP_GUIDE.md) |
| `pico-sdk/` | Raspberry Pi Pico (W) / Pico 2 (W) | [Pico Setup Guide](pico-sdk/PICO_SETUP_GUIDE.md) |
| `nrf52/` | Nordic nRF52840 | [nRF52 Setup Guide](nrf52/nrf52_SETUP_GUIDE.md) |
| `stm32/` | STM32F411 | — |
| `coralmicro/` | Coral Dev Board Micro | [Coralmicro Setup Guide](CORALMICRO_SETUP_GUIDE.md) |

## Getting Started

Refer to the setup guide for your target platform (linked in the table above). Each guide covers toolchain installation, code compilation, flashing, and measurement procedures.

For the Coral Dev Board Micro, we recommend cloning the repository into `path_to_microgreen/profiling/inference/` for consistency with the rest of the project.

## Results

Profiling results referenced in the paper are documented in [RESULTS.md](RESULTS.md).